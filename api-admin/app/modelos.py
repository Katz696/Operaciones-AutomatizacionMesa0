from typing import Optional, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from .database import engine
from .dependencies import obtener_usuario_actual, requerir_rol
from .clients import api_ml_post

router = APIRouter(tags=["modelos"])

TipoModelo = Literal["padtypes", "categoria", "subcategoria"]


class ActivarModeloRequest(BaseModel):
    tipo: TipoModelo
    archivo: str


# ============================================================
# Modelos entrenados (tabla `models`) — lectura directa a DB
# ============================================================

@router.get("/models")
def listar_modelos(
    tipo: Optional[TipoModelo] = None,
    usuario: dict = Depends(obtener_usuario_actual)
):
    if tipo:
        query = text("""
            SELECT id, nombre, tipo, version, archivo, accuracy, f1_score,
                   fecha_entrenamiento, activo, notas
            FROM models
            WHERE tipo = :tipo
            ORDER BY fecha_entrenamiento DESC
        """)
        params = {"tipo": tipo}
    else:
        query = text("""
            SELECT id, nombre, tipo, version, archivo, accuracy, f1_score,
                   fecha_entrenamiento, activo, notas
            FROM models
            ORDER BY tipo, fecha_entrenamiento DESC
        """)
        params = {}

    with engine.connect() as conn:
        rows = conn.execute(query, params).mappings().all()
    return list(rows)


# ============================================================
# Activar una versión — proxy a api-ml (tiene que recargar
# el modelo en memoria de SU proceso, api-admin no puede)
# ============================================================

@router.post("/models/activar")
def activar_modelo(
    payload: ActivarModeloRequest,
    usuario: dict = Depends(requerir_rol("admin"))
):
    try:
        resp = api_ml_post(
            "/set-model",
            params={"nombre_modelo": payload.archivo, "tipo": payload.tipo}
        )
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"No se pudo contactar a api-ml: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"api-ml respondió {resp.status_code}: {resp.text}")

    return resp.json()


# ============================================================
# Reentrenamientos — disparar vía proxy a api-ml,
# consultar estado con lectura directa a training_jobs
# ============================================================

@router.post("/reentrenamientos/{tipo}")
def disparar_reentrenamiento(
    tipo: TipoModelo,
    usuario: dict = Depends(requerir_rol("admin"))
):
    endpoint = {
        "padtypes": "/train",                 # síncrono en api-ml, sin job_id
        "categoria": "/train-category",        # async, devuelve job_id
        "subcategoria": "/train-subcategory",  # async, devuelve job_id
    }[tipo]

    # /train (padtypes) bloquea hasta terminar el script, así que le
    # damos más margen de timeout que a los otros dos.
    timeout = 300.0 if tipo == "padtypes" else 30.0

    try:
        resp = api_ml_post(endpoint, timeout=timeout)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"No se pudo contactar a api-ml: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"api-ml respondió {resp.status_code}: {resp.text}")

    return resp.json()


@router.get("/reentrenamientos")
def listar_reentrenamientos(limit: int = 20, usuario: dict = Depends(obtener_usuario_actual)):
    query = text("""
        SELECT id, tipo, estado, script, inicio, fin, returncode
        FROM training_jobs
        ORDER BY inicio DESC
        LIMIT :limit
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"limit": limit}).mappings().all()
    return list(rows)


@router.get("/reentrenamientos/{job_id}")
def obtener_reentrenamiento(job_id: str, usuario: dict = Depends(obtener_usuario_actual)):
    query = text("""
        SELECT id, tipo, estado, script, inicio, fin, returncode, stdout, stderr
        FROM training_jobs
        WHERE id = :id
    """)
    with engine.connect() as conn:
        row = conn.execute(query, {"id": job_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="job_id no encontrado")
    return dict(row)