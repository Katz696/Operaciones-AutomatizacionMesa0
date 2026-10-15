from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from .database import engine
from .dependencies import obtener_usuario_actual

router = APIRouter(prefix="/historial", tags=["historial"])


def requiere_admin(usuario: dict = Depends(obtener_usuario_actual)) -> dict:
    if usuario.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo un administrador puede hacer esto.")
    return usuario


def requiere_revisor(usuario: dict = Depends(obtener_usuario_actual)) -> dict:
    # admin y revisor pueden modificar; el rol "lectura" solo consulta.
    if usuario.get("role") not in ("admin", "revisor"):
        raise HTTPException(status_code=403, detail="Tu rol no permite modificar predicciones.")
    return usuario

TipoCampo = Literal["tipo", "categoria", "subcategoria"]
Estado = Literal["todas", "pendientes", "revisadas", "automaticas"]

# Columnas fijas por dimensión
COL_REVISION = {
    "tipo": "tipo_revision",
    "categoria": "categoria_revision",
    "subcategoria": "subcategoria_revision",
}

# Filtros por estado de revisión del ticket 
FILTROS_ESTADO = {
    "todas": "TRUE",
    # Al menos una dimensión pendiente: mismo criterio que /metricas/resumen.
    "pendientes": """(
        tipo_revision = 'pendiente'
        OR categoria_revision = 'pendiente'
        OR subcategoria_revision = 'pendiente'
    )""",
    # Ninguna pendiente y al menos una confirmada/corregida por una persona.
    "revisadas": """(
        COALESCE(tipo_revision, '') <> 'pendiente'
        AND COALESCE(categoria_revision, '') <> 'pendiente'
        AND COALESCE(subcategoria_revision, '') <> 'pendiente'
        AND (
            tipo_revision IN ('confirmado', 'corregido')
            OR categoria_revision IN ('confirmado', 'corregido')
            OR subcategoria_revision IN ('confirmado', 'corregido')
        )
    )""",
    # Las tres dimensiones aceptadas automáticamente.
    "automaticas": """(
        tipo_revision = 'NA'
        AND categoria_revision = 'NA'
        AND subcategoria_revision = 'NA'
    )""",
}


@router.get("")
def listar(
    q: Optional[str] = None,
    estado: Estado = "todas",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    usuario: dict = Depends(obtener_usuario_actual),
):
    filtro_estado = FILTROS_ESTADO[estado]
    params: dict = {"limit": page_size, "offset": (page - 1) * page_size}

    filtro_busqueda = "TRUE"
    if q and q.strip():
        limpio = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        params["q"] = f"%{limpio}%"
        filtro_busqueda = """(
            code ILIKE :q
            OR incident_title ILIKE :q
            OR cliente_nombre ILIKE :q
            OR tipo_predicho ILIKE :q
            OR categoria_predicha ILIKE :q
            OR subcategoria_predicha ILIKE :q
        )"""

    where = f"{filtro_estado} AND {filtro_busqueda}"

    query_total = text(f"SELECT COUNT(*) FROM predicciones WHERE {where}")
    query_items = text(f"""
        SELECT
            p.id, p.code, p.incident_title, p.description, p.cliente_nombre,
            p.tipo_predicho, p.tipo_confianza, p.tipo_modelo_version, p.tipo_revision,
            p.categoria_predicha, p.categoria_confianza, p.categoria_modelo_version, p.categoria_revision,
            p.subcategoria_predicha, p.subcategoria_confianza, p.subcategoria_modelo_version, p.subcategoria_revision,
            p.notificado, p.fecha_creacion, p.fecha_actualizacion,
            (SELECT COUNT(*) FROM correcciones c WHERE c.prediccion_id = p.id) AS n_correcciones
        FROM predicciones p
        WHERE {where}
        ORDER BY p.fecha_creacion DESC, p.id
        LIMIT :limit OFFSET :offset
    """)

    with engine.connect() as conn:
        total = conn.execute(query_total, {k: v for k, v in params.items() if k == "q"}).scalar()
        rows = conn.execute(query_items, params).mappings().all()

    return {"total": total, "page": page, "page_size": page_size, "items": list(rows)}


class MarcarPendienteBody(BaseModel):
    dimensiones: list[TipoCampo] = Field(
        default_factory=lambda: ["tipo", "categoria", "subcategoria"]
    )


@router.post("/{prediccion_id}/pendiente")
def marcar_pendiente(
    prediccion_id: str,
    body: MarcarPendienteBody,
    usuario: dict = Depends(requiere_revisor),
):
    dimensiones = list(dict.fromkeys(body.dimensiones))  # sin repetidas, conserva orden
    if not dimensiones:
        raise HTTPException(status_code=400, detail="Indica al menos una dimensión.")

    sets = ", ".join(f"{COL_REVISION[d]} = 'pendiente'" for d in dimensiones)
    query = text(f"""
        UPDATE predicciones
        SET {sets}, fecha_actualizacion = NOW()
        WHERE id = :id
        RETURNING id
    """)
    with engine.begin() as conn:
        res = conn.execute(query, {"id": prediccion_id}).first()

    if res is None:
        raise HTTPException(status_code=404, detail="Predicción no encontrada.")
    return {"status": "ok", "campos_actualizados": dimensiones}


@router.delete("/{prediccion_id}")
def eliminar(prediccion_id: str, usuario: dict = Depends(requiere_admin)):
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM tickets_guardado_fallido WHERE prediccion_id = :id"),
            {"id": prediccion_id},
        )
        corr = conn.execute(
            text("DELETE FROM correcciones WHERE prediccion_id = :id"),
            {"id": prediccion_id},
        )
        res = conn.execute(
            text("DELETE FROM predicciones WHERE id = :id"),
            {"id": prediccion_id},
        )
        if res.rowcount == 0:
            raise HTTPException(status_code=404, detail="Predicción no encontrada.")

    return {"status": "eliminada", "correcciones_eliminadas": corr.rowcount}