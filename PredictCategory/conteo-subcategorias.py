import pandas as pd

data = pd.read_csv("../data/dataset-training-category.csv", sep=";")
cats = pd.read_csv("../data/categorias-activas.csv", sep=";")

ids_hijos  = set(cats[cats["padCategories_id"].notna()]["id"])
ids_padres = set(cats[cats["padCategories_id"].isna()]["id"])

apuntan_hijo  = data["Category_id"].isin(ids_hijos).sum()
apuntan_padre = data["Category_id"].isin(ids_padres).sum()

print(f"Tickets apuntando a hijo  : {apuntan_hijo:,}")
print(f"Tickets apuntando a padre : {apuntan_padre:,}")
print(f"Sin match                 : {len(data) - apuntan_hijo - apuntan_padre:,}")

cats_hijos = cats[cats["padCategories_id"].notna()]
data_hijos = data[data["Category_id"].isin(set(cats_hijos["id"]))]

print(f"Subcategorías únicas en el dataset: {data_hijos['Category_id'].nunique()}")
print(f"\nTop 5 subcategorías con más tickets:")
print(data_hijos["Category_id"].value_counts().head())