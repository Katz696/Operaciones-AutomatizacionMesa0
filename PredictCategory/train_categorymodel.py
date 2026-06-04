"""
Entrenamiento de modelo de categoría principal
Arquitectura: sentence-transformers (embeddings) + LogisticRegression
Modelo base: paraphrase-multilingual-MiniLM-L12-v2

"""
import numpy as np
import pandas as pd
import joblib
from datetime import datetime

from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report
)

from text_preprocessing import limpiar_texto


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

DATASET_PATH       = "../data/dataset-training-category.csv"
CATEGORIAS_PATH    = "../data/categorias-activas.csv"       
MODEL_OUTPUT_DIR   = "../models/"

# Modelo de embeddings multilingüe ligero
EMBEDDING_MODEL    = "paraphrase-multilingual-MiniLM-L12-v2"

BATCH_SIZE         = 64    # Reducir a 32 si problemas de memoria
TEST_SIZE          = 0.2
RANDOM_STATE       = 42


# =============================================================================
# 1. CARGAR Y PREPARAR DATOS
# =============================================================================

print("=" * 60)
print("  MODELO DE CATEGORÍA PRINCIPAL")
print("=" * 60)

# --- Dataset de tickets ---
data = pd.read_csv(DATASET_PATH, sep=";")
print(f"\n[1/6] Dataset cargado: {len(data):,} registros")


# --- Tabla de categorías para obtener solo las categorías PADRE (sin padCategories_id) ---
cats = pd.read_csv(CATEGORIAS_PATH, sep=";")

# Categorías padre = las que tienen padCategories_id NULL/vacío
cats_padre = cats[cats["padCategories_id"].isna()][["id", "name"]].copy()
cats_padre.columns = ["Category_id", "category_name"]

print(f"    Categorías padre encontradas: {len(cats_padre)}")

# --- Merge: quedarse solo con tickets que tienen categoría padre directa ---
# Si Category_id en el dataset ya apunta a la categoría padre, hacer merge directo.
# Si Category_id apunta a subcategorías, necesitas resolverlo subiendo al padre:

# Mapa subcategoría → categoría padre
cats_sub = cats[cats["padCategories_id"].notna()][["id", "padCategories_id"]].copy()
mapa_sub_padre = dict(zip(cats_sub["id"], cats_sub["padCategories_id"]))

# ── Diagnóstico de descarte ──────────────────────────────────
print("\n  >> DIAGNÓSTICO DE DESCARTE <<")

# 1. Tickets sin Category_id
sin_categoria = data["Category_id"].isna().sum()
print(f"  Tickets sin Category_id (NULL): {sin_categoria:,}")

# 2. IDs únicos en el dataset
ids_en_tickets = set(data["Category_id"].dropna().unique())

# 3. IDs disponibles en categorias.csv (padres e hijos)
ids_en_cats    = set(cats["id"].unique())
ids_solo_padre = set(cats_padre["Category_id"].unique())

# 4. IDs del dataset que no existen en categorias.csv
ids_huerfanos = ids_en_tickets - ids_en_cats
print(f"  Category_ids en tickets que NO existen en categorias.csv: {len(ids_huerfanos):,}")

# 5. IDs del dataset que son subcategorías sin padre resoluble
ids_sub_sin_padre = ids_en_tickets & (ids_en_cats - ids_solo_padre) - set(mapa_sub_padre.keys())
print(f"  Subcategorías sin padre resoluble: {len(ids_sub_sin_padre):,}")

# 6. Muestra algunos IDs huérfanos para inspección
if ids_huerfanos:
    print(f"\n  Ejemplo de IDs huérfanos (primeros 5):")
    for i in list(ids_huerfanos)[:5]:
        print(f"    {i}")
print("─" * 60)

# Cuántos tickets tiene cada ID huérfano
tickets_huerfanos = data[data["Category_id"].isin(ids_huerfanos)]
conteo_huerfanos = tickets_huerfanos["Category_id"].value_counts()

print(f"\n  Total tickets afectados por IDs huérfanos: {len(tickets_huerfanos):,}")
print(f"\n  Top 10 IDs huérfanos con más tickets:")
print(conteo_huerfanos.head(10).to_string())

def resolver_categoria_padre(cat_id):
    """Sube un nivel si cat_id es subcategoría."""
    if pd.isna(cat_id):
        return None
    # Si ya es padre, devolver tal cual
    if cat_id in cats_padre["Category_id"].values:
        return cat_id
    # Si es subcategoría, devolver su padre
    return mapa_sub_padre.get(cat_id, cat_id)

data["category_padre_id"] = data["Category_id"].apply(resolver_categoria_padre)

# Merge para obtener nombre legible
data = data.merge(cats_padre, left_on="category_padre_id", right_on="Category_id", how="left")

# Descartar tickets sin categoría asignable
antes = len(data)
data = data.dropna(subset=["category_name"])
print(f"    Tickets con categoría válida: {len(data):,}  (descartados: {antes - len(data):,})")

dist = data["category_name"].value_counts()
print(f"    Categorías activas: {dist.nunique()}")
print(f"    Top 5 categorías:\n{dist.head().to_string()}")


# =============================================================================
# 2. PREPROCESAMIENTO DE TEXTO
# =============================================================================

print("\n[2/6] Preprocesando texto...")

