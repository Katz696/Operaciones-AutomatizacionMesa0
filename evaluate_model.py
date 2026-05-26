import joblib
import pandas as pd
import glob
import os
import json
import sys

from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
from sklearn.model_selection import train_test_split

from text_preprocessing import limpiar_texto
from config import clases_validas


# ==========================
# Leer métricas del modelo actual (desde argumentos)
# ==========================

# default si no se pasan argumentos
accuracy_old = 0
f1_old = 0

if len(sys.argv) >= 3:
    try:
        accuracy_old = float(sys.argv[1])
        f1_old = float(sys.argv[2])
    except:
        pass


# ==========================
# Funciones auxiliares
# ==========================

def mapear_clase(id_tipo):
    return clases_validas.get(id_tipo, "Otros")


# ==========================
# Cargar dataset
# ==========================

data = pd.read_csv("data/dataset-base.csv", sep=";")

# ==========================
# Limpieza
# ==========================

data["Title"] = data["incidentTitle"].apply(limpiar_texto)
data["Description"] = data["description"].apply(limpiar_texto)

data["texto"] = data["Title"] + " " + data["Description"]
data["categoria"] = data["padTypes_id"].apply(mapear_clase)

X = data["texto"]
y = data["categoria"]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# ==========================
# Buscar modelo nuevo
# ==========================

modelos = glob.glob("models/modelo_tickets_*.pkl")

if not modelos:
    raise Exception("No hay modelos entrenados")

modelo_nuevo_path = sorted(modelos)[-1]

modelo_nuevo_data = joblib.load(modelo_nuevo_path)
modelo_nuevo = modelo_nuevo_data["modelo"]
version_nuevo = modelo_nuevo_data.get("version", "sin_version")

if not hasattr(modelo_nuevo, "predict"):
    raise Exception("Modelo inválido")

# ==========================
# Evaluar modelo nuevo
# ==========================

pred_new = modelo_nuevo.predict(X_test)

accuracy_new = accuracy_score(y_test, pred_new)
f1_new = f1_score(y_test, pred_new, average="weighted")

# ==========================
# Comparación
# ==========================

mejora = f1_new > f1_old

# ==========================
# Reportes (opcional para debug)
# ==========================

cm = confusion_matrix(y_test, pred_new)

# ==========================
# Resultado final (MISMA ESTRUCTURA)
# ==========================

resultado = {
    "modelo_nuevo": os.path.basename(modelo_nuevo_path),
    "version_nuevo": version_nuevo,
    "accuracy_new": accuracy_new,
    "f1_new": f1_new,
    "accuracy_old": accuracy_old,
    "f1_old": f1_old,
    "mejora": mejora,
    "promovido": mejora,
    "confusion_matrix": cm.tolist()
}

print(json.dumps(resultado))