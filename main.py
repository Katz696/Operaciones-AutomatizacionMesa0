import os
import glob
from typing import Optional
import joblib
import subprocess
import pandas as pd
import re
import logging
import json
from datetime import datetime
from unidecode import unidecode
from fastapi import Body, FastAPI,Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Union
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl
from sentence_transformers import SentenceTransformer
import torch
import numpy as np
import ssl

MAIL_HOST     = os.getenv("MAIL_HOST")
MAIL_PORT     = int(os.getenv("MAIL_PORT", 587))
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_FROM     = os.getenv("MAIL_FROM")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "API")

class EmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    name: Optional[str] = ""

# autentificacion imports
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
import bcrypt
# ------------------------

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL")
THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.70))

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )

security = HTTPBasic()

app = FastAPI(
    title="API Clasificador de Tickets",
    version="2.0"
)

# Cargar modelo

MODELS_DIR = "models"

modelo = None
mapa_ids = None
version_modelo = None

modelo_categoria    = None
version_categoria   = None
embedder_categoria  = None
 
modelo_subcategoria   = None
version_subcategoria  = None
embedder_subcategoria = None
 

# funcion para autentificar usuario

def autenticar_usuario(credentials: HTTPBasicCredentials = Depends(security)):

    query = text("""
        SELECT username, password_hash, is_active
        FROM api_users
        WHERE username = :username
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {"username": credentials.username})
        user = result.mappings().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Basic"},
        )

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Usuario inactivo")

    # comparar password con hash
    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Basic"},
        )

    return user["username"]
    
    
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cargar_modelo_actual():

    global modelo, mapa_ids, version_modelo

    query = text("""
        SELECT archivo
        FROM models
        WHERE activo = true AND tipo = 'padtypes'
        ORDER BY fecha_entrenamiento DESC
        LIMIT 1
    """)
    
    try :
        with engine.connect() as conn:
            result = conn.execute(query)
            modelo_activo = result.mappings().first()
    except Exception as e:
        logger.error(f"Error consultando el modelo activo: {e}")
        raise Exception("Error al cargar el modelo")

    if not modelo_activo:
        raise Exception("No hay modelo activo en la base de datos")
    
    ruta_modelo = os.path.join(MODELS_DIR, modelo_activo["archivo"])

    if not os.path.exists(ruta_modelo):
        raise Exception("Modelo no encontrado: " + ruta_modelo)

    datos_modelo = joblib.load(ruta_modelo)

    modelo = datos_modelo["modelo"]
    mapa_ids = datos_modelo["mapa_ids"]
    version_modelo = datos_modelo["version"]

    logger.info(f"Modelo cargado: {ruta_modelo}")

def cargar_modelo_categoria():

    global modelo_categoria, version_categoria, embedder_categoria

    query = text("""
        SELECT archivo FROM models
        WHERE activo = true AND tipo = 'categoria'
        ORDER BY fecha_entrenamiento DESC
        LIMIT 1
    """)

    try:
        with engine.connect() as conn:
            activo = conn.execute(query).mappings().first()
    except Exception as e:
        logger.error(f"Error consultando modelo categoría: {e}")
        raise Exception("Error al cargar modelo de categoría")

    if not activo:
        raise Exception("No hay modelo de categoría activo en la base de datos")

    ruta = os.path.join(MODELS_DIR, activo["archivo"])

    if not os.path.exists(ruta):
        raise Exception(f"Modelo de categoría no encontrado: {ruta}")

    datos                = joblib.load(ruta)
    device               = "cuda" if torch.cuda.is_available() else "cpu"
    embedder_categoria   = SentenceTransformer(datos["embedding_model_name"]).to(device)
    datos["_device"]     = device
    modelo_categoria     = datos
    version_categoria    = datos["version"]

    logger.info(f"Modelo categoría cargado: {ruta} — v{version_categoria}")
 
def cargar_modelo_subcategoria():

    global modelo_subcategoria, version_subcategoria, embedder_subcategoria

    query = text("""
        SELECT archivo FROM models
        WHERE activo = true AND tipo = 'subcategoria'
        ORDER BY fecha_entrenamiento DESC
        LIMIT 1
    """)

    try:
        with engine.connect() as conn:
            activo = conn.execute(query).mappings().first()
    except Exception as e:
        logger.error(f"Error consultando modelo subcategoría: {e}")
        raise Exception("Error al cargar modelo de subcategoría")

    if not activo:
        raise Exception("No hay modelo de subcategoría activo en la base de datos")

    ruta = os.path.join(MODELS_DIR, activo["archivo"])

    if not os.path.exists(ruta):
        raise Exception(f"Modelo de subcategoría no encontrado: {ruta}")

    datos                  = joblib.load(ruta)
    device                 = "cuda" if torch.cuda.is_available() else "cpu"
    embedder_subcategoria  = SentenceTransformer(datos["embedding_model_name"]).to(device)
    datos["_device"]       = device
    modelo_subcategoria    = datos
    version_subcategoria   = datos["version"]

    logger.info(f"Modelo subcategoría cargado: {ruta} — v{version_subcategoria}")

 
# Cargar al arranque
cargar_modelo_categoria()
cargar_modelo_subcategoria()
cargar_modelo_actual()

# mapa de categorias
_cats_df = pd.read_csv("data/categorias-activas.csv", sep=";")
MAPA_NOMBRE_A_ID = dict(zip(_cats_df["name"], _cats_df["id"]))

# esquma de entrada
class Ticket(BaseModel):
    code: str
    id: str
    titulo: str | None = ""
    descripcion: str | None = ""

class TicketCategoria(BaseModel):
    code:        str
    id:          str
    titulo:      str | None = ""
    descripcion: str | None = ""
    client_id:   str

class TicketSubcategoria(BaseModel):
    code:            str
    id:              str
    titulo:          str | None = ""
    descripcion:     str | None = ""
    client_id:       str
    categoria_padre: str          # nombre devuelto por /categoria/predict

class FeedbackCorreccionCategoria(BaseModel):
    id:                  str
    categoria_corregida: str      # nombre de la categoría correcta
    categoria_id:        str      # UUID de la categoría correcta


# limpiar texto

def limpiar_texto(texto):

    if not texto:
        return ""

    texto = texto.lower()
    texto = texto.replace("\n", " ")
    texto = unidecode(texto)
    texto = re.sub(r"[^a-zA-Z0-9 ]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()

# funcion upsert para tabla de resumen
def upsert_resumen_feedback(
    ticket_id, titulo, descripcion,
    dimension,        # "tipo, categoria o subcategoria"
    valor, valor_id, confianza
):
    columnas = {
        "tipo":         ("tipo_valor",         "tipo_id",         "tipo_confianza",         "tipo_revision"),
        "categoria":    ("categoria_valor",     "categoria_id",    "categoria_confianza",    "categoria_revision"),
        "subcategoria": ("subcategoria_valor",  "subcategoria_id", "subcategoria_confianza", "subcategoria_revision"),
    }
    col_valor, col_id, col_conf, col_rev = columnas[dimension]

    query = text(f"""
        INSERT INTO ticket_feedback_resumen (
            id, incident_title, description,
            {col_valor}, {col_id}, {col_conf}, {col_rev},
            fecha_actualizacion
        )
        VALUES (
            :id, :titulo, :descripcion,
            :valor, :valor_id, :confianza, 'pendiente',
            NOW()
        )
        ON CONFLICT (id) DO UPDATE SET
            {col_valor} = EXCLUDED.{col_valor},
            {col_id}    = EXCLUDED.{col_id},
            {col_conf}  = EXCLUDED.{col_conf},
            {col_rev}   = 'pendiente',
            incident_title      = EXCLUDED.incident_title,
            description         = EXCLUDED.description,
            fecha_actualizacion = NOW()
    """)

    try:
        with engine.connect() as conn:
            conn.execute(query, {
                "id":        ticket_id,
                "titulo":    titulo,
                "descripcion": descripcion,
                "valor":     valor,
                "valor_id":  valor_id,
                "confianza": confianza
            })
            conn.commit()
        logger.info(f"[resumen] upsert {dimension}: {ticket_id}")
    except Exception as e:
        logger.error(f"Error en upsert_resumen_feedback ({dimension}): {e}")

# registrar baja confianza

def registrar_baja_confianza(ticket_id, titulo, descripcion, padtypes_predicho, confianza):

    mapa_tipos = {v: k for k, v in mapa_ids.items()}
    tipo_predicho = mapa_tipos.get(padtypes_predicho, "Otros")

    query = text("""
        INSERT INTO tickets_feedback (
            id,
            incident_title,
            description,
            padtypes_id_predicho,
            tipo_predicho,
            confianza,
            fecha,
            ml_revision,
            used_for_training,
            padtypes_id_corregido
        )
        VALUES (
            :id,
            :titulo,
            :descripcion,
            :pad_id,
            :tipo,
            :confianza,
            :fecha,
            'pendiente',
            false,
            NULL
        )
        ON CONFLICT (id) DO NOTHING
    """)

    try:
        with engine.connect() as conn:
            conn.execute(query, {
                "id": ticket_id,
                "titulo": titulo,
                "descripcion": descripcion,
                "pad_id": padtypes_predicho,
                "tipo": tipo_predicho,
                "confianza": confianza,
                "fecha": datetime.now()
            })
            conn.commit()
            logger.info(f"Ticket registrado por baja confianza: {ticket_id} - {tipo_predicho} ({confianza:.2f})")
            upsert_resumen_feedback(ticket_id, titulo, descripcion, "tipo", tipo_predicho, padtypes_predicho, confianza)

    except Exception as e:
        logger.error(f"Error insertando en DB: {e}")

def _predecir_con_filtro(
    embedder,
    datos_modelo: dict,
    texto: str,
    indices_validos: list
) -> list:
    """
    Genera embedding, filtra probabilidades por índices válidos,
    renormaliza y devuelve top 3.
    """
    device        = datos_modelo["_device"]
    clf           = datos_modelo["classifier"]
    le            = datos_modelo["label_encoder"]

    embedding     = embedder.encode([texto], device=device, convert_to_numpy=True)
    proba_global  = clf.predict_proba(embedding)[0]

    proba_filtrada = np.zeros(len(proba_global))
    proba_filtrada[indices_validos] = proba_global[indices_validos]

    if proba_filtrada.sum() > 0:
        proba_filtrada /= proba_filtrada.sum()
    else:
        proba_filtrada = proba_global   # fallback sin filtro

    top_indices = proba_filtrada.argsort()[::-1][:3]
    categorias  = le.inverse_transform(top_indices)

    return [
        {"nombre": cat, "probabilidad": round(float(proba_filtrada[i]), 4)}
        for cat, i in zip(categorias, top_indices)
    ]


def registrar_baja_confianza_categoria(
    ticket_id, titulo, descripcion,
    client_id, cliente_nombre,
    categoria_predicha, categoria_id,
    confianza, tipo_modelo
):
    query = text("""
        INSERT INTO categoria_feedback (
            id, incident_title, description,
            client_id, cliente_nombre,
            categoria_predicha, categoria_id_predicha,
            confianza, tipo_modelo, fecha,
            ml_revision, used_for_training, categoria_id_corregida
        )
        VALUES (
            :id, :titulo, :descripcion,
            :client_id, :cliente_nombre,
            :categoria_predicha, :categoria_id,
            :confianza, :tipo_modelo, :fecha,
            'pendiente', false, NULL
        )
        ON CONFLICT (id, tipo_modelo) DO NOTHING
    """)

    try:
        with engine.connect() as conn:
            conn.execute(query, {
                "id":                 ticket_id,
                "titulo":             titulo,
                "descripcion":        descripcion,
                "client_id":          client_id,
                "cliente_nombre":     cliente_nombre,
                "categoria_predicha": categoria_predicha,
                "categoria_id":       categoria_id,
                "confianza":          confianza,
                "tipo_modelo":        tipo_modelo,
                "fecha":              datetime.now()
            })
            conn.commit()
            logger.info(f"[{tipo_modelo}] Baja confianza: {ticket_id} → {categoria_predicha} ({confianza:.2f})")
            upsert_resumen_feedback(ticket_id, titulo, descripcion, tipo_modelo, categoria_predicha, categoria_id, confianza)
    except Exception as e:
        logger.error(f"Error insertando categoria_feedback: {e}")

# endpoint probar salud del sistema

@app.get("/health")
def health_check():

    resultado = {
        "api":                  "ok",
        "model_padtypes":       modelo is not None,
        "model_categoria":      modelo_categoria is not None,
        "model_subcategoria":   modelo_subcategoria is not None,
        "version_padtypes":     version_modelo,
        "version_categoria":    version_categoria,
        "version_subcategoria": version_subcategoria
    }

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        resultado["database"] = "ok"
    except:
        resultado["database"] = "error"

    return resultado

@app.post("/predict")

def predecir_ticket(ticket: Ticket, username: str = Depends(autenticar_usuario)):

    texto = limpiar_texto(ticket.titulo or "") + " " + limpiar_texto(ticket.descripcion or "")

    if texto.strip() == "":
        return {
            "id": ticket.id,
            "categoria": "Otros",
            "confianza": 0
        }

    categoria = modelo.predict([texto])[0]

    probabilidades = modelo.predict_proba([texto])[0]

    confianza = float(max(probabilidades))

    tipo_id = mapa_ids[categoria]

    clases = modelo.classes_

    if confianza < THRESHOLD:
        registrar_baja_confianza(
            ticket.id,
            ticket.titulo,
            ticket.descripcion,
            tipo_id,
            confianza
        )

    return {
        "code": ticket.code,
        "id": ticket.id,
        "titulo": ticket.titulo,
        "descripcion": ticket.descripcion,
        "categoria": categoria,
        "tipo_id": tipo_id,
        "confianza": confianza,
        "modelo_version": version_modelo
    }

# endpoint para crear dataset de entrenamiento a partir del feedback

@app.post("/build-dataset")
def build_dataset(username: str = Depends(autenticar_usuario)):

    proceso = subprocess.run(
        ["python", "build_training_dataset.py"],
        capture_output=True,
        text=True
    )

    dataset_built = "DATASET_BUILT=true" in proceso.stdout

    return {
        "status": "dataset processed",
        "dataset_built": dataset_built,
        "stdout": proceso.stdout,
        "stderr": proceso.stderr
    }

# endpoint para ejecutar entrenamiento

@app.post("/train")

def train_model(username: str = Depends(autenticar_usuario)):

    proceso = subprocess.run(
        ["python", "train_model.py"],
        capture_output=True,
        text=True
    )

    return {
        "status": "training executed",
        "output": proceso.stdout
    }

# endpoint para ejecutar evaluación

@app.post("/evaluate")
def evaluate_model(username: str = Depends(autenticar_usuario)):

    query = text("""
        SELECT accuracy, f1_score
        FROM models
        WHERE activo = true AND tipo = 'padtypes'
        ORDER BY fecha_entrenamiento DESC
        LIMIT 1
    """)
    
    try :
        with engine.connect() as conn:
            result = conn.execute(query)
            modelo_activo = result.mappings().first()
    except Exception as e:
        logger.error(f"Error consultando el modelo activo: {e}")

    accuracy_actual = modelo_activo["accuracy"] if modelo_activo else None
    f1_actual = modelo_activo["f1_score"] if modelo_activo else None

    proceso = subprocess.run(
    [
        "python",
        "evaluate_model.py",
        str(accuracy_actual),
        str(f1_actual)
    ],
    capture_output=True,
    text=True
    )

    try:
        output_lines = proceso.stdout.strip().split("\n")

        json_line = output_lines[-1]

        data = json.loads(json_line)
    except Exception as e:
        return {
            "error": "no se pudo parsear salida",
            "stdout": proceso.stdout,
            "stderr": proceso.stderr
        }

    # guardar en DB
    query = text("""
    INSERT INTO models (
        nombre,
        version,
        archivo,
        accuracy,
        f1_score,
        fecha_entrenamiento,
        activo,
        tipo   
    )
    VALUES (
        :nombre,
        :version,
        :archivo,
        :accuracy,
        :f1,
        :fecha,
        :activo,
        :tipo
    )
    ON CONFLICT (archivo)
    DO UPDATE SET
        accuracy = EXCLUDED.accuracy,
        f1_score = EXCLUDED.f1_score,
        fecha_entrenamiento = EXCLUDED.fecha_entrenamiento,
        activo = EXCLUDED.activo
    """)

    with engine.connect() as conn:
        conn.execute(query, {
            "nombre": "clasificador_tickets",
            "version": data["version_nuevo"],
            "archivo": data["modelo_nuevo"],
            "accuracy": data["accuracy_new"],
            "f1": data["f1_new"],
            "fecha": datetime.now(),
            "activo": data["promovido"],
            "tipo": "padtypes"
        })
        conn.commit()

    return {
        "status": "evaluation executed",
        "metrics": data
    }
# endpoint para recargar modelo

@app.post("/reload-model")

def reload_model(username: str = Depends(autenticar_usuario)):

    cargar_modelo_actual()

    return {
        "status": "modelo recargado",
        "version": version_modelo
    }

# endpoint informacion del modelo

@app.get("/model-info")

def model_info():

    return {
        "version": version_modelo,
        "clases": list(modelo.classes_)
    }

@app.post("/set-model")
def set_model(nombre_modelo: str, username: str = Depends(autenticar_usuario)):

    query_buscar = text("""
        SELECT archivo
        FROM models
        WHERE archivo = :archivo
    """)

    query_reset = text("""
        UPDATE models
        SET activo = false
        WHERE activo = true AND tipo = 'padtypes'
    """)

    query_activate = text("""
        UPDATE models
        SET activo = true
        WHERE archivo = :archivo
        RETURNING version
    """)

    try:
        with engine.begin() as conn:

            # verificar que existe
            result = conn.execute(query_buscar, {"archivo": nombre_modelo})
            existe = result.mappings().first()

            if not existe:
                return {"error": "modelo no existe en DB"}

            # desactivar todos
            conn.execute(query_reset)

            # activar el nuevo
            result = conn.execute(query_activate, {"archivo": nombre_modelo})
            row = result.fetchone()

        # recargar modelo en memoria
        cargar_modelo_actual()

        return {
            "status": "modelo actualizado",
            "archivo": nombre_modelo,
            "version": row[0]
        }

    except Exception as e:
        return {
            "error": "fallo al cambiar modelo",
            "detalle": str(e)
        }

# endpoint para tickets pendientes de revisión en la tabla maestra

@app.get("/feedback/pending")
def obtener_tickets_pendientes_resumen(limit: int = 10, username: str = Depends(autenticar_usuario)):
    query = text("""
        SELECT
            id, incident_title, description,
            tipo_valor, tipo_id, tipo_confianza, tipo_revision,
            categoria_valor, categoria_id, categoria_confianza, categoria_revision,
            subcategoria_valor, subcategoria_id, subcategoria_confianza, subcategoria_revision,
            fecha_creacion
        FROM ticket_feedback_resumen
        WHERE correo_enviado = FALSE
          AND (
              tipo_revision        = 'pendiente' OR
              categoria_revision   = 'pendiente' OR
              subcategoria_revision = 'pendiente'
          )
        ORDER BY fecha_creacion ASC
        LIMIT :limit
    """)
    try:
        with engine.connect() as conn:
            rows = conn.execute(query, {"limit": limit}).mappings().all()
        return {"total": len(rows), "tickets": [dict(r) for r in rows]}
    except Exception as e:
        return {"error": "fallo en consulta", "detalle": str(e)}

# endpoint para enviar correos

@app.post("/send-mail")
def send_mail(email: EmailRequest, username: str = Depends(autenticar_usuario)):

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = email.subject
        msg["From"]    = f"{MAIL_FROM_NAME} <{MAIL_FROM}>"
        msg["To"]      = email.to
        msg.attach(MIMEText(email.body, "html"))

        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        server = smtplib.SMTP(MAIL_HOST, MAIL_PORT, timeout=30)
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.sendmail(MAIL_FROM, email.to, msg.as_string())
        server.quit()

        logger.info(f"Correo enviado a {email.to} por usuario {username}")
        return {
            "status": "ok",
            "message": f"Correo enviado a {email.to}"
        }

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(status_code=401, detail="Error de autenticación SMTP")

    except smtplib.SMTPException as e:
        logger.error(f"Error SMTP: {type(e).__name__} - {e}")
        raise HTTPException(status_code=500, detail=f"Error SMTP: {str(e)}")

    except Exception as e:
        logger.error(f"Error inesperado: {type(e).__name__} - {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# endpoint para marcar correos enviados en la tabla maestra

@app.post("/feedback/correo-enviado")
def marcar_correo_enviado(ids: List[str] = Body(...), username: str = Depends(autenticar_usuario)):
    query = text("""
        UPDATE ticket_feedback_resumen
        SET correo_enviado = TRUE, fecha_actualizacion = NOW()
        WHERE id = ANY(:ids)
        AND correo_enviado = FALSE
        RETURNING id
    """)
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"ids": ids})
            updated_ids = [row[0] for row in result]
            conn.commit()
        return {
            "ids_recibidos": len(ids),
            "actualizados":  len(updated_ids),
            "status": "ok"
        }
    except Exception as e:
        return {"error": "fallo interno", "detalle": str(e)}

# endpoint para marcar tickets como enviados a revision de ML
@app.post("/feedback/mark-sent-bulk")
def marcar_tickets_enviados(ids: List[str] = Body(...), username: str = Depends(autenticar_usuario)):

    query = text("""
        UPDATE tickets_feedback
        SET ml_revision = 'enviado'
        WHERE id = ANY(:ids)
        AND ml_revision = 'pendiente'
        RETURNING id
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"ids": ids})
            updated_ids = [row[0] for row in result]
            conn.commit()

        return {
            "ids_recibidos": len(ids),
            "actualizados": len(updated_ids),
            "status": "ok"
        }

    except Exception as e:
        return {
            "error": "fallo interno",
            "detalle": str(e)
        }
