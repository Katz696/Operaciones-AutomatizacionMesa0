"""
Entrenamiento de modelo de categoría principal con contexto de cliente
Arquitectura: sentence-transformers (embeddings) + LogisticRegression

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

DATASET_PATH    = "../data/dataset-training-category.csv"
CATEGORIAS_PATH = "../data/categorias-activas.csv"    # id;name;padCategories_id;path;inactive
CLIENTES_PATH   = "../data/clientes.csv"      # id;name
MODEL_OUTPUT_DIR = "../models/"

EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

BATCH_SIZE   = 64    # Reducir a 32 si hay problemas de memoria
TEST_SIZE    = 0.2
RANDOM_STATE = 42
MIN_TICKETS  = 5     # Mínimo de tickets por categoría para incluirla


# =============================================================================
# 1. CARGAR DATOS
# =============================================================================

print("=" * 60)
print("  MODELO DE CATEGORÍA PRINCIPAL (con contexto cliente)")
print("=" * 60)

data  = pd.read_csv(DATASET_PATH,    sep=";")
cats  = pd.read_csv(CATEGORIAS_PATH, sep=";")
clientes = pd.read_csv(CLIENTES_PATH, sep=";")

print(f"\n[1/7] Archivos cargados:")
print(f"    Tickets    : {len(data):,}")
print(f"    Categorías : {len(cats):,}")
print(f"    Clientes   : {len(clientes):,}")


# =============================================================================
# 2. RESOLVER JERARQUÍA DE CATEGORÍAS + CLIENTE
# =============================================================================

print(f"\n[2/7] Resolviendo jerarquía y relaciones...")

# Categorías padre (sin padCategories_id)
cats_padre = cats[cats["padCategories_id"].isna()][["id", "name"]].copy()
cats_padre.columns = ["cat_padre_id", "category_name"]
print(f"    Categorías padre activas: {len(cats_padre)}")

# Mapa subcategoría → padre
cats_sub      = cats[cats["padCategories_id"].notna()][["id", "padCategories_id"]].copy()
mapa_sub_padre = dict(zip(cats_sub["id"], cats_sub["padCategories_id"]))

ids_padre_set = set(cats_padre["cat_padre_id"].values)

def resolver_categoria_padre(cat_id):
    if pd.isna(cat_id):
        return None
    if cat_id in ids_padre_set:
        return cat_id
    return mapa_sub_padre.get(cat_id, None)

# Mapa cliente UUID → nombre legible
mapa_clientes = dict(zip(clientes["id"], clientes["name"]))

# Resolver categoría padre en cada ticket
data["cat_padre_id"]   = data["Category_id"].apply(resolver_categoria_padre)
data["cliente_nombre"] = data["Client_id"].map(mapa_clientes)

# Merge con nombre de categoría
data = data.merge(cats_padre, on="cat_padre_id", how="left")

# Diagnóstico antes de filtrar
sin_cat    = data["category_name"].isna().sum()
sin_cliente = data["cliente_nombre"].isna().sum()
print(f"    Tickets sin categoría resoluble : {sin_cat:,}")
print(f"    Tickets sin cliente resoluble   : {sin_cliente:,}")

# Conservar solo tickets con categoría Y cliente válidos
antes = len(data)
data  = data.dropna(subset=["category_name", "cliente_nombre"])
print(f"    Tickets válidos: {len(data):,}  (descartados: {antes - len(data):,})")

# Mapa inferido: cliente → set de categorías que le pertenecen
mapa_cliente_categorias = (
    data.groupby("cliente_nombre")["category_name"]
    .apply(lambda x: sorted(x.unique().tolist()))
    .to_dict()
)
print(f"    Clientes con categorías mapeadas: {len(mapa_cliente_categorias)}")

# # Visualizar mapa cliente → categorías
# print(f"\n  {'CLIENTE':<30} {'CATEGORÍAS':>5}")
# print("  " + "─" * 50)
# for cliente, categorias in sorted(mapa_cliente_categorias.items()):
#     print(f"  {cliente:<30} {len(categorias):>3} categorías")
#     for cat in categorias:
#         print(f"    {'':4}→ {cat}")
#     print()


# =============================================================================
# 3. PREPROCESAMIENTO DE TEXTO
# =============================================================================

print(f"\n[3/7] Preprocesando texto...")

data["titulo_limpio"] = data["IncidentTitle"].fillna("").apply(limpiar_texto)
data["desc_limpia"]   = data["Description"].fillna("").apply(limpiar_texto)

# Prefijo de cliente + título duplicado (mayor peso semántico) + descripción
# Formato: "[CLIENTE] título título descripción"
data["texto"] = (
    "[" + data["cliente_nombre"] + "] " +
    data["titulo_limpio"] + " " +
    data["titulo_limpio"] + " " +
    data["titulo_limpio"] + " " +
    data["desc_limpia"]
).str[:1200]

print(f"    Longitud media del texto: {data['texto'].str.len().mean():.0f} caracteres")
print(f"    Ejemplo: {data['texto'].iloc[0][:120]}...")


# =============================================================================
# 4. FILTRAR CLASES CON POCOS TICKETS + ENCODING
# =============================================================================

print(f"\n[4/7] Filtrando clases y codificando etiquetas...")

conteo = data["category_name"].value_counts()

# Diagnóstico de distribución
print(f"    Distribución por rangos:")
print(f"      > 1000 tickets : {(conteo >= 1000).sum()} categorías")
print(f"      100 - 999      : {((conteo >= 100) & (conteo < 1000)).sum()} categorías")
print(f"      10 - 99        : {((conteo >= 10)  & (conteo < 100)).sum()} categorías")
print(f"      {MIN_TICKETS} - 9          : {((conteo >= MIN_TICKETS) & (conteo < 10)).sum()} categorías")

# Categorías eliminadas
eliminadas = conteo[conteo < MIN_TICKETS]
if len(eliminadas):
    print(f"\n    Categorías eliminadas por < {MIN_TICKETS} tickets ({len(eliminadas)}):")
    print(f"    {', '.join(eliminadas.index.tolist())}")

cats_validas = conteo[conteo >= MIN_TICKETS].index
antes_filtro = len(data)
data = data[data["category_name"].isin(cats_validas)]
print(f"\n    Tickets tras filtro : {len(data):,}  (descartados: {antes_filtro - len(data):,})")

# Actualizar mapa cliente → categorías tras el filtro
mapa_cliente_categorias = (
    data.groupby("cliente_nombre")["category_name"]
    .apply(lambda x: sorted(x.unique().tolist()))
    .to_dict()
)

X = data["texto"].values
y = data["category_name"].values

le = LabelEncoder()
y_encoded = le.fit_transform(y)
print(f"    Clases finales codificadas: {len(le.classes_)}")


# =============================================================================
# 5. SPLIT
# =============================================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y_encoded,
    test_size=TEST_SIZE,
    random_state=RANDOM_STATE,
    stratify=y_encoded
)

print(f"\n[5/7] Split realizado:")
print(f"    Train: {len(X_train):,} | Test: {len(X_test):,}")


# =============================================================================
# 6. GENERACIÓN DE EMBEDDINGS
# =============================================================================

print(f"\n[6/7] Cargando modelo de embeddings: {EMBEDDING_MODEL}")

embedder = SentenceTransformer(EMBEDDING_MODEL)

import torch
device = "cuda" if torch.cuda.is_available() else "cpu"
embedder = embedder.to(device)
print(f"    Dispositivo: {device.upper()}")

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

print(f"    Shape embeddings: {X_train_emb.shape}")


# =============================================================================
# 7. ENTRENAMIENTO DEL CLASIFICADOR
# =============================================================================

print(f"\n[7/7] Entrenando clasificador...")

clf = LogisticRegression(
    max_iter=1000,
    C=8.0,
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

acc  = accuracy_score(y_test, y_pred)
f1_w = f1_score(y_test, y_pred, average="weighted")
f1_m = f1_score(y_test, y_pred, average="macro")

print("\n" + "=" * 60)
print("  RESULTADOS")
print("=" * 60)
print(f"  Accuracy   : {acc:.4f}  ({acc*100:.1f}%)")
print(f"  F1 Weighted: {f1_w:.4f}")
print(f"  F1 Macro   : {f1_m:.4f}")
print("=" * 60)

print("\nReporte por categoría:")
print(classification_report(y_test, y_pred, target_names=le.classes_, zero_division=0))


# =============================================================================
# GUARDAR MODELO
# =============================================================================

version      = datetime.now().strftime("%Y%m%d_%H%M")
nombre_model = f"{MODEL_OUTPUT_DIR}modelo_categoria_{version}.pkl"

joblib.dump(
    {
        "embedding_model_name"    : EMBEDDING_MODEL,
        "classifier"              : clf,
        "label_encoder"           : le,
        "mapa_cliente_categorias" : mapa_cliente_categorias,  # cliente → [categorías válidas]
        "mapa_clientes"           : mapa_clientes,            # UUID → nombre cliente
        "version"                 : version,
        "metricas": {
            "accuracy"   : round(acc,  4),
            "f1_weighted": round(f1_w, 4),
            "f1_macro"   : round(f1_m, 4),
            "n_clases"   : len(le.classes_),
            "n_train"    : len(X_train),
            "n_test"     : len(X_test),
        }
    },
    nombre_model
)

print(f"\nModelo guardado: {nombre_model}")
print("Listo.\n")