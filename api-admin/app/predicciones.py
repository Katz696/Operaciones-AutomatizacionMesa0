from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import text

from .database import engine
from .dependencies import obtener_usuario_actual, requerir_rol

import os
import httpx
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predicciones", tags=["predicciones"])

ML_API_URL = os.getenv("ML_API_URL", "http://api:8000")
PROACTIVANET_API_URL = os.getenv("PROACTIVANET_API_URL", "http://api-proactivanet:8001")

def _forward_auth_header(request: Request) -> dict:
    auth = request.headers.get("authorization")
    if not auth:
        raise HTTPException(status_code=401, detail="Falta token de autenticación")
    return {"Authorization": auth}

class CorreccionRequest(BaseModel):
    # Todos opcionales
    tipo_nombre: Optional[str] = None
    tipo_id: Optional[str] = None
    categoria_nombre: Optional[str] = None
    categoria_id: Optional[str] = None
    subcategoria_nombre: Optional[str] = None
    subcategoria_id: Optional[str] = None

def _obtener_prediccion(prediccion_id: str):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM predicciones WHERE id = :id"),
            {"id": prediccion_id}
        ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Predicción no encontrada")
    return row

def _guardar_correccion(
    conn, prediccion_id: str, campo: str,
    valor_original, valor_id_original,
    valor_corregido, valor_id_corregido,
    accion: str, revisor_username: str
):
    row = conn.execute(
        text("SELECT id FROM api_users WHERE username = :u"),
        {"u": revisor_username}
    ).mappings().first()
    revisor_id = row["id"] if row else None

    query = text("""
        INSERT INTO correcciones (
            prediccion_id, campo, valor_original, valor_id_original,
            valor_corregido, valor_id_corregido, accion, revisor_id, fecha_revision
        )
        VALUES (
            :prediccion_id, :campo, :valor_original, :valor_id_original,
            :valor_corregido, :valor_id_corregido, :accion, :revisor_id, NOW()
        )
        ON CONFLICT (prediccion_id, campo) DO UPDATE SET
            valor_corregido    = EXCLUDED.valor_corregido,
            valor_id_corregido = EXCLUDED.valor_id_corregido,
            accion             = EXCLUDED.accion,
            revisor_id         = EXCLUDED.revisor_id,
            fecha_revision     = NOW()
    """)
    conn.execute(query, {
        "prediccion_id": prediccion_id, "campo": campo,
        "valor_original": valor_original, "valor_id_original": valor_id_original,
        "valor_corregido": valor_corregido, "valor_id_corregido": valor_id_corregido,
        "accion": accion, "revisor_id": revisor_id
    })

    conn.execute(
        text(f"UPDATE predicciones SET {campo}_revision = :accion, fecha_actualizacion = NOW() WHERE id = :id"),
        {"accion": accion, "id": prediccion_id}
    )