class FeedbackConfirmacion(BaseModel):

    id: str

class FeedbackCorreccion(BaseModel):

    id: str
    categoria: str

# endpoint para confirmar ticket

@app.post("/feedback/confirm")
def confirmar_ticket(confirmacion: FeedbackConfirmacion, username: str = Depends(autenticar_usuario)):

    query = text("""
        UPDATE tickets_feedback
        SET 
            padtypes_id_corregido = padtypes_id_predicho,
            ml_revision = 'confirmado'
        WHERE id = :id
        RETURNING id
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"id": confirmacion.id})
            updated = result.fetchone()
            conn.commit()

        if not updated:
            return {"error": "ticket no encontrado"}

        return {
            "status": "prediccion confirmada",
            "ticket_id": confirmacion.id
        }

    except Exception as e:
        return {
            "error": "fallo interno",
            "detalle": str(e)
        }
    
# endpoint para corregir ticket

@app.post("/feedback/correct")
def corregir_ticket(feedback: FeedbackCorreccion, username: str = Depends(autenticar_usuario)):

    if feedback.categoria not in mapa_ids:
        return {
            "error": "categoria invalida",
            "categorias_validas": list(mapa_ids.keys())
        }

    padtypes_id = mapa_ids[feedback.categoria]

    query = text("""
        UPDATE tickets_feedback
        SET 
            padtypes_id_corregido = :nuevo_id,
            ml_revision = 'corregido'
        WHERE id = :id
        RETURNING id
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {
                "id": feedback.id,
                "nuevo_id": padtypes_id
            })
            updated = result.fetchone()
            conn.commit()

        if not updated:
            return {"error": "ticket no encontrado"}

        return {
            "status": "ticket corregido",
            "ticket_id": feedback.id,
            "categoria": feedback.categoria,
            "padTypes_id": padtypes_id
        }

    except Exception as e:
        return {
            "error": "fallo interno",
            "detalle": str(e)
        }

