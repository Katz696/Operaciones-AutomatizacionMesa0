from typing import Optional, Literal
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text

from .database import engine
from .dependencies import obtener_usuario_actual, requerir_rol
from .clients import api_ml_post

from .dependencies import obtener_usuario_actual

router = APIRouter(prefix="/modelos", tags=["modelos"])

TipoModelo = Literal["padtypes", "categoria", "subcategoria"]

ML_API_URL = os.getenv("API_ML_BASE_URL", "http://api:8000")

def _forward_auth_header(request: Request) -> dict:
    auth = request.headers.get("authorization")
    if not auth:
        raise HTTPException(status_code=401, detail="Falta token de autenticación")
    return {"Authorization": auth}

class ActivarModeloRequest(BaseModel):
    tipo: TipoModelo
    archivo: str


# ============================================================
# Modelos entrenados (tabla `models`) — lectura directa a DB
# ============================================================

@router.get("")
async def listar_modelos(request: Request, usuario: dict = Depends(obtener_usuario_actual)):
    headers = _forward_auth_header(request)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{ML_API_URL}/models", headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Error consultando api-ml: {e}")

    return resp.json()

# ============================================================
# Activar una versión — proxy a api-ml (tiene que recargar
# el modelo en memoria de SU proceso, api-admin no puede)
# ============================================================

@router.post("/models/activar")
def activar_modelo(
    payload: ActivarModeloRequest,
    request: Request,
    usuario: dict = Depends(requerir_rol("admin"))
):
    headers = _forward_auth_header(request)
    try:
        resp = api_ml_post(
            "/set-model",
            headers=headers,
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
    request: Request,
    usuario: dict = Depends(requerir_rol("admin"))
):
    headers = _forward_auth_header(request)

    endpoint = {
        "padtypes": "/train",
        "categoria": "/train-category",
        "subcategoria": "/train-subcategory",
    }[tipo]

    timeout = 300.0 if tipo == "padtypes" else 30.0

    try:
        resp = api_ml_post(endpoint, headers=headers, timeout=timeout)
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

@router.post("/dataset/{tipo}")
def construir_dataset(
    tipo: TipoModelo,
    request: Request,
    usuario: dict = Depends(requerir_rol("admin"))
):
    headers = _forward_auth_header(request)
    endpoint = "/build-dataset" if tipo == "padtypes" else "/build-dataset-category"

    try:
        resp = api_ml_post(endpoint, headers=headers, timeout=120.0)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"No se pudo contactar a api-ml: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"api-ml respondió {resp.status_code}: {resp.text}")

    return resp.json()

@router.post("/evaluaciones/{tipo}")
def evaluar_modelo(
    tipo: TipoModelo,
    request: Request,
    usuario: dict = Depends(requerir_rol("admin"))
):
    headers = _forward_auth_header(request)
    endpoint = {
        "padtypes": "/evaluate",
        "categoria": "/evaluate-category",
        "subcategoria": "/evaluate-subcategory",
    }[tipo]

    try:
        resp = api_ml_post(endpoint, headers=headers, timeout=120.0)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"No se pudo contactar a api-ml: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"api-ml respondió {resp.status_code}: {resp.text}")

    return resp.json()