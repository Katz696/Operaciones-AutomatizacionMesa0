"""
Entrenamiento de modelo de categoría principal con contexto de cliente
Arquitectura: sentence-transformers (embeddings) + LogisticRegression

"""

import json
import os
from datetime import datetime

import numpy as np
import pandas as pd
import joblib
import torch

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
from relacion_clientes import cargar_relacion_cliente_categorias

EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

BATCH_SIZE   = 64    
TEST_SIZE    = 0.2
RANDOM_STATE = 42
MIN_TICKETS  = 5


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

<<<<<<< HEAD
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

BATCH_SIZE   = 64
TEST_SIZE    = 0.2
RANDOM_STATE = 42

# Mínimo TÉCNICO (no es criterio de calidad): por debajo de esto no se puede
# estratificar el split. Las categorías con menos tickets siguen en los mapas.
MIN_TICKETS_TECNICO = 5

# Criterio de confianza: tras una primera pasada, las clases con F1 < umbral en test.
UMBRAL_F1_CONFIANZA = 0.50

DATASET_PATH     = "../data/dataset-training-category.csv"
CATEGORIAS_PATH  = "../data/categorias-activas.csv"
CLIENTES_PATH    = "../data/clientes.csv"
RELACION_PATH    = "../data/clientes-categorias.csv"
MODEL_OUTPUT_DIR = "../models/"

os.makedirs(MODEL_OUTPUT_DIR, exist_ok=True)


def crear_clasificador():
    return LogisticRegression(
        max_iter=1000,
        C=8.0,
        solver="lbfgs",
        class_weight="balanced",
        n_jobs=-1,
        random_state=RANDOM_STATE,
        verbose=1
    )


=======
DATASET_PATH    = "../data/dataset-training-category.csv"
CATEGORIAS_PATH = "../data/categorias-activas.csv"  
CLIENTES_PATH   = "../data/clientes.csv"     
MODEL_OUTPUT_DIR = "../models/"

>>>>>>> 0cd777d9e435266f99d7e0b5f43263882b102b18
# =============================================================================
# 1. CARGAR DATOS Y NORMALIZAR IDENTIFICADORES
# =============================================================================

<<<<<<< HEAD
print("\n[1/8] Cargando archivos...")
=======
print("\n[1/7] Cargando archivos...")
>>>>>>> 0cd777d9e435266f99d7e0b5f43263882b102b18

data = pd.read_csv(DATASET_PATH, sep=";")
cats = pd.read_csv(CATEGORIAS_PATH, sep=";")
clientes = pd.read_csv(CLIENTES_PATH, sep=";")
relacion = cargar_relacion_cliente_categorias(RELACION_PATH)

# Limpiar espacios accidentales en los encabezados
data.columns = data.columns.str.strip()
cats.columns = cats.columns.str.strip()
clientes.columns = clientes.columns.str.strip()

# Verificar columnas requeridas
requeridas_data = {
    "IncidentTitle", "Description", "Category_id", "Client_id"
}
requeridas_cats = {"id", "name", "padCategories_id"}
requeridas_clientes = {"id", "name"}

for nombre, df, requeridas in [
    ("tickets", data, requeridas_data),
    ("categorías", cats, requeridas_cats),
    ("clientes", clientes, requeridas_clientes),
]:
    faltantes = requeridas - set(df.columns)
    if faltantes:
        raise ValueError(
            f"Columnas faltantes en {nombre}: {sorted(faltantes)}. "
            f"Columnas encontradas: {df.columns.tolist()}"
        )

# Normalizar UUID del dataset de tickets
for columna in ["Category_id", "Client_id"]:
    data[columna] = (
        data[columna]
        .astype("string")
        .str.strip()
        .str.upper()
    )

# Normalizar UUID del catálogo de categorías
for columna in ["id", "padCategories_id"]:
    cats[columna] = (
        cats[columna]
        .astype("string")
        .str.strip()
        .str.upper()
    )