# estado de los tickets de feedback por medio de id

@app.get("/feedback/revision/{ticket_id}")
def obtener_revision_ticket(ticket_id: str, username: str = Depends(autenticar_usuario)):
 
    query = text("""
        SELECT id, incident_title, tipo_predicho, confianza, fecha, ml_revision
        FROM tickets_feedback
        WHERE id = :ticket_id
    """)
 
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"ticket_id": ticket_id})
            row = result.mappings().first()
 
        if not row:
            raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' no encontrado")
 
        return {
            "id": row["id"],
            "incident_title": row["incident_title"],
            "tipo_predicho": row["tipo_predicho"],
            "confianza": row["confianza"],
            "fecha": str(row["fecha"]) if row["fecha"] else None,
            "ml_revision": row["ml_revision"],
        }
 
    except HTTPException:
        raise
    except Exception as e:
        return {"error": "fallo en consulta", "detalle": str(e)}
    

# endpoint para obtener métricas de feedback

@app.get("/metrics")
def obtener_metricas(username: str = Depends(autenticar_usuario)):

    query = text("""
        SELECT
            COUNT(*) as total_feedback,
            SUM(CASE WHEN ml_revision = 'pendiente' THEN 1 ELSE 0 END) as pendientes,
            SUM(CASE WHEN ml_revision = 'confirmado' THEN 1 ELSE 0 END) as confirmados,
            SUM(CASE WHEN ml_revision = 'corregido' THEN 1 ELSE 0 END) as corregidos,
            AVG(confianza) as confianza_promedio
        FROM tickets_feedback
    """)

    with engine.connect() as conn:
        result = conn.execute(query).mappings().first()
    
    return result

