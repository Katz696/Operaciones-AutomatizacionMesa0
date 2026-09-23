import pandas as pd
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

BASE_DATASET = "data/dataset-base.csv"
OUTPUT_DATASET = "data/dataset-training.csv"

def obtener_min_feedback(engine, clave: str, default: int = 1) -> int:
    query = text("SELECT valor FROM ml_config WHERE clave = :clave")
    with engine.connect() as conn:
        row = conn.execute(query, {"clave": clave}).fetchone()

    if row is None:
        print(f"Advertencia: no existe la clave '{clave}' en ml_config, usando default={default}")
        return default

    return int(row.valor)


MIN_FEEDBACK = obtener_min_feedback(engine, "min_feedback_tipo")
print("MIN_FEEDBACK configurado:", MIN_FEEDBACK)

print("Construyendo dataset de entrenamiento...")

# =========================
# cargar dataset existente
# =========================

if os.path.exists(OUTPUT_DATASET):

    dataset_actual = pd.read_csv(OUTPUT_DATASET, sep=";")
    print("Dataset training actual:", len(dataset_actual))

else:

    dataset_actual = pd.read_csv(BASE_DATASET, sep=";")
    print("Dataset base cargado:", len(dataset_actual))

dataset_final = dataset_actual
dataset_built = False

# =========================
# Cargar feedback (correcciones de tipo) desde db
# =========================

query = """
SELECT
    c.id                    AS correccion_id,
    p.id                    AS ticket_id,
    p.incident_title,
    p.description,
    c.valor_id_corregido    AS padtypes_id
FROM correcciones c
JOIN predicciones p ON p.id = c.prediccion_id
WHERE c.campo = 'tipo'
  AND c.accion IN ('corregido', 'confirmado')
  AND c.used_for_training = false
"""

feedback_nuevo = pd.read_sql(query, engine)

print("Feedback nuevo disponible:", len(feedback_nuevo))

# =========================
# construir dataset
# =========================

if len(feedback_nuevo) >= MIN_FEEDBACK:

    feedback_final = pd.DataFrame({
        "id": feedback_nuevo["ticket_id"],
        "incidentTitle": feedback_nuevo["incident_title"],
        "description": feedback_nuevo["description"],
        "padTypes_id": feedback_nuevo["padtypes_id"]
    })

    print("Tickets agregados al entrenamiento:", len(feedback_final))

    # dataset acumulativo
    dataset_final = pd.concat(
        [dataset_actual, feedback_final],
        ignore_index=True
    )

    dataset_built = True

    # marcar como usadas las correcciones que se incluyeron
    correccion_ids_usadas = feedback_nuevo["correccion_id"].tolist()

    update_query = text("""
        UPDATE correcciones
        SET used_for_training = true
        WHERE id = ANY(:ids)
    """)

    with engine.connect() as conn:
        conn.execute(update_query, {"ids": correccion_ids_usadas})
        conn.commit()

else:

    print(f"Feedback insuficiente ({len(feedback_nuevo)}/{MIN_FEEDBACK})")


# =========================
# eliminar duplicados
# =========================

dataset_final = dataset_final.drop_duplicates(
    subset=["incidentTitle", "description", "padTypes_id"]
)

print("Dataset final:", len(dataset_final))

# =========================
# guardar dataset acumulado
# =========================

dataset_final.to_csv(
    OUTPUT_DATASET,
    sep=";",
    index=False
)

print("Dataset de entrenamiento actualizado:", OUTPUT_DATASET)

# =========================
# bandera para n8n / API
# =========================

if dataset_built:
    print("DATASET_BUILT=true")
else:
    print("DATASET_BUILT=false")