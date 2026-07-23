import numpy as np
import pandas as pd
import joblib
import json
from datetime import datetime

from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, f1_score, classification_report
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV

from text_preprocessing import limpiar_texto


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

DATASET_PATH    = "../data/dataset-training-category.csv"
CATEGORIAS_PATH = "../data/categorias-activas.csv"
CLIENTES_PATH   = "../data/clientes.csv"   
MODEL_OUTPUT_DIR = "../models/"

EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

BATCH_SIZE   = 64
TEST_SIZE    = 0.2
RANDOM_STATE = 42
MIN_TICKETS  = 30


# =============================================================================
# 1. CARGAR DATOS
# =============================================================================

print("=" * 60)
print("  MODELO DE SUBCATEGORÍA (categoría hijo)")
print("=" * 60)

data     = pd.read_csv(DATASET_PATH,    sep=";")
cats     = pd.read_csv(CATEGORIAS_PATH, sep=";")
clientes = pd.read_csv(CLIENTES_PATH,   sep=";")

print(f"\n[1/7] Archivos cargados:")
print(f"    Tickets    : {len(data):,}")
print(f"    Categorías : {len(cats):,}")
print(f"    Clientes   : {len(clientes):,}")


# =============================================================================
# 2. SEPARAR PADRES E HIJOS + CONSTRUIR MAPAS
# =============================================================================

print(f"\n[2/7] Construyendo mapas de jerarquía...")

# Separar categorías padre e hijo
cats_padre = cats[cats["padCategories_id"].isna()].copy()
cats_hijo  = cats[cats["padCategories_id"].notna()].copy()

# Mapa: id_hijo → nombre_hijo
mapa_hijo_nombre = dict(zip(cats_hijo["id"], cats_hijo["name"]))

# Mapa: id_hijo → id_padre
mapa_hijo_padre  = dict(zip(cats_hijo["id"], cats_hijo["padCategories_id"]))

# Mapa: id_padre → nombre_padre
mapa_padre_nombre = dict(zip(cats_padre["id"], cats_padre["name"]))

# Mapa: cliente UUID → nombre
mapa_clientes = dict(zip(clientes["id"], clientes["name"]))

ids_hijos = set(cats_hijo["id"].values)

print(f"    Categorías padre : {len(cats_padre):,}")
print(f"    Categorías hijo  : {len(cats_hijo):,}")


# =============================================================================
# 3. FILTRAR SOLO TICKETS QUE APUNTAN A SUBCATEGORÍA HIJO
# =============================================================================

print(f"\n[3/7] Filtrando tickets con subcategoría hijo...")

antes = len(data)
data  = data[data["Category_id"].isin(ids_hijos)].copy()
print(f"    Tickets con subcategoría hijo: {len(data):,}  (descartados: {antes - len(data):,})")

# Resolver nombres
data["subcategoria_nombre"] = data["Category_id"].map(mapa_hijo_nombre)
data["cat_padre_id"]        = data["Category_id"].map(mapa_hijo_padre)
data["cat_padre_nombre"]    = data["cat_padre_id"].map(mapa_padre_nombre)

data["cliente_nombre"]      = data["Client_id"].astype(str).str.upper().map(mapa_clientes)

# Descartar tickets sin resolución completa
antes = len(data)
data  = data.dropna(subset=["subcategoria_nombre", "cat_padre_nombre", "cliente_nombre"])
print(f"    Tickets con resolución completa: {len(data):,}  (descartados: {antes - len(data):,})")


# =============================================================================
# 4. PREPROCESAMIENTO DE TEXTO
# =============================================================================

print(f"\n[4/7] Preprocesando texto...")

data["titulo_limpio"] = data["IncidentTitle"].fillna("").apply(limpiar_texto)
data["desc_limpia"]   = data["Description"].fillna("").apply(limpiar_texto)

# Formato: [CLIENTE][CATEGORÍA PADRE] título título título descripción
data["texto"] = (
    "[" + data["cliente_nombre"]    + "]" +
    "[" + data["cat_padre_nombre"]  + "] " +
    data["titulo_limpio"] + " " +
    data["titulo_limpio"] + " " +
    data["titulo_limpio"] + " " +
    data["desc_limpia"]
).str[:1200]

print(f"    Longitud media del texto: {data['texto'].str.len().mean():.0f} caracteres")
print(f"    Ejemplo: {data['texto'].iloc[0][:130]}...")


# =============================================================================
# 5. FILTRAR CLASES CON POCOS TICKETS + ENCODING
# =============================================================================

print(f"\n[5/7] Filtrando clases y codificando etiquetas...")

conteo = data["subcategoria_nombre"].value_counts()

