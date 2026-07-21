import joblib
import glob
import os
import json
import sys


# ==========================
# Leer métricas del modelo actual
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
# Buscar modelo nuevo
# ==========================

modelos = glob.glob("models/modelo_categoria_*.pkl")

if not modelos:
    raise Exception("No hay modelos de categoria entrenados")

modelo_nuevo_path = sorted(modelos)[-1]

modelo_nuevo_data = joblib.load(modelo_nuevo_path)

if "classifier" not in modelo_nuevo_data or "metricas" not in modelo_nuevo_data:
    raise Exception("Modelo inválido: faltan 'classifier' o 'metricas'")

version_nuevo = modelo_nuevo_data.get("version", "sin_version")
metricas_nuevo = modelo_nuevo_data["metricas"]

# ==========================
# Métricas del modelo nuevo
# ==========================

accuracy_new = metricas_nuevo["accuracy"]
f1_new_weighted = metricas_nuevo["f1_weighted"]
f1_new_macro = metricas_nuevo["f1_macro"]

# ==========================
# Comparación
# ==========================

mejora = f1_new_weighted > f1_old

# ==========================
# Resultado final
# ==========================

resultado = {
    "dimension": "categoria",
    "modelo_nuevo": os.path.basename(modelo_nuevo_path),
    "version_nuevo": version_nuevo,
    "accuracy_new": accuracy_new,
    "f1_new": f1_new_weighted,
    "f1_new_macro": f1_new_macro,
    "accuracy_old": accuracy_old,
    "f1_old": f1_old,
    "n_clases": metricas_nuevo.get("n_clases"),
    "n_train": metricas_nuevo.get("n_train"),
    "n_test": metricas_nuevo.get("n_test"),
    "mejora": mejora,
    "promovido": mejora
}

print(json.dumps(resultado))