"""
Entrenamiento de modelo de subcategoría con contexto de cliente y categoría padre
Arquitectura: sentence-transformers (embeddings) + LinearSVC calibrado

"""

import json
import os
from datetime import datetime

import numpy as np
import pandas as pd
import joblib
<<<<<<< HEAD
import torch
=======
import json
import os
from datetime import datetime
>>>>>>> 0cd777d9e435266f99d7e0b5f43263882b102b18

from sentence_transformers import SentenceTransformer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, f1_score, classification_report
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV

from text_preprocessing import limpiar_texto
from relacion_clientes import cargar_relacion_cliente_categorias


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

<<<<<<< HEAD
DATASET_PATH     = "../data/dataset-training-category.csv"
CATEGORIAS_PATH  = "../data/categorias-activas.csv"
CLIENTES_PATH    = "../data/clientes.csv"
RELACION_PATH    = "../data/clientes-categorias.csv"
=======
DATASET_PATH    = "../data/dataset-training-category.csv"
CATEGORIAS_PATH = "../data/categorias-activas.csv"
CLIENTES_PATH   = "../data/clientes.csv"   
>>>>>>> 0cd777d9e435266f99d7e0b5f43263882b102b18
MODEL_OUTPUT_DIR = "../models/"

os.makedirs(MODEL_OUTPUT_DIR, exist_ok=True)

EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

BATCH_SIZE   = 64
TEST_SIZE    = 0.2
RANDOM_STATE = 42

# Mínimo TÉCNICO (no es criterio de calidad): CalibratedClassifierCV(cv=3) necesita
# al menos 3 ejemplos por clase en train, y el split estratificado al menos 2 en total.
# Las subcategorías con menos tickets siguen apareciendo en los mapas.
MIN_TICKETS_TECNICO = 5

# Criterio de confianza: tras una primera pasada, las clases con F1 < umbral en test
# se excluyen del clasificador final (siguen apareciendo en los mapas).
# Poner en 0 para desactivar el filtro por confianza.
UMBRAL_F1_CONFIANZA = 0.50


def crear_clasificador():
    svc = LinearSVC(
        C=0.5,
        max_iter=2000,
        class_weight="balanced",
        random_state=RANDOM_STATE
    )
    # CalibratedClassifierCV para obtener probabilidades
    return CalibratedClassifierCV(svc, cv=3)

# =============================================================================
# 1. CARGAR DATOS
# =============================================================================

data = pd.read_csv(DATASET_PATH, sep=";")
cats = pd.read_csv(CATEGORIAS_PATH, sep=";")
clientes = pd.read_csv(CLIENTES_PATH, sep=";")
<<<<<<< HEAD
relacion = cargar_relacion_cliente_categorias(RELACION_PATH)
=======
>>>>>>> 0cd777d9e435266f99d7e0b5f43263882b102b18

# Limpiar espacios en los nombres de las columnas
data.columns = data.columns.str.strip()
cats.columns = cats.columns.str.strip()
clientes.columns = clientes.columns.str.strip()

# Normalizar IDs del dataset de tickets
for columna in ["Category_id", "Client_id"]:
    data[columna] = (
        data[columna].astype("string").str.strip().str.upper()
    )
<<<<<<< HEAD

# Normalizar IDs del catálogo de categorías
for columna in ["id", "padCategories_id"]:
    cats[columna] = (
        cats[columna].astype("string").str.strip().str.upper()
    )

# Normalizar IDs del catálogo de clientes
clientes["id"] = (
    clientes["id"].astype("string").str.strip().str.upper()
)

print("\n[1/8] Archivos cargados y IDs normalizados:")
print(f"    Tickets                    : {len(data):,}")
print(f"    Categorías                 : {len(cats):,}")
print(f"    Clientes                   : {len(clientes):,}")
print(f"    Relación cliente-categoría : {len(relacion):,} filas "
      f"({relacion['cliente_id'].nunique():,} clientes)")
=======
>>>>>>> 0cd777d9e435266f99d7e0b5f43263882b102b18