# endpoint para obtener precision real
# De todos los tickets revisados, ¿cuántos estaban bien clasificados?

@app.get("/metrics/accuracy")
def accuray(username: str = Depends(autenticar_usuario)):

    query = text("""
        SELECT
            COUNT(*) FILTER (WHERE padtypes_id_predicho = padtypes_id_corregido) * 1.0 /
            NULLIF(COUNT(*) FILTER (WHERE ml_revision IN ('confirmado','corregido')), 0)
            AS accuracy
        FROM tickets_feedback
        WHERE ml_revision IN ('confirmado','corregido')
    """)

    with engine.connect() as conn:
        result = "exactitud de prediccion segun los datos de retroalimentacion: " + str(conn.execute(query).scalar())

    return result

# ####################################################
# -------------Prediccion de Categoria---------------
# ####################################################

@app.post("/categoria/predict")
def predecir_categoria(ticket: TicketCategoria, username: str = Depends(autenticar_usuario)):

    if modelo_categoria is None:
        return {
            "code": ticket.code, "id": ticket.id,
            "cliente": "/", "categoria": "/",
            "confianza": 0.0, "top": [],
            "modelo_version": version_categoria
        }

    cliente_nombre = modelo_categoria["mapa_clientes"].get(ticket.client_id.upper(), "/")

    if cliente_nombre == "/":
        logger.warning(f"client_id no reconocido: {ticket.client_id}")
        return {
            "code": ticket.code, "id": ticket.id,
            "cliente": "/", "categoria": "/",
            "confianza": 0.0, "top": [],
            "modelo_version": version_categoria
        }

    cats_cliente = modelo_categoria["mapa_cliente_categorias"].get(cliente_nombre, [])

    if not cats_cliente:
        logger.warning(f"Sin categorías para cliente: {cliente_nombre}")
        return {
            "code": ticket.code, "id": ticket.id,
            "cliente": cliente_nombre, "categoria": "/",
            "confianza": 0.0, "top": [],
            "modelo_version": version_categoria
        }

    le              = modelo_categoria["label_encoder"]
    indices_validos = [i for i, cls in enumerate(le.classes_) if cls in cats_cliente]

    titulo_limpio = limpiar_texto(ticket.titulo or "")
    desc_limpia   = limpiar_texto(ticket.descripcion or "")
    texto = f"[{cliente_nombre}] {titulo_limpio} {titulo_limpio} {titulo_limpio} {desc_limpia}".strip()[:1200]

    if not texto.strip():
        return {
            "code": ticket.code, "id": ticket.id,
            "cliente": cliente_nombre, "categoria": "/",
            "confianza": 0.0, "top": [],
            "modelo_version": version_categoria
        }

    top              = _predecir_con_filtro(embedder_categoria, modelo_categoria, texto, indices_validos)
    categoria_nombre = top[0]["nombre"]
    confianza        = top[0]["probabilidad"]
    categoria_id     = MAPA_NOMBRE_A_ID.get(categoria_nombre, "/")

    if confianza < THRESHOLD:
        registrar_baja_confianza_categoria(
            ticket.id, ticket.titulo, ticket.descripcion,
            ticket.client_id, cliente_nombre,
            categoria_nombre, categoria_id, confianza, "categoria"
        )

    return {
        "code":           ticket.code,
        "id":             ticket.id,
        "cliente":        cliente_nombre,
        "categoria":      categoria_nombre,
        "categoria_id":   categoria_id,
        "confianza":      confianza,
        "modelo_version": version_categoria
    }

