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
        WHERE activo = true
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


cargar_modelo_actual()

# esquma de entrada

class Ticket(BaseModel):
    code: str
    id: str
    titulo: str | None = ""
    descripcion: str | None = ""

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

    except Exception as e:
        logger.error(f"Error insertando en DB: {e}")

# endpoint probar salud del sistema

@app.get("/health")
def health_check():

    status = {
        "api": "ok",
        "model_loaded": modelo is not None,
        "version": version_modelo
    }

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        status["database"] = "ok"
    except:
        status["database"] = "error"

    return status

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
        WHERE activo = true
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
            activo
        )
        VALUES (
            :nombre,
            :version,
            :archivo,
            :accuracy,
            :f1,
            :fecha,
            :activo
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
            "activo": data["promovido"]
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
        WHERE activo = true
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

# endpoint para tickets pendientes de revisión

@app.get("/feedback/pending")
def obtener_tickets_pendientes(limit: int = 10, username: str = Depends(autenticar_usuario)):

    query = text("""
        SELECT 
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
        FROM tickets_feedback
        WHERE ml_revision = 'pendiente'
        ORDER BY fecha DESC
        LIMIT :limit
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"limit": limit})
            rows = result.mappings().all()  # devuelve dicts

        return {
            "total": len(rows),
            "tickets": rows
        }

    except Exception as e:
        return {
            "error": "fallo en consulta",
            "detalle": str(e)
        }
    
# endpoint para enviar correos
import ssl

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