async def _aplicar_en_proactivanet(headers: dict, code: str, tipo: str, categoria: str, subcategoria: str) -> dict:
    payload = {"tickets": [{"code": code, "tipo": tipo, "categoria": categoria, "subcategoria": subcategoria}]}
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(f"{PROACTIVANET_API_URL}/api/v1/tickets/batch", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["results"][0] if data.get("results") else {"status": "error", "message": "Sin respuesta"}
        except httpx.HTTPStatusError as e:
            return {
                "status": "error",
                "message": f"api-proactivanet respondió {e.response.status_code}: {e.response.text}"
            }
        except httpx.HTTPError as e:
            return {"status": "error", "message": f"No se pudo contactar a api-proactivanet: {e}"}

async def _aplicar_en_proactivanet_bg(headers: dict, code: str, tipo: str, categoria: str, subcategoria: str):
    resultado = await _aplicar_en_proactivanet(headers, code, tipo, categoria, subcategoria)
    if resultado.get("status") == "error":
        logger.error(f"[confirmar] RPA falló para {code}: {resultado.get('message')}")
    else:
        logger.info(f"[confirmar] RPA aplicado para {code}")

def _normalizar_subcategoria(valor: Optional[str]) -> str:
    return valor if valor not in (None, "") else "/"

# ---------------- opciones (proxy hacia api-ml) ----------------

def _obtener_client_id(prediccion_id: str) -> str:
    pred = _obtener_prediccion(prediccion_id)
    if not pred["client_id"]:
        raise HTTPException(status_code=400, detail="La predicción no tiene client_id asociado")
    return pred["client_id"]


@router.get("/{prediccion_id}/opciones-categoria")
async def opciones_categoria(
    prediccion_id: str, request: Request, usuario: dict = Depends(obtener_usuario_actual)
):
    client_id = _obtener_client_id(prediccion_id)
    headers = _forward_auth_header(request)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(
                f"{ML_API_URL}/categoria/opciones", params={"client_id": client_id}, headers=headers
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Error consultando api-ml: {e}")

    return resp.json()


@router.get("/{prediccion_id}/opciones-subcategoria")
async def opciones_subcategoria(
    prediccion_id: str, categoria: str, request: Request, usuario: dict = Depends(obtener_usuario_actual)
):
    client_id = _obtener_client_id(prediccion_id)
    headers = _forward_auth_header(request)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(
                f"{ML_API_URL}/subcategoria/opciones",
                params={"client_id": client_id, "categoria": categoria},
                headers=headers,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Error consultando api-ml: {e}")

    return resp.json()

# ============================================================
# Lectura
# ============================================================

@router.get("/pending")
def obtener_pendientes(limit: int = 20, usuario: dict = Depends(obtener_usuario_actual)):
    query = text("""
        SELECT
            id, code, incident_title, description, cliente_nombre,
            tipo_predicho, tipo_id_predicho, tipo_confianza, tipo_revision,
            categoria_predicha, categoria_id_predicha, categoria_confianza, categoria_revision,
            subcategoria_predicha, subcategoria_id_predicha, subcategoria_confianza, subcategoria_revision,
            fecha_creacion
        FROM predicciones
        WHERE tipo_revision = 'pendiente'
           OR categoria_revision = 'pendiente'
           OR subcategoria_revision = 'pendiente'
        ORDER BY fecha_creacion ASC
        LIMIT :limit
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"limit": limit}).mappings().all()
    return {"total": len(rows), "tickets": [dict(r) for r in rows]}


@router.get("/{prediccion_id}")
def obtener_detalle(prediccion_id: str, usuario: dict = Depends(obtener_usuario_actual)):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM predicciones WHERE id = :id"),
            {"id": prediccion_id}
        ).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail="Predicción no encontrada")

        correcciones = conn.execute(
            text("""
                SELECT campo, valor_original, valor_corregido, accion, fecha_revision
                FROM correcciones
                WHERE prediccion_id = :id
                ORDER BY campo
            """),
            {"id": prediccion_id}
        ).mappings().all()

    resultado = dict(row)
    resultado["correcciones"] = [dict(c) for c in correcciones]
    return resultado


# ============================================================
# Escritura — admin y revisor
# ============================================================

@router.post("/{prediccion_id}/confirmar")
def confirmar(
    prediccion_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    usuario: dict = Depends(requerir_rol("admin", "revisor")),
):
    headers = _forward_auth_header(request)

    with engine.begin() as conn:
        pred = conn.execute(
            text("SELECT * FROM predicciones WHERE id = :id"), {"id": prediccion_id}
        ).mappings().first()
        if not pred:
            raise HTTPException(status_code=404, detail="Predicción no encontrada")
        if not pred["code"]:
            raise HTTPException(status_code=400, detail="La predicción no tiene 'code' de Proactivanet asociado")
        if not pred["tipo_predicho"] or not pred["categoria_predicha"]:
            raise HTTPException(status_code=400, detail="La predicción no tiene tipo/categoría para aplicar")

        campos_actualizados = []
        dimensiones = [
            ("tipo", "tipo_predicho", "tipo_id_predicho"),
            ("categoria", "categoria_predicha", "categoria_id_predicha"),
            ("subcategoria", "subcategoria_predicha", "subcategoria_id_predicha"),
        ]
        for campo, valor_col, valor_id_col in dimensiones:
            if pred[f"{campo}_revision"] == "pendiente":
                _guardar_correccion(
                    conn, prediccion_id, campo,
                    pred[valor_col], pred[valor_id_col],
                    pred[valor_col], pred[valor_id_col],
                    "confirmado", usuario["username"]
                )
                campos_actualizados.append(campo)

        if not campos_actualizados:
            return {"status": "sin cambios", "detalle": "ninguna dimensión estaba pendiente", "automatizacion": "omitida"}

    background_tasks.add_task(
        _aplicar_en_proactivanet_bg,
        headers, pred["code"],
        pred["tipo_predicho"], pred["categoria_predicha"],
        _normalizar_subcategoria(pred["subcategoria_predicha"]),
    )

    return {
        "status": "confirmado",
        "prediccion_id": prediccion_id,
        "campos_actualizados": campos_actualizados,
        "automatizacion": "iniciada",
    }
    

@router.post("/{prediccion_id}/corregir")
async def corregir(
    prediccion_id: str, payload: CorreccionRequest, request: Request,
    usuario: dict = Depends(requerir_rol("admin", "revisor"))
):
    headers = _forward_auth_header(request)
    
    pred = _obtener_prediccion(prediccion_id)

    if not pred["code"]:
        raise HTTPException(status_code=400, detail="La predicción no tiene 'code' de Proactivanet asociado")

    with engine.begin() as conn:
        campos_actualizados = []

        if payload.tipo_nombre is not None:
            _guardar_correccion(
                conn, prediccion_id, "tipo",
                pred["tipo_predicho"], pred["tipo_id_predicho"],
                payload.tipo_nombre, payload.tipo_id,
                "corregido", usuario["username"]
            )
            campos_actualizados.append("tipo")

        if payload.categoria_nombre is not None:
            _guardar_correccion(
                conn, prediccion_id, "categoria",
                pred["categoria_predicha"], pred["categoria_id_predicha"],
                payload.categoria_nombre, payload.categoria_id,
                "corregido", usuario["username"]
            )
            campos_actualizados.append("categoria")

        if payload.subcategoria_nombre is not None:
            _guardar_correccion(
                conn, prediccion_id, "subcategoria",
                pred["subcategoria_predicha"], pred["subcategoria_id_predicha"],
                payload.subcategoria_nombre, payload.subcategoria_id,
                "corregido", usuario["username"]
            )
            campos_actualizados.append("subcategoria")

        if not campos_actualizados:
            raise HTTPException(status_code=400, detail="No se envió ningún campo para corregir")

    # valores finales a aplicar en Proactivanet: el corregido si vino, si no el que ya estaba predicho
    tipo_final = payload.tipo_nombre or pred["tipo_predicho"]
    categoria_final = payload.categoria_nombre or pred["categoria_predicha"]
    subcategoria_final = (
        payload.subcategoria_nombre
        if payload.subcategoria_nombre is not None
        else pred["subcategoria_predicha"]
    )

    resultado_rpa = await _aplicar_en_proactivanet(headers, pred["code"], tipo_final, categoria_final, subcategoria_final)

    return {
        "status": "corregido",
        "prediccion_id": prediccion_id,
        "campos_actualizados": campos_actualizados,
        "proactivanet": resultado_rpa,
    }