@app.post("/categoria/reload")
def reload_categoria(username: str = Depends(autenticar_usuario)):
    cargar_modelo_categoria()
    return {"status": "modelo de categoría recargado", "version": version_categoria}


@app.get("/categoria/model-info")
def categoria_model_info():
    if modelo_categoria is None:
        raise HTTPException(status_code=503, detail="Modelo de categoría no cargado")
    return {
        "version":  version_categoria,
        "clases":   list(modelo_categoria["label_encoder"].classes_),
        "metricas": modelo_categoria.get("metricas", {})
    }


@app.get("/categoria/feedback/pending")
def feedback_categoria_pendientes(
    limit: int = 10,
    tipo:  str  = "categoria",
    username: str = Depends(autenticar_usuario)
):
    query = text("""
        SELECT id, incident_title, description, client_id, cliente_nombre,
               categoria_predicha, categoria_id_predicha, confianza,
               tipo_modelo, fecha, ml_revision, categoria_id_corregida
        FROM categoria_feedback
        WHERE ml_revision = 'pendiente' AND tipo_modelo = :tipo
        ORDER BY fecha DESC LIMIT :limit
    """)
    try:
        with engine.connect() as conn:
            rows = conn.execute(query, {"limit": limit, "tipo": tipo}).mappings().all()
        return {"total": len(rows), "tickets": rows}
    except Exception as e:
        return {"error": "fallo en consulta", "detalle": str(e)}