print(f"    Distribución por rangos:")
print(f"      > 1000 tickets : {(conteo >= 1000).sum()} subcategorías")
print(f"      100 - 999      : {((conteo >= 100) & (conteo < 1000)).sum()} subcategorías")
print(f"      10 - 99        : {((conteo >= 10)  & (conteo < 100)).sum()} subcategorías")
print(f"      {MIN_TICKETS} - 9          : {((conteo >= MIN_TICKETS) & (conteo < 10)).sum()} subcategorías")

eliminadas = conteo[conteo < MIN_TICKETS]
if len(eliminadas):
    print(f"\n    Subcategorías eliminadas por < {MIN_TICKETS} tickets ({len(eliminadas)}):")
    for nombre, cnt in eliminadas.items():
        print(f"      - {nombre}: {cnt} ticket(s)")

subs_validas = conteo[conteo >= MIN_TICKETS].index
antes_filtro = len(data)
data = data[data["subcategoria_nombre"].isin(subs_validas)]
print(f"\n    Tickets tras filtro : {len(data):,}  (descartados: {antes_filtro - len(data):,})")

# Mapa
# Clave compuesta para filtrar en inferencia con máxima precisión
mapa_padre_subcategorias = (
    data.groupby(["cliente_nombre", "cat_padre_nombre"])["subcategoria_nombre"]
    .apply(lambda x: sorted(x.unique().tolist()))
    .to_dict()
)

# También mapa plano: cat_padre → subcategorías
mapa_solo_padre_subcats = (
    data.groupby("cat_padre_nombre")["subcategoria_nombre"]
    .apply(lambda x: sorted(x.unique().tolist()))
    .to_dict()
)

print(f"    Combinaciones (cliente, padre) mapeadas: {len(mapa_padre_subcategorias)}")

# Exportar mapa para revisión
with open("../models/mapa_subcategorias.json", "w", encoding="utf-8") as f:
    json.dump(
        {
            "por_cliente_y_padre": {str(k): v for k, v in mapa_padre_subcategorias.items()},
            "por_padre"          : mapa_solo_padre_subcats
        },
        f, ensure_ascii=False, indent=2
    )
print(f"    Mapa exportado: models/mapa_subcategorias.json")

X = data["texto"].values
y = data["subcategoria_nombre"].values

le = LabelEncoder()
y_encoded = le.fit_transform(y)
print(f"    Subcategorías finales codificadas: {len(le.classes_)}")


# =============================================================================
# 6. SPLIT
# =============================================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y_encoded,
    test_size=TEST_SIZE,
    random_state=RANDOM_STATE,
    stratify=y_encoded
)

print(f"\n[6/7] Split realizado:")
print(f"    Train: {len(X_train):,} | Test: {len(X_test):,}")


# =============================================================================
# 7. EMBEDDINGS + ENTRENAMIENTO
# =============================================================================

print(f"\n[7/7] Generando embeddings y entrenando...")

import torch
device = "cuda" if torch.cuda.is_available() else "cpu"

embedder = SentenceTransformer(EMBEDDING_MODEL)
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
print("    Entrenando clasificador...")

svc = LinearSVC(
    C=0.5,
    max_iter=2000,
    class_weight="balanced",
    random_state=RANDOM_STATE
)

# CalibratedClassifierCV para obtener probabilidades
clf = CalibratedClassifierCV(svc, cv=3)

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

print("\nReporte por subcategoría:")
print(classification_report(y_test, y_pred, target_names=le.classes_, zero_division=0))


# =============================================================================
# GUARDAR MODELO
# =============================================================================

version      = datetime.now().strftime("%Y%m%d_%H%M")
nombre_model = f"{MODEL_OUTPUT_DIR}modelo_subcategoria_{version}.pkl"

joblib.dump(
    {
        "embedding_model_name"       : EMBEDDING_MODEL,
        "classifier"                 : clf,
        "label_encoder"              : le,
        "mapa_padre_subcategorias"   : mapa_padre_subcategorias,   
        "mapa_solo_padre_subcats"    : mapa_solo_padre_subcats,    
        "mapa_clientes"              : mapa_clientes,       
        "mapa_padre_nombre"          : mapa_padre_nombre,          
        "version"                    : version,
        "metricas": {
            "accuracy"    : round(acc,  4),
            "f1_weighted" : round(f1_w, 4),
            "f1_macro"    : round(f1_m, 4),
            "n_clases"    : len(le.classes_),
            "n_train"     : len(X_train),
            "n_test"      : len(X_test),
        }
    },
    nombre_model
)

print(f"\nModelo guardado: {nombre_model}")
print("Listo.\n")