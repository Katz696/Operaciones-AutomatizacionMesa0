import pandas as pd
import joblib
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, f1_score

from text_preprocessing import limpiar_texto, stopwords_es
from config import clases_validas, mapa_ids


def mapear_clase(id_tipo):
    return clases_validas.get(id_tipo, "Otros")


# =========================
# Cargar dataset
# =========================

data = pd.read_csv("data/dataset-training.csv", sep=";")

print("Dataset cargado:", len(data))


# =========================
# Limpieza
# =========================

data["Title"] = data["incidentTitle"].apply(limpiar_texto)
data["Description"] = data["description"].apply(limpiar_texto)

data["texto"] = data["Title"] + " " + data["Description"]

data["categoria"] = data["padTypes_id"].apply(mapear_clase)


X = data["texto"]
y = data["categoria"]


# =========================
# Split
# =========================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)


# =========================
# Pipeline
# =========================

modelo = Pipeline([

    (
        "tfidf",
        TfidfVectorizer(
            max_features=80000,
            ngram_range=(1,2),
            min_df=3,
            max_df=0.9,
            sublinear_tf=True,
            stop_words=stopwords_es
        )
    ),

    (
        "clf",
        LogisticRegression(
            max_iter=1000,
            # class_weight="balanced"
        )
    )
])


print("Entrenando modelo...")

modelo.fit(X_train, y_train)


# =========================
# Guardar modelo
# =========================

version = datetime.now().strftime("%Y%m%d_%H%M")

nombre_modelo = f"models/modelo_tickets_{version}.pkl"

joblib.dump({
    "modelo": modelo,
    "mapa_ids": mapa_ids,
    "version": version
}, nombre_modelo)

print("Modelo guardado:", nombre_modelo)