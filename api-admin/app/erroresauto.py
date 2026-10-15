from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from .database import engine
from .dependencies import obtener_usuario_actual

router = APIRouter(prefix="/errores-auto", tags=["errores-auto"])

Estado = Literal["todos", "sin_notificar", "notificados"]

# Condiciones fijas por estado: nunca se arman con texto que mande el usuario,
# así que es seguro usarlas en los f-strings de SQL de más abajo.
CONDICION_ESTADO = {
    "sin_notificar": "t.notificado IS NOT TRUE",
    "notificados": "t.notificado IS TRUE",
}


@router.get("/resumen")
def resumen(usuario: dict = Depends(obtener_usuario_actual)):
    q_totales = text("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE notificado IS NOT TRUE) AS sin_notificar,
            COUNT(*) FILTER (WHERE notificado IS TRUE) AS notificados,
            MAX(fecha_deteccion) AS ultima_deteccion
        FROM tickets_guardado_fallido
    """)
    q_pasos = text("""
        SELECT
            COALESCE(paso, 'sin_paso') AS paso,
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE notificado IS NOT TRUE) AS sin_notificar
        FROM tickets_guardado_fallido
        GROUP BY 1
        ORDER BY total DESC, 1
    """)
    with engine.connect() as conn:
        totales = conn.execute(q_totales).mappings().first()
        pasos = conn.execute(q_pasos).mappings().all()

    return {**dict(totales), "por_paso": [dict(p) for p in pasos]}


@router.get("")
def listar(
    estado: Estado = "todos",
    paso: Optional[str] = None,
    buscar: Optional[str] = None,
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    usuario: dict = Depends(obtener_usuario_actual),
):
    condiciones: list[str] = []
    filtros: dict = {}

    if estado in CONDICION_ESTADO:
        condiciones.append(CONDICION_ESTADO[estado])

    if paso:
        # "sin_paso" es el nombre que /resumen le da a los registros con paso NULL.
        condiciones.append("COALESCE(t.paso, 'sin_paso') = :paso")
        filtros["paso"] = paso

    if buscar:
        condiciones.append(
            "(t.incidente_codigo ILIKE :buscar"
            " OR t.mensaje_error ILIKE :buscar"
            " OR p.incident_title ILIKE :buscar)"
        )
        filtros["buscar"] = f"%{buscar}%"

    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
    desde = f"""
        FROM tickets_guardado_fallido t
        LEFT JOIN predicciones p ON p.id = t.prediccion_id
        {where}
    """

    q_total = text(f"SELECT COUNT(*) {desde}")
    q_items = text(f"""
        SELECT
            t.id, t.prediccion_id, t.incidente_codigo,
            p.incident_title, p.cliente_nombre,
            t.tipo, t.categoria, t.subcategoria,
            t.paso, t.mensaje_error,
            t.fecha_deteccion, t.notificado, t.fecha_notificado
        {desde}
        ORDER BY t.fecha_deteccion DESC, t.id DESC
        LIMIT :limit OFFSET :offset
    """)

    with engine.connect() as conn:
        total = conn.execute(q_total, filtros).scalar()
        rows = conn.execute(q_items, {**filtros, "limit": limit, "offset": offset}).mappings().all()

    return {"total": total, "items": [dict(r) for r in rows]}


class CambioNotificado(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=500)
    notificado: bool


@router.post("/notificado")
def cambiar_notificado(body: CambioNotificado, usuario: dict = Depends(obtener_usuario_actual)):
    """
    notificado=true  -> marca los errores como notificados (no se vuelven a enviar).
    notificado=false -> los deja sin notificar, así que el flujo de n8n que consulta
                        los pendientes los incluye otra vez en el siguiente correo.
    """
    query = text("""
        UPDATE tickets_guardado_fallido
        SET notificado = :notificado,
            fecha_notificado = CASE WHEN :notificado THEN NOW() ELSE NULL END
        WHERE id = ANY(:ids)
        RETURNING id
    """)
    with engine.begin() as conn:
        rows = conn.execute(query, {"ids": body.ids, "notificado": body.notificado}).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="No se encontraron los errores indicados.")

    return {"actualizados": [r[0] for r in rows]}