# Normalizar IDs del catálogo de categorías
for columna in ["id", "padCategories_id"]:
    cats[columna] = (
        cats[columna].astype("string").str.strip().str.upper()
    )

# Normalizar IDs del catálogo de clientes
clientes["id"] = (
    clientes["id"].astype("string").str.strip().str.upper()
)

print("\nArchivos cargados y IDs normalizados:")
print(f"Tickets: {len(data):,}")
print(f"Categorías: {len(cats):,}")
print(f"Clientes: {len(clientes):,}")

# =============================================================================
# 2. SEPARAR PADRES E HIJOS + CONSTRUIR MAPAS BASE
# =============================================================================

print(f"\n[2/8] Construyendo mapas de jerarquía...")

cats_padre = cats[cats["padCategories_id"].isna()].copy()
cats_hijo  = cats[cats["padCategories_id"].notna()].copy()

mapa_hijo_nombre  = dict(zip(cats_hijo["id"], cats_hijo["name"]))
mapa_hijo_padre   = dict(zip(cats_hijo["id"], cats_hijo["padCategories_id"]))
mapa_padre_nombre = dict(zip(cats_padre["id"], cats_padre["name"]))

ids_hijos = set(cats_hijo["id"].values)

# Mapa: cliente UUID → nombre (clientes.csv + clientes que solo vengan en la relación)
mapa_clientes = dict(zip(clientes["id"], clientes["name"]))
agregados = 0
for cid, nombre in relacion[["cliente_id", "cliente_nombre_rel"]].drop_duplicates("cliente_id").itertuples(index=False):
    if cid not in mapa_clientes and pd.notna(nombre):
        mapa_clientes[cid] = nombre
        agregados += 1
if agregados:
    print(f"    Clientes añadidos desde la relación (no estaban en clientes.csv): {agregados}")

print(f"    Categorías padre : {len(cats_padre):,}")
print(f"    Categorías hijo  : {len(cats_hijo):,}")

# --- Catálogo COMPLETO de subcategorías activas por padre --------------------
cats_hijo["cat_padre_nombre"] = cats_hijo["padCategories_id"].map(mapa_padre_nombre)
mapa_solo_padre_subcats = (
    cats_hijo.dropna(subset=["cat_padre_nombre", "name"])
    .groupby("cat_padre_nombre")["name"]
    .apply(lambda x: sorted(x.unique().tolist()))
    .to_dict()
)
catalogo_subcategorias_activas = sorted(cats_hijo["name"].dropna().unique().tolist())
print(f"    Subcategorías activas en catálogo: {len(catalogo_subcategorias_activas):,}")

# --- Tuplas (cliente, padre, subcategoría) según la RELACIÓN real ------------
rel = relacion[relacion["categoria_id"].isin(ids_hijos)].copy()
rel["subcategoria_nombre"] = rel["categoria_id"].map(mapa_hijo_nombre)
rel["cat_padre_nombre"]    = rel["categoria_id"].map(mapa_hijo_padre).map(mapa_padre_nombre)
rel["cliente_nombre"]      = rel["cliente_id"].map(mapa_clientes)
rel = rel.dropna(subset=["subcategoria_nombre", "cat_padre_nombre", "cliente_nombre"])

tuplas_relacion = set(
    zip(rel["cliente_nombre"], rel["cat_padre_nombre"], rel["subcategoria_nombre"])
)
print(f"    Tuplas (cliente, padre, subcategoría) en la relación: {len(tuplas_relacion):,}")


# =============================================================================
# 3. FILTRAR SOLO TICKETS QUE APUNTAN A SUBCATEGORÍA HIJO
# =============================================================================

print(f"\n[3/8] Filtrando tickets con subcategoría hijo...")

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
if data.empty:
    raise ValueError(
        "No quedaron tickets con subcategoría, categoría padre y cliente válidos. "
        "Verifica Category_id, padCategories_id y Client_id, así como "
        "la coincidencia de los UUID entre los tres CSV."
    )
print(f"    Tickets con resolución completa: {len(data):,}  (descartados: {antes - len(data):,})")