# Normalizar UUID del catálogo de clientes
clientes["id"] = (
    clientes["id"]
    .astype("string")
    .str.strip()
    .str.upper()
)

<<<<<<< HEAD
print(f"    Tickets cargados            : {len(data):,}")
print(f"    Categorías cargadas         : {len(cats):,}")
print(f"    Clientes cargados           : {len(clientes):,}")
print(f"    Relación cliente-categoría  : {len(relacion):,} filas "
      f"({relacion['cliente_id'].nunique():,} clientes)")
=======
print(f"    Tickets cargados    : {len(data):,}")
print(f"    Categorías cargadas : {len(cats):,}")
print(f"    Clientes cargados   : {len(clientes):,}")
>>>>>>> 0cd777d9e435266f99d7e0b5f43263882b102b18
print("    UUID normalizados a mayúsculas.")


# =============================================================================
# 2. RESOLVER JERARQUÍA DE CATEGORÍAS + CLIENTE
# =============================================================================

print(f"\n[2/8] Resolviendo jerarquía y relaciones...")

# Categorías padre (sin padCategories_id)
cats_padre = cats[cats["padCategories_id"].isna()][["id", "name"]].copy()
cats_padre.columns = ["cat_padre_id", "category_name"]
print(f"    Categorías padre activas: {len(cats_padre)}")

mapa_padre_nombre = dict(zip(cats_padre["cat_padre_id"], cats_padre["category_name"]))
ids_padre_set     = set(cats_padre["cat_padre_id"].values)
ids_activas       = set(cats["id"].values)

# Catálogo completo de categorías padre activas (lo que la API debe poder mostrar)
catalogo_categorias_activas = sorted(cats_padre["category_name"].dropna().unique().tolist())

# Mapa subcategoría → padre
cats_sub       = cats[cats["padCategories_id"].notna()][["id", "padCategories_id"]].copy()
mapa_sub_padre = dict(zip(cats_sub["id"], cats_sub["padCategories_id"]))

def resolver_categoria_padre(cat_id):
    if pd.isna(cat_id):
        return None
    if cat_id in ids_padre_set:
        return cat_id
    return mapa_sub_padre.get(cat_id, None)

# Mapa cliente UUID → nombre legible (clientes.csv + clientes que solo vengan en la relación)
mapa_clientes = dict(zip(clientes["id"], clientes["name"]))
agregados = 0
for cid, nombre in relacion[["cliente_id", "cliente_nombre_rel"]].drop_duplicates("cliente_id").itertuples(index=False):
    if cid not in mapa_clientes and pd.notna(nombre):
        mapa_clientes[cid] = nombre
        agregados += 1
if agregados:
    print(f"    Clientes añadidos desde la relación (no estaban en clientes.csv): {agregados}")

# --- Pares (cliente, categoría padre) según la RELACIÓN real -----------------
rel = relacion[relacion["categoria_id"].isin(ids_activas)].copy()
print(f"    Relaciones con categoría inactiva/desconocida (ignoradas): "
      f"{len(relacion) - len(rel):,}")

rel["cat_padre_id"]    = rel["categoria_id"].apply(resolver_categoria_padre)
rel["category_name"]   = rel["cat_padre_id"].map(mapa_padre_nombre)
rel["cliente_nombre"]  = rel["cliente_id"].map(mapa_clientes)
rel = rel.dropna(subset=["category_name", "cliente_nombre"])

# Un cliente con una subcategoría disponible implica que su padre también lo está
pares_relacion = set(zip(rel["cliente_nombre"], rel["category_name"]))
print(f"    Pares (cliente, categoría padre) en la relación: {len(pares_relacion):,}")

# Resolver categoría padre en cada ticket
data["cat_padre_id"]   = data["Category_id"].apply(resolver_categoria_padre)
<<<<<<< HEAD
=======