@app.post("/categoria/feedback/confirm")
def confirmar_categoria(
    confirmacion: FeedbackConfirmacion,
    tipo: str = "categoria",
    username: str = Depends(autenticar_usuario)
):
    query = text("""
        UPDATE categoria_feedback
        SET categoria_id_corregida = categoria_id_predicha,
            ml_revision = 'confirmado'
        WHERE id = :id AND tipo_modelo = :tipo
        RETURNING id
    """)
    try:
        with engine.connect() as conn:
            updated = conn.execute(query, {"id": confirmacion.id, "tipo": tipo}).fetchone()
            conn.commit()
        if not updated:
            return {"error": "ticket no encontrado"}
        return {"status": "predicción confirmada", "ticket_id": confirmacion.id}
    except Exception as e:
        return {"error": "fallo interno", "detalle": str(e)}


@app.post("/categoria/feedback/correct")
def corregir_categoria(
    feedback: FeedbackCorreccionCategoria,
    tipo: str = "categoria",
    username: str = Depends(autenticar_usuario)
):
    query = text("""
        UPDATE categoria_feedback
        SET categoria_predicha     = :cat_corregida,
            categoria_id_corregida = :cat_id,
            ml_revision            = 'corregido'
        WHERE id = :id AND tipo_modelo = :tipo
        RETURNING id
    """)
    try:
        with engine.connect() as conn:
            updated = conn.execute(query, {
                "id": feedback.id, "cat_corregida": feedback.categoria_corregida,
                "cat_id": feedback.categoria_id, "tipo": tipo
            }).fetchone()
            conn.commit()
        if not updated:
            return {"error": "ticket no encontrado"}
        return {
            "status":              "ticket corregido",
            "ticket_id":           feedback.id,
            "categoria_corregida": feedback.categoria_corregida
        }
    except Exception as e:
        return {"error": "fallo interno", "detalle": str(e)}