# --- Tuplas observadas en tickets (complemento de la relación) ---------------
tuplas_tickets = set(
    zip(data["cliente_nombre"], data["cat_padre_nombre"], data["subcategoria_nombre"])
)
fuera_de_relacion = tuplas_tickets - tuplas_relacion
print(f"    Tuplas vistas en tickets pero ausentes en la relación: {len(fuera_de_relacion):,}")

# MAPA COMPLETO (cliente, padre) → subcategorías: relación ∪ tickets.
# Si un (cliente, padre) no tiene subcategorías conocidas no se crea la llave,
# para que la API use el fallback por padre.
_tmp = {}
for cli, pad, sub in tuplas_relacion | tuplas_tickets:
    _tmp.setdefault((cli, pad), set()).add(sub)
mapa_padre_subcategorias = {k: sorted(v) for k, v in sorted(_tmp.items())}

# El fallback por padre también incorpora lo observado en tickets
for _, pad, sub in tuplas_tickets:
    lista = mapa_solo_padre_subcats.setdefault(pad, [])
    if sub not in lista:
        lista.append(sub)
        lista.sort()

print(f"    Combinaciones (cliente, padre) mapeadas: {len(mapa_padre_subcategorias)}")

# Exportar mapa para revisión
with open(f"{MODEL_OUTPUT_DIR}mapa_subcategorias.json", "w", encoding="utf-8") as f:
    json.dump(
        {
            "por_cliente_y_padre": {str(k): v for k, v in mapa_padre_subcategorias.items()},
            "por_padre"          : mapa_solo_padre_subcats
        },
        f, ensure_ascii=False, indent=2
    )
print(f"    Mapa exportado: {MODEL_OUTPUT_DIR}mapa_subcategorias.json")


# =============================================================================
# 4. PREPROCESAMIENTO DE TEXTO
# =============================================================================

print(f"\n[4/8] Preprocesando texto...")

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
# 5. MÍNIMO TÉCNICO + ENCODING
# =============================================================================

print(f"\n[5/8] Aplicando mínimo técnico y codificando etiquetas...")

conteo = data["subcategoria_nombre"].value_counts()   # conteo REAL, se conserva para el reporte

print(f"    Distribución por rangos:")
print(f"      >= 1000 tickets : {(conteo >= 1000).sum()} subcategorías")
print(f"      100 - 999       : {((conteo >= 100) & (conteo < 1000)).sum()} subcategorías")
print(f"      10 - 99         : {((conteo >= 10)  & (conteo < 100)).sum()} subcategorías")
print(f"      {MIN_TICKETS_TECNICO} - 9           : {((conteo >= MIN_TICKETS_TECNICO) & (conteo < 10)).sum()} subcategorías")
print(f"      < {MIN_TICKETS_TECNICO}            : {(conteo < MIN_TICKETS_TECNICO).sum()} subcategorías")

sin_minimo = conteo[conteo < MIN_TICKETS_TECNICO]
if len(sin_minimo):
    print(f"\n    Sin mínimo técnico para entrenar ({len(sin_minimo)}) — siguen en los mapas:")
    for nombre, cnt in sin_minimo.items():
        print(f"      - {nombre}: {cnt} ticket(s)")

subs_entrenables = conteo[conteo >= MIN_TICKETS_TECNICO].index
antes_filtro = len(data)
data_train = data[data["subcategoria_nombre"].isin(subs_entrenables)]
print(f"\n    Tickets para entrenar: {len(data_train):,}  (apartados: {antes_filtro - len(data_train):,})")

<<<<<<< HEAD
X = data_train["texto"].values
y = data_train["subcategoria_nombre"].values
=======
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
>>>>>>> 0cd777d9e435266f99d7e0b5f43263882b102b18

le = LabelEncoder()
y_encoded = le.fit_transform(y)
print(f"    Subcategorías entrenables: {len(le.classes_)}")


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

print(f"\n[6/8] Split realizado:")
print(f"    Train: {len(X_train):,} | Test: {len(X_test):,}")


# =============================================================================
# 7. EMBEDDINGS (una sola vez) + ENTRENAMIENTO + FILTRO POR CONFIANZA
# =============================================================================

print(f"\n[7/8] Generando embeddings y entrenando...")

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

# ---- Primera pasada: todas las clases entrenables ---------------------------
print("    Entrenando clasificador (primera pasada)...")
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

<<<<<<< HEAD
idx_confiables = np.where(f1_por_clase >= UMBRAL_F1_CONFIANZA)[0]
idx_baja_conf  = np.where(f1_por_clase <  UMBRAL_F1_CONFIANZA)[0]
=======
# CalibratedClassifierCV para obtener probabilidades
clf = CalibratedClassifierCV(svc, cv=3)
>>>>>>> 0cd777d9e435266f99d7e0b5f43263882b102b18

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
    clf, le_final = clf_1, le
    y_train_f, y_test_f = y_train, y_test
    X_test_f = X_test_emb
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

cobertura_test = len(y_test_f) / len(y_test)

print("\n" + "=" * 60)
print("  RESULTADOS (solo subcategorías que el modelo predice)")
print("=" * 60)
print(f"  Accuracy   : {acc:.4f}  ({acc*100:.1f}%)")
print(f"  F1 Weighted: {f1_w:.4f}")
print(f"  F1 Macro   : {f1_m:.4f}")
print(f"  Clases predichas / activas : {len(le_final.classes_)} / {len(catalogo_subcategorias_activas)}")
print(f"  Cobertura de tickets de test: {cobertura_test*100:.1f}%")
print("=" * 60)
print("  OJO: accuracy/F1 NO incluyen los tickets de subcategorías ignoradas;")
print("  compáralos junto con la cobertura.")

print("\nReporte por subcategoría:")
print(classification_report(y_test_f, y_pred, target_names=le_final.classes_, zero_division=0))


# =============================================================================
# SUBCATEGORÍAS IGNORADAS (todas las activas que el modelo no predice)
# =============================================================================

clases_entrenadas = set(le_final.classes_)
subcategorias_ignoradas = {}
for nombre in catalogo_subcategorias_activas:
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
    subcategorias_ignoradas[nombre] = {"tickets": tickets, "motivo": motivo, **extra}

print(f"\nSubcategorías activas ignoradas por el modelo: {len(subcategorias_ignoradas)}")

with open(f"{MODEL_OUTPUT_DIR}subcategorias_ignoradas.json", "w", encoding="utf-8") as f:
    json.dump(subcategorias_ignoradas, f, ensure_ascii=False, indent=2)
print(f"Reporte exportado: {MODEL_OUTPUT_DIR}subcategorias_ignoradas.json")


# =============================================================================
# GUARDAR MODELO
# =============================================================================

version      = datetime.now().strftime("%Y%m%d_%H%M")
nombre_model = f"{MODEL_OUTPUT_DIR}modelo_subcategoria_{version}.pkl"

joblib.dump(
    {
        "embedding_model_name"          : EMBEDDING_MODEL,
        "classifier"                    : clf,
        "label_encoder"                 : le_final,
        # Mapas COMPLETOS (todas las subcategorías reales, no solo las aprendidas)
        "mapa_padre_subcategorias"      : mapa_padre_subcategorias,   # (cliente, padre) → [subcats]
        "mapa_solo_padre_subcats"       : mapa_solo_padre_subcats,    # padre → [subcats] fallback
        "catalogo_subcategorias_activas": catalogo_subcategorias_activas,
        "mapa_clientes"                 : mapa_clientes,              # UUID → nombre cliente
        "mapa_padre_nombre"             : mapa_padre_nombre,          # UUID padre → nombre padre
        # Qué predice realmente el modelo y qué quedó fuera
        "clases_entrenadas"             : sorted(clases_entrenadas),
        "subcategorias_ignoradas"       : subcategorias_ignoradas,
        "version"                       : version,
        "metricas": {
            "accuracy"            : round(acc,  4),
            "f1_weighted"         : round(f1_w, 4),
            "f1_macro"            : round(f1_m, 4),
            "n_clases"            : len(le_final.classes_),
            "n_clases_activas"    : len(catalogo_subcategorias_activas),
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