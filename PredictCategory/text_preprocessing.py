import re
import pandas as pd
from unidecode import unidecode

def limpiar_texto(texto):

    if pd.isna(texto):
        return ""

    texto = texto.lower()
    texto = texto.replace("\n", " ")
    texto = unidecode(texto)
    texto = re.sub(r"[^a-zA-Z0-9 ]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


stopwords_es = [
"de","la","el","los","las",
"para","por","con",
"al","del",
"se","su","sus",
"esta","este","estos","estas",
"favor"
]