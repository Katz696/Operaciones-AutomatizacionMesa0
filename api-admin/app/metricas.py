from typing import Literal, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import text

from .database import engine
from .dependencies import obtener_usuario_actual
from .modelos import TipoModelo

router = APIRouter(prefix="/metricas", tags=["metricas"])

TipoCampo = Literal["tipo", "categoria", "subcategoria"]

# Nombres de columna por dimensión — fijos en este dict, nunca se
# interpolan directo desde lo que manda el usuario, así que es seguro
# usarlos en f-strings de SQL más abajo.
COLUMNAS = {
    "tipo": {
        "predicho": "tipo_predicho",
        "id": "tipo_id_predicho",
        "confianza": "tipo_confianza",
    },
    "categoria": {
        "predicho": "categoria_predicha",
        "id": "categoria_id_predicha",
        "confianza": "categoria_confianza",
    },
    "subcategoria": {
        "predicho": "subcategoria_predicha",
        "id": "subcategoria_id_predicha",
        "confianza": "subcategoria_confianza",
    },
}


@router.get("/resumen")
def resumen(usuario: dict = Depends(obtener_usuario_actual)):
    query = text("""
        SELECT
            COUNT(*) FILTER (WHERE tipo_predicho IS NOT NULL) AS tipo_total,
            SUM(CASE WHEN tipo_revision = 'pendiente' THEN 1 ELSE 0 END) AS tipo_pendientes,
            SUM(CASE WHEN tipo_revision = 'NA' THEN 1 ELSE 0 END) AS tipo_auto_aceptados,

            COUNT(*) FILTER (WHERE categoria_predicha IS NOT NULL) AS categoria_total,
            SUM(CASE WHEN categoria_revision = 'pendiente' THEN 1 ELSE 0 END) AS categoria_pendientes,
            SUM(CASE WHEN categoria_revision = 'NA' THEN 1 ELSE 0 END) AS categoria_auto_aceptados,

            COUNT(*) FILTER (WHERE subcategoria_predicha IS NOT NULL) AS subcategoria_total,
            SUM(CASE WHEN subcategoria_revision = 'pendiente' THEN 1 ELSE 0 END) AS subcategoria_pendientes,
            SUM(CASE WHEN subcategoria_revision = 'NA' THEN 1 ELSE 0 END) AS subcategoria_auto_aceptados
        FROM predicciones
    """)
    with engine.connect() as conn:
        row = conn.execute(query).mappings().first()

    return {
        "tipo": {
            "total": row["tipo_total"], "pendientes": row["tipo_pendientes"],
            "auto_aceptados": row["tipo_auto_aceptados"]
        },
        "categoria": {
            "total": row["categoria_total"], "pendientes": row["categoria_pendientes"],
            "auto_aceptados": row["categoria_auto_aceptados"]
        },
        "subcategoria": {
            "total": row["subcategoria_total"], "pendientes": row["subcategoria_pendientes"],
            "auto_aceptados": row["subcategoria_auto_aceptados"]
        },
    }


@router.get("/volumen")
def volumen(dias: int = 30, usuario: dict = Depends(obtener_usuario_actual)):
    query = text("""
        SELECT date_trunc('day', fecha_creacion) AS dia, COUNT(*) AS total
        FROM predicciones
        WHERE fecha_creacion >= NOW() - (:dias * INTERVAL '1 day')
        GROUP BY dia
        ORDER BY dia
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"dias": dias}).mappings().all()
    return list(rows)


@router.get("/distribucion/{campo}")
def distribucion(campo: TipoCampo, top: int = 10, usuario: dict = Depends(obtener_usuario_actual)):
    col = COLUMNAS[campo]["predicho"]
    query = text(f"""
        SELECT {col} AS valor, COUNT(*) AS total
        FROM predicciones
        WHERE {col} IS NOT NULL
        GROUP BY {col}
        ORDER BY total DESC
        LIMIT :top
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"top": top}).mappings().all()
    return list(rows)


@router.get("/confianza/{campo}")
def confianza(campo: TipoCampo, usuario: dict = Depends(obtener_usuario_actual)):
    col_conf = COLUMNAS[campo]["confianza"]
    query = text(f"""
        SELECT
            AVG({col_conf}) AS promedio,
            MIN({col_conf}) AS minimo,
            MAX({col_conf}) AS maximo,
            COUNT(*) FILTER (
                WHERE {col_conf} < (SELECT valor::float FROM ml_config WHERE clave = 'confidence_threshold')
            ) AS bajo_threshold
        FROM predicciones
        WHERE {col_conf} IS NOT NULL
    """)
    with engine.connect() as conn:
        row = conn.execute(query).mappings().first()
    return dict(row)


@router.get("/accuracy/{campo}")
def accuracy(campo: TipoCampo, usuario: dict = Depends(obtener_usuario_actual)):
    col_id = COLUMNAS[campo]["id"]
    query = text(f"""
        SELECT
            COUNT(*) FILTER (WHERE p.{col_id} = c.valor_id_corregido) * 1.0
                / NULLIF(COUNT(*), 0) AS accuracy,
            COUNT(*) AS total_revisados
        FROM predicciones p
        JOIN correcciones c ON c.prediccion_id = p.id AND c.campo = :campo
        WHERE c.accion IN ('confirmado', 'corregido')
    """)
    with engine.connect() as conn:
        row = conn.execute(query, {"campo": campo}).mappings().first()
    return dict(row)


@router.get("/modelos/{tipo}/evolucion")
def evolucion_modelo(tipo: TipoModelo, usuario: dict = Depends(obtener_usuario_actual)):
    query = text("""
        SELECT version, accuracy, f1_score, fecha_entrenamiento, activo
        FROM models
        WHERE tipo = :tipo
        ORDER BY fecha_entrenamiento ASC
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"tipo": tipo}).mappings().all()
    return list(rows)