# ##########################################################
# -----------------Predict Subcategoria---------------------
# ##########################################################

@app.post("/subcategoria/predict")
def predecir_subcategoria(ticket: TicketSubcategoria, username: str = Depends(autenticar_usuario)):

    if modelo_subcategoria is None:
        return {
            "code": ticket.code, "id": ticket.id,
            "cliente": "/", "categoria_padre": ticket.categoria_padre,
            "subcategoria": "/", "confianza": 0.0, "top": [],
            "modelo_version": version_subcategoria
        }

    # Resolver cliente
    mapa_clientes  = modelo_subcategoria["mapa_clientes"]
    cliente_nombre = modelo_subcategoria["mapa_clientes"].get(ticket.client_id.upper(), "/")

    if cliente_nombre == "/":
        logger.warning(f"client_id no reconocido: {ticket.client_id}")
        return {
            "code": ticket.code, "id": ticket.id,
            "cliente": "/", "categoria_padre": ticket.categoria_padre,
            "subcategoria": "/", "confianza": 0.0, "top": [],
            "modelo_version": version_subcategoria
        }

    # Subcategorías válidas para (cliente, padre)
    clave   = (cliente_nombre, ticket.categoria_padre)
    subcats = modelo_subcategoria["mapa_padre_subcategorias"].get(clave, [])

    if not subcats:
        subcats = modelo_subcategoria["mapa_solo_padre_subcats"].get(ticket.categoria_padre, [])
        logger.warning(f"Fallback a mapa_solo_padre: cliente={cliente_nombre}, padre={ticket.categoria_padre}")

    if not subcats:
        logger.warning(f"Sin subcategorías para cliente={cliente_nombre}, padre={ticket.categoria_padre}")
        return {
            "code": ticket.code, "id": ticket.id,
            "cliente": cliente_nombre, "categoria_padre": ticket.categoria_padre,
            "subcategoria": "/", "confianza": 0.0, "top": [],
            "modelo_version": version_subcategoria
        }

    le              = modelo_subcategoria["label_encoder"]
    indices_validos = [i for i, cls in enumerate(le.classes_) if cls in subcats]

    titulo_limpio = limpiar_texto(ticket.titulo or "")
    desc_limpia   = limpiar_texto(ticket.descripcion or "")
    texto = (
        f"[{cliente_nombre}][{ticket.categoria_padre}] "
        f"{titulo_limpio} {titulo_limpio} {titulo_limpio} {desc_limpia}"
    ).strip()[:1200]

    if not texto.strip():
        return {
            "code": ticket.code, "id": ticket.id,
            "cliente": cliente_nombre, "categoria_padre": ticket.categoria_padre,
            "subcategoria": "/", "confianza": 0.0, "top": [],
            "modelo_version": version_subcategoria
        }

    top             = _predecir_con_filtro(embedder_subcategoria, modelo_subcategoria, texto, indices_validos)
    subcat_nombre   = top[0]["nombre"]
    confianza       = top[0]["probabilidad"]
    subcategoria_id = MAPA_NOMBRE_A_ID.get(subcat_nombre, "/")

    # si duda en subcategoría, registrar también la categoría padre
    categoria_padre_id = MAPA_NOMBRE_A_ID.get(ticket.categoria_padre, "/")

    if confianza < THRESHOLD:
        # registrar subcategoría
        registrar_baja_confianza_categoria(
            ticket.id, ticket.titulo, ticket.descripcion,
            ticket.client_id, cliente_nombre,
            subcat_nombre, subcategoria_id, confianza, "subcategoria"
        )
        # registrar categoría padre también
        registrar_baja_confianza_categoria(
            ticket.id, ticket.titulo, ticket.descripcion,
            ticket.client_id, cliente_nombre,
            ticket.categoria_padre, categoria_padre_id, confianza, "categoria"
        )

    return {
        "code":             ticket.code,
        "id":               ticket.id,
        "cliente":          cliente_nombre,
        "categoria_padre":  ticket.categoria_padre,
        "subcategoria":     subcat_nombre,
        "subcategoria_id":  subcategoria_id,
        "confianza":        confianza,
        "modelo_version":   version_subcategoria,
        "top": top
    }

