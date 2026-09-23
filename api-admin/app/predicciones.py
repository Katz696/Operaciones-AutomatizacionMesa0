from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from .database import engine
from .dependencies import obtener_usuario_actual, requerir_rol

router = APIRouter(prefix="/predicciones", tags=["predicciones"])


class CorreccionRequest(BaseModel):
    # Todos opcionales
    tipo_nombre: Optional[str] = None
    tipo_id: Optional[str] = None
    categoria_nombre: Optional[str] = None
    categoria_id: Optional[str] = None
    subcategoria_nombre: Optional[str] = None
    subcategoria_id: Optional[str] = None


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
def confirmar(prediccion_id: str, usuario: dict = Depends(requerir_rol("admin", "revisor"))):
    with engine.begin() as conn:
        pred = conn.execute(
            text("SELECT * FROM predicciones WHERE id = :id"),
            {"id": prediccion_id}
        ).mappings().first()

        if not pred:
            raise HTTPException(status_code=404, detail="Predicción no encontrada")

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
            return {"status": "sin cambios", "detalle": "ninguna dimensión estaba pendiente"}

    return {
        "status": "confirmado",
        "prediccion_id": prediccion_id,
        "campos_actualizados": campos_actualizados
    }


@router.post("/{prediccion_id}/corregir")
def corregir(
    prediccion_id: str,
    payload: CorreccionRequest,
    usuario: dict = Depends(requerir_rol("admin", "revisor"))
):
    with engine.begin() as conn:
        pred = conn.execute(
            text("SELECT * FROM predicciones WHERE id = :id"),
            {"id": prediccion_id}
        ).mappings().first()

        if not pred:
            raise HTTPException(status_code=404, detail="Predicción no encontrada")

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

    return {
        "status": "corregido",
        "prediccion_id": prediccion_id,
        "campos_actualizados": campos_actualizados
    }