data["titulo_limpio"]      = data["IncidentTitle"].fillna("").apply(limpiar_texto)
data["descripcion_limpia"] = data["Description"].fillna("").apply(limpiar_texto)

# El título pesa más → se repite para dar más relevancia semántica
data["texto"] = (
    data["titulo_limpio"] + " " +
    # data["titulo_limpio"] + " " +   # título duplicado = mayor peso
    data["descripcion_limpia"]
)

# Truncar a 512 tokens aproximados (límite del modelo de embeddings)
data["texto"] = data["texto"].str[:1200]

X = data["texto"].values
y = data["category_name"].values

print(f"    Longitud media del texto: {data['texto'].str.len().mean():.0f} caracteres")


# =============================================================================
# 3. ENCODING DE ETIQUETAS
# =============================================================================

# Filtrar categorías con menos de 5 tickets (muy pocas para entrenar bien)
conteo = data["category_name"].value_counts()
categorias_validas = conteo[conteo >= 5].index
antes_filtro = len(data)
data = data[data["category_name"].isin(categorias_validas)]
print(f"    Categorías eliminadas por pocos tickets: {len(conteo) - len(categorias_validas)}")
print(f"    Tickets tras filtro: {len(data):,}  (descartados: {antes_filtro - len(data):,})")

X = data["texto"].values
y = data["category_name"].values

# Categorías eliminadas
eliminadas = conteo[conteo < 5]
print(f"\n    Categorías eliminadas ({len(eliminadas)}):")
print(eliminadas.to_string())

# Categorías que quedaron
print(f"\n    Categorías activas ({len(categorias_validas)}):")
print(conteo[conteo >= 30].to_string())

le = LabelEncoder()
y_encoded = le.fit_transform(y)
print(f"\n[3/6] Clases codificadas: {len(le.classes_)}")


# =============================================================================
# 4. SPLIT
# =============================================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y_encoded,
    test_size=TEST_SIZE,
    random_state=RANDOM_STATE,
    stratify=y_encoded
)

print(f"\n[4/6] Split realizado:")
print(f"    Train: {len(X_train):,} | Test: {len(X_test):,}")


# =============================================================================
# 5. GENERACIÓN DE EMBEDDINGS
# =============================================================================

print(f"\n[5/6] Cargando modelo de embeddings: {EMBEDDING_MODEL}")
print("    (Primera ejecución descarga ~120MB automáticamente)")

embedder = SentenceTransformer(EMBEDDING_MODEL)

# Detectar GPU automáticamente (usa tu GTX 1650 si está disponible)
device = "cuda" if __import__("torch").cuda.is_available() else "cpu"
embedder = embedder.to(device)
print(f"    Dispositivo detectado: {device.upper()}")

print("    Generando embeddings de entrenamiento...")
X_train_emb = embedder.encode(
    X_train.tolist(),
    batch_size=BATCH_SIZE,
    show_progress_bar=True,
    device=device,
    convert_to_numpy=True
)

print("    Generando embeddings de test...")
X_test_emb = embedder.encode(
    X_test.tolist(),
    batch_size=BATCH_SIZE,
    show_progress_bar=True,
    device=device,
    convert_to_numpy=True
)

print(f"    Shape embeddings: {X_train_emb.shape}")  # (n_samples, 384)


# =============================================================================
# 6. ENTRENAMIENTO DEL CLASIFICADOR
# =============================================================================

print("\n[6/6] Entrenando clasificador...")

clf = LogisticRegression(
    max_iter=1000,
    C=4.0,
    solver="lbfgs",
    class_weight="balanced",
    n_jobs=-1,
    random_state=RANDOM_STATE,
    verbose=1
)

clf.fit(X_train_emb, y_train)


# =============================================================================
# EVALUACIÓN
# =============================================================================

y_pred = clf.predict(X_test_emb)

acc    = accuracy_score(y_test, y_pred)
f1_w   = f1_score(y_test, y_pred, average="weighted")
f1_m   = f1_score(y_test, y_pred, average="macro")

print("\n" + "=" * 60)
print("  RESULTADOS")
print("=" * 60)
print(f"  Accuracy :       {acc:.4f}  ({acc*100:.1f}%)")
print(f"  F1 Weighted:     {f1_w:.4f}")
print(f"  F1 Macro:        {f1_m:.4f}")
print("=" * 60)

# Reporte detallado por clase
nombres_clases = le.inverse_transform(sorted(set(y_test)))
print("\nReporte por categoría:")
print(
    classification_report(
        y_test,
        y_pred,
        target_names=le.classes_,
        zero_division=0
    )
)


# =============================================================================
# GUARDAR MODELO
# =============================================================================

version      = datetime.now().strftime("%Y%m%d_%H%M")
nombre_model = f"{MODEL_OUTPUT_DIR}modelo_categoria_{version}.pkl"

joblib.dump(
    {
        "embedding_model_name": EMBEDDING_MODEL,   # Para recargarlo en inferencia
        "classifier":           clf,
        "label_encoder":        le,
        "version":              version,
        "metricas": {
            "accuracy":     round(acc, 4),
            "f1_weighted":  round(f1_w, 4),
            "f1_macro":     round(f1_m, 4),
            "n_clases":     len(le.classes_),
            "n_train":      len(X_train),
            "n_test":       len(X_test),
        }
    },
    nombre_model
)

print(f"\nModelo guardado: {nombre_model}")
print("Listo.\n")