>>>>>>> 0cd777d9e435266f99d7e0b5f43263882b102b18
data["cliente_nombre"] = data["Client_id"].astype(str).str.upper().map(mapa_clientes)

# Merge con nombre de categoría
data = data.merge(cats_padre, on="cat_padre_id", how="left")

# Diagnóstico antes de filtrar
sin_cat     = data["category_name"].isna().sum()
sin_cliente = data["cliente_nombre"].isna().sum()
print(f"    Tickets sin categoría resoluble : {sin_cat:,}")
print(f"    Tickets sin cliente resoluble   : {sin_cliente:,}")

# Conservar solo tickets con categoría Y cliente válidos
antes = len(data)
data  = data.dropna(subset=["category_name", "cliente_nombre"])
if data.empty:
    raise ValueError(
        "No quedaron tickets con categoría y cliente válidos. "
        "Revisa la coincidencia de Category_id, padCategories_id "
        "y Client_id después de normalizar los UUID."
    )
print(f"    Tickets válidos: {len(data):,}  (descartados: {antes - len(data):,})")

# --- Pares observados en tickets (complemento de la relación) ----------------
pares_tickets = set(zip(data["cliente_nombre"], data["category_name"]))
fuera_de_relacion = pares_tickets - pares_relacion
print(f"    Pares vistos en tickets pero ausentes en la relación: {len(fuera_de_relacion):,}")

<<<<<<< HEAD
# MAPA COMPLETO: relación real ∪ observado en tickets (NO depende de lo aprendido)
_tmp = {}
for cli, cat in pares_relacion | pares_tickets:
    _tmp.setdefault(cli, set()).add(cat)
mapa_cliente_categorias = {k: sorted(v) for k, v in sorted(_tmp.items())}
print(f"    Clientes con categorías mapeadas: {len(mapa_cliente_categorias)}")

=======
>>>>>>> 0cd777d9e435266f99d7e0b5f43263882b102b18

# =============================================================================
# 3. PREPROCESAMIENTO DE TEXTO
# =============================================================================

print(f"\n[3/8] Preprocesando texto...")

data["titulo_limpio"] = data["IncidentTitle"].fillna("").apply(limpiar_texto)
data["desc_limpia"]   = data["Description"].fillna("").apply(limpiar_texto)

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
# 4. MÍNIMO TÉCNICO + ENCODING
# =============================================================================

print(f"\n[4/8] Aplicando mínimo técnico y codificando etiquetas...")

conteo = data["category_name"].value_counts()   # conteo REAL, se conserva para el reporte

print(f"    Distribución por rangos:")
print(f"      >= 1000 tickets : {(conteo >= 1000).sum()} categorías")
print(f"      100 - 999       : {((conteo >= 100) & (conteo < 1000)).sum()} categorías")
print(f"      10 - 99         : {((conteo >= 10)  & (conteo < 100)).sum()} categorías")
print(f"      {MIN_TICKETS_TECNICO} - 9           : {((conteo >= MIN_TICKETS_TECNICO) & (conteo < 10)).sum()} categorías")
print(f"      < {MIN_TICKETS_TECNICO}            : {(conteo < MIN_TICKETS_TECNICO).sum()} categorías")

sin_minimo = conteo[conteo < MIN_TICKETS_TECNICO]
if len(sin_minimo):
    print(f"\n    Sin mínimo técnico para entrenar ({len(sin_minimo)}) — siguen en los mapas:")
    print(f"    {', '.join(sin_minimo.index.tolist())}")

cats_entrenables = conteo[conteo >= MIN_TICKETS_TECNICO].index
antes_filtro = len(data)
data_train = data[data["category_name"].isin(cats_entrenables)]
print(f"\n    Tickets para entrenar: {len(data_train):,}  (apartados: {antes_filtro - len(data_train):,})")

X = data_train["texto"].values
y = data_train["category_name"].values

