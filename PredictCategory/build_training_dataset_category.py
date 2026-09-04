import pandas as pd
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

# =========================
# Rutas
# =========================

BASE_DATASET   = "../data/dataset-base-category.csv"
OUTPUT_DATASET = "../data/dataset-training-category.csv"

def obtener_min_feedback(engine, clave: str, default: int = 1) -> int:
    query = text("SELECT valor FROM ml_config WHERE clave = :clave")
    with engine.connect() as conn:
        row = conn.execute(query, {"clave": clave}).fetchone()

    if row is None:
        print(f"Advertencia: no existe la clave '{clave}' en ml_config, usando default={default}")
        return default

    return int(row.valor)


MIN_FEEDBACK = obtener_min_feedback(engine, "min_feedback_categoria")
print("MIN_FEEDBACK configurado:", MIN_FEEDBACK)

COLUMNAS_MODELO = ["IncidentTitle", "Description", "Category_id", "Client_id"]

print("Construyendo dataset de entrenamiento (categoria/subcategoria)...")

# =========================
# cargar dataset existente
# =========================

if os.path.exists(OUTPUT_DATASET):

    dataset_actual = pd.read_csv(OUTPUT_DATASET, sep=";")
    print("Dataset training actual:", len(dataset_actual))

else:

    dataset_actual = pd.read_csv(BASE_DATASET, sep=";")
    print("Dataset base cargado:", len(dataset_actual))

dataset_actual = dataset_actual[COLUMNAS_MODELO]

dataset_final = dataset_actual
dataset_built = False

# =========================
# Cargar feedback desde db
# =========================

query = """
SELECT *
FROM categoria_feedback
WHERE tipo_modelo IN ('categoria', 'subcategoria')
"""

feedback = pd.read_sql(query, engine)

print("Total feedback en DB (categoria + subcategoria):", len(feedback))

# =========================
# filtrar feedback nuevo
# =========================

feedback_nuevo = feedback[
    (feedback["ml_revision"].isin(["corregido", "confirmado"])) &
    (feedback["used_for_training"] == False)
]

print("Feedback nuevo disponible:", len(feedback_nuevo))
print(
    "  - categoria:",
    len(feedback_nuevo[feedback_nuevo["tipo_modelo"] == "categoria"]),
    "| subcategoria:",
    len(feedback_nuevo[feedback_nuevo["tipo_modelo"] == "subcategoria"])
)

# =========================
# construir dataset
# =========================

if len(feedback_nuevo) >= MIN_FEEDBACK:

    feedback_final = pd.DataFrame({
        "IncidentTitle": feedback_nuevo["incident_title"],
        "Description": feedback_nuevo["description"],
        "Category_id": feedback_nuevo["categoria_id_corregida"],
        "Client_id":   feedback_nuevo["client_id"].astype(str).str.upper()
    })[COLUMNAS_MODELO]

    print("Tickets agregados al entrenamiento:", len(feedback_final))

    # dataset acumulativo
    dataset_final = pd.concat(
        [dataset_actual, feedback_final],
        ignore_index=True
    )

    dataset_built = True

    # marcar feedback como usado
    update_query = text("""
        UPDATE categoria_feedback
        SET used_for_training = true
        WHERE id = ANY(:ids) AND tipo_modelo = :tipo_modelo
    """)

    with engine.connect() as conn:
        for dimension in ("categoria", "subcategoria"):
            ids_usados = feedback_nuevo.loc[
                feedback_nuevo["tipo_modelo"] == dimension, "id"
            ].tolist()

            if ids_usados:
                conn.execute(update_query, {"ids": ids_usados, "tipo_modelo": dimension})

        conn.commit()

else:

    print(f"Feedback insuficiente ({len(feedback_nuevo)}/{MIN_FEEDBACK})")


# =========================
# eliminar duplicados
# =========================

dataset_final = dataset_final.drop_duplicates(
    subset=["IncidentTitle", "Description", "Category_id", "Client_id"]
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