@app.post("/subcategoria/reload")
def reload_subcategoria(username: str = Depends(autenticar_usuario)):
    cargar_modelo_subcategoria()
    return {"status": "modelo de subcategoría recargado", "version": version_subcategoria}


@app.get("/subcategoria/model-info")
def subcategoria_model_info():
    if modelo_subcategoria is None:
        raise HTTPException(status_code=503, detail="Modelo de subcategoría no cargado")
    return {
        "version":  version_subcategoria,
        "clases":   list(modelo_subcategoria["label_encoder"].classes_),
        "metricas": modelo_subcategoria.get("metricas", {})
    }


@app.get("/subcategoria/feedback/pending")
def feedback_subcategoria_pendientes(
    limit: int = 10,
    username: str = Depends(autenticar_usuario)
):
    query = text("""
        SELECT id, incident_title, description, client_id, cliente_nombre,
               categoria_predicha, confianza, fecha, ml_revision
        FROM categoria_feedback
        WHERE ml_revision = 'pendiente' AND tipo_modelo = 'subcategoria'
        ORDER BY fecha DESC LIMIT :limit
    """)
    try:
        with engine.connect() as conn:
            rows = conn.execute(query, {"limit": limit}).mappings().all()
        return {"total": len(rows), "tickets": rows}
    except Exception as e:
        return {"error": "fallo en consulta", "detalle": str(e)}


@app.post("/subcategoria/feedback/confirm")
def confirmar_subcategoria(
    confirmacion: FeedbackConfirmacion,
    username: str = Depends(autenticar_usuario)
):
    query = text("""
        UPDATE categoria_feedback
        SET categoria_id_corregida = categoria_id_predicha,
            ml_revision = 'confirmado'
        WHERE id = :id AND tipo_modelo = 'subcategoria'
        RETURNING id
    """)
    try:
        with engine.connect() as conn:
            updated = conn.execute(query, {"id": confirmacion.id}).fetchone()
            conn.commit()
        if not updated:
            return {"error": "ticket no encontrado"}
        return {"status": "predicción confirmada", "ticket_id": confirmacion.id}
    except Exception as e:
        return {"error": "fallo interno", "detalle": str(e)}


@app.post("/subcategoria/feedback/correct")
def corregir_subcategoria(
    feedback: FeedbackCorreccionCategoria,
    username: str = Depends(autenticar_usuario)
):
    query = text("""
        UPDATE categoria_feedback
        SET categoria_predicha     = :cat_corregida,
            categoria_id_corregida = :cat_id,
            ml_revision            = 'corregido'
        WHERE id = :id AND tipo_modelo = 'subcategoria'
        RETURNING id
    """)
    try:
        with engine.connect() as conn:
            updated = conn.execute(query, {
                "id": feedback.id, "cat_corregida": feedback.categoria_corregida,
                "cat_id": feedback.categoria_id
            }).fetchone()
            conn.commit()
        if not updated:
            return {"error": "ticket no encontrado"}
        return {
            "status":              "subcategoría corregida",
            "ticket_id":           feedback.id,
            "categoria_corregida": feedback.categoria_corregida
        }
    except Exception as e:
        return {"error": "fallo interno", "detalle": str(e)}