le = LabelEncoder()
y_encoded = le.fit_transform(y)
print(f"    Clases entrenables: {len(le.classes_)}")


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

print(f"\n[5/8] Split realizado:")
print(f"    Train: {len(X_train):,} | Test: {len(X_test):,}")


# =============================================================================
# 6. GENERACIÓN DE EMBEDDINGS (una sola vez)
# =============================================================================

print(f"\n[6/8] Cargando modelo de embeddings: {EMBEDDING_MODEL}")

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


# =============================================================================
# 7. ENTRENAMIENTO + FILTRO POR CONFIANZA
# =============================================================================

print(f"\n[7/8] Entrenando clasificador (primera pasada)...")

clf_1 = crear_clasificador()
clf_1.fit(X_train_emb, y_train)

y_pred_1 = clf_1.predict(X_test_emb)
acc_1  = accuracy_score(y_test, y_pred_1)
f1_w_1 = f1_score(y_test, y_pred_1, average="weighted")
f1_m_1 = f1_score(y_test, y_pred_1, average="macro")
print(f"    Primera pasada -> Accuracy: {acc_1:.4f} | F1 Macro: {f1_m_1:.4f}")

# F1 por clase en test
n_clases = len(le.classes_)
f1_por_clase = f1_score(
    y_test, y_pred_1,
    labels=np.arange(n_clases), average=None, zero_division=0
)
soporte_test = np.bincount(y_test, minlength=n_clases)

idx_confiables = np.where(f1_por_clase >= UMBRAL_F1_CONFIANZA)[0]
idx_baja_conf  = np.where(f1_por_clase <  UMBRAL_F1_CONFIANZA)[0]

if len(idx_confiables) == 0:
    raise ValueError(
        f"Ninguna clase alcanzó F1 >= {UMBRAL_F1_CONFIANZA}. Baja el umbral o revisa los datos."
    )

info_baja_confianza = {
    le.classes_[i]: {"f1": round(float(f1_por_clase[i]), 4), "soporte_test": int(soporte_test[i])}
    for i in idx_baja_conf
}
print(f"    Clases con confianza suficiente: {len(idx_confiables)} | "
      f"descartadas por baja confianza: {len(idx_baja_conf)}")

if len(idx_baja_conf) == 0:
    # Nada que descartar: la primera pasada ya es el modelo final
    clf, le_final = clf_1, le
    X_train_f, X_test_f = X_train_emb, X_test_emb
    y_train_f, y_test_f = y_train, y_test
else:
    print("    Reentrenando solo con las clases confiables...")
    nombres_ok = le.classes_[idx_confiables]
    mask_tr = np.isin(y_train, idx_confiables)
    mask_te = np.isin(y_test,  idx_confiables)

    le_final = LabelEncoder().fit(nombres_ok)
    y_train_f = le_final.transform(le.inverse_transform(y_train[mask_tr]))
    y_test_f  = le_final.transform(le.inverse_transform(y_test[mask_te]))
    X_train_f = X_train_emb[mask_tr]
    X_test_f  = X_test_emb[mask_te]

    clf = crear_clasificador()
    clf.fit(X_train_f, y_train_f)


# =============================================================================
# 8. EVALUACIÓN
# =============================================================================

print(f"\n[8/8] Evaluando modelo final...")

y_pred = clf.predict(X_test_f)

acc  = accuracy_score(y_test_f, y_pred)
f1_w = f1_score(y_test_f, y_pred, average="weighted")
f1_m = f1_score(y_test_f, y_pred, average="macro")

# Cobertura: qué parte de los tickets de test pertenece a clases que el modelo sí predice
cobertura_test = len(y_test_f) / len(y_test)

