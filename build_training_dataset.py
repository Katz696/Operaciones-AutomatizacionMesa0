import pandas as pd
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

BASE_DATASET = "data/dataset-base.csv"
FEEDBACK_DATASET = "logs/low_confidence_predictions.csv"
OUTPUT_DATASET = "data/dataset-training.csv"

MIN_FEEDBACK = 50

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
# Cargar feedback desde db
# =========================

query = """
SELECT *
FROM tickets_feedback
"""

feedback = pd.read_sql(query, engine)

print("Total feedback en DB:", len(feedback))

# =========================
# filtrar feedback nuevo
# =========================

feedback_nuevo = feedback[
    (feedback["ml_revision"].isin(["corregido", "confirmado"])) &
    (feedback["used_for_training"] == False)
]

print("Feedback nuevo disponible:", len(feedback_nuevo))

# =========================
# construir dataset
# =========================

if len(feedback_nuevo) >= MIN_FEEDBACK:

    feedback_final = pd.DataFrame({
        "id": feedback_nuevo["id"],
        "incidentTitle": feedback_nuevo["incident_title"],
        "description": feedback_nuevo["description"],
        "padTypes_id": feedback_nuevo["padtypes_id_corregido"]
    })

    print("Tickets agregados al entrenamiento:", len(feedback_final))

        # dataset acumulativo
    dataset_final = pd.concat(
        [dataset_actual, feedback_final],
        ignore_index=True
    )

    dataset_built = True

    # marcar feedback como usado
    ids_usados = feedback_nuevo["id"].tolist()

    update_query = text("""
        UPDATE tickets_feedback
        SET used_for_training = true
        WHERE id = ANY(:ids)
    """)

    with engine.connect() as conn:
        conn.execute(update_query, {"ids": ids_usados})
        conn.commit()

    # feedback.loc[
    #     feedback["id"].isin(feedback_nuevo["id"]),
    #     "used_for_training"
    # ] = True

    # feedback.to_csv(FEEDBACK_DATASET, sep=";", index=False)

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