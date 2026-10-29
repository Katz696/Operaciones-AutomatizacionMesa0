"""
Carga de la relación cliente -> categorías disponibles.

"""

import re
import pandas as pd


def _leer_csv_auto(path):
    """Detecta si el separador es ';' o ','"""
    with open(path, "r", encoding="utf-8-sig") as f:
        primera = f.readline()
    sep = ";" if primera.count(";") > primera.count(",") else ","
    return pd.read_csv(path, sep=sep, dtype=str, encoding="utf-8-sig")


def cargar_relacion_cliente_categorias(path):
    df = _leer_csv_auto(path)
    df.columns = df.columns.str.strip()

    faltantes = {"customerId", "customerName"} - set(df.columns)
    if faltantes:
        raise ValueError(
            f"Columnas faltantes en la relación cliente-categorías: {sorted(faltantes)}. "
            f"Columnas encontradas (primeras 10): {df.columns.tolist()[:10]}"
        )

    patron = re.compile(r"^categories/(\d+)/id$")
    indices = sorted(
        int(m.group(1)) for c in df.columns if (m := patron.match(c))
    )
    if not indices:
        raise ValueError(
            "No se encontraron columnas con el patrón 'categories/N/id' en la relación."
        )

    bloques = []
    for i in indices:
        col_id, col_name = f"categories/{i}/id", f"categories/{i}/name"
        if col_name not in df.columns:
            continue
        sub = df[["customerId", "customerName", col_id, col_name]].copy()
        sub.columns = [
            "cliente_id", "cliente_nombre_rel", "categoria_id", "categoria_nombre_rel"
        ]
        bloques.append(sub.dropna(subset=["categoria_id"]))

    largo = pd.concat(bloques, ignore_index=True)

    for col in ["cliente_id", "categoria_id"]:
        largo[col] = largo[col].astype("string").str.strip().str.upper()
    for col in ["cliente_nombre_rel", "categoria_nombre_rel"]:
        largo[col] = largo[col].astype("string").str.strip()

    largo = largo[(largo["cliente_id"] != "") & (largo["categoria_id"] != "")]
    largo = largo.dropna(subset=["cliente_id", "categoria_id"])
    largo = largo.drop_duplicates(subset=["cliente_id", "categoria_id"]).reset_index(drop=True)
    return largo