print("\n" + "=" * 60)
print("  RESULTADOS (solo clases que el modelo predice)")
print("=" * 60)
print(f"  Accuracy   : {acc:.4f}  ({acc*100:.1f}%)")
print(f"  F1 Weighted: {f1_w:.4f}")
print(f"  F1 Macro   : {f1_m:.4f}")
print(f"  Clases predichas / activas : {len(le_final.classes_)} / {len(catalogo_categorias_activas)}")
print(f"  Cobertura de tickets de test: {cobertura_test*100:.1f}%")
print("=" * 60)
print("  OJO: accuracy/F1 NO incluyen los tickets de categorías ignoradas;")
print("  compáralos junto con la cobertura.")

print("\nReporte por categoría:")
print(classification_report(y_test_f, y_pred, target_names=le_final.classes_, zero_division=0))


# =============================================================================
# CATEGORÍAS IGNORADAS (todas las activas que el modelo no predice)
# =============================================================================

clases_entrenadas = set(le_final.classes_)
categorias_ignoradas = {}
for nombre in catalogo_categorias_activas:
    if nombre in clases_entrenadas:
        continue
    tickets = int(conteo.get(nombre, 0))
    if nombre in info_baja_confianza:
        motivo = "baja_confianza"
        extra = info_baja_confianza[nombre]
    elif tickets > 0:
        motivo = "sin_minimo_tecnico"
        extra = {}
    else:
        motivo = "sin_tickets"
        extra = {}
    categorias_ignoradas[nombre] = {"tickets": tickets, "motivo": motivo, **extra}

print(f"\nCategorías activas ignoradas por el modelo: {len(categorias_ignoradas)}")

with open(f"{MODEL_OUTPUT_DIR}categorias_ignoradas.json", "w", encoding="utf-8") as f:
    json.dump(categorias_ignoradas, f, ensure_ascii=False, indent=2)
print(f"Reporte exportado: {MODEL_OUTPUT_DIR}categorias_ignoradas.json")


# =============================================================================
# GUARDAR MODELO
# =============================================================================

version      = datetime.now().strftime("%Y%m%d_%H%M")
nombre_model = f"{MODEL_OUTPUT_DIR}modelo_categoria_{version}.pkl"

joblib.dump(
    {
<<<<<<< HEAD
        "embedding_model_name"       : EMBEDDING_MODEL,
        "classifier"                 : clf,
        "label_encoder"              : le_final,
        # Mapas COMPLETOS (todas las categorías reales, no solo las aprendidas)
        "mapa_cliente_categorias"    : mapa_cliente_categorias,
        "catalogo_categorias_activas": catalogo_categorias_activas,
        "mapa_clientes"              : mapa_clientes,
        # Qué predice realmente el modelo y qué quedó fuera
        "clases_entrenadas"          : sorted(clases_entrenadas),
        "categorias_ignoradas"       : categorias_ignoradas,
        "version"                    : version,
=======
        "embedding_model_name"    : EMBEDDING_MODEL,
        "classifier"              : clf,
        "label_encoder"           : le,
        "mapa_cliente_categorias" : mapa_cliente_categorias, 
        "mapa_clientes"           : mapa_clientes,          
        "version"                 : version,
>>>>>>> 0cd777d9e435266f99d7e0b5f43263882b102b18
        "metricas": {
            "accuracy"            : round(acc,  4),
            "f1_weighted"         : round(f1_w, 4),
            "f1_macro"            : round(f1_m, 4),
            "n_clases"            : len(le_final.classes_),
            "n_clases_activas"    : len(catalogo_categorias_activas),
            "cobertura_test"      : round(cobertura_test, 4),
            "umbral_f1_confianza" : UMBRAL_F1_CONFIANZA,
            "primera_pasada"      : {
                "accuracy"   : round(acc_1, 4),
                "f1_weighted": round(f1_w_1, 4),
                "f1_macro"   : round(f1_m_1, 4),
                "n_clases"   : n_clases,
            },
            "n_train"             : len(y_train_f),
            "n_test"              : len(y_test_f),
        }
    },
    nombre_model
)

print(f"\nModelo guardado: {nombre_model}")
print("Listo.\n")