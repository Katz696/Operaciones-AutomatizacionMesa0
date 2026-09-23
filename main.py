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
from fastapi import Body, FastAPI,Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from typing import List, Union, Literal
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl
from sentence_transformers import SentenceTransformer
import torch
import numpy as np
import ssl
import uuid
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import HTTPBasicCredentials
from jose import jwt, JWTError

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"

# esqumas de entradas
class EmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    name: Optional[str] = ""
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
    categoria_padre: str          

class FeedbackCorreccionCategoria(BaseModel):
    id:                  str
    categoria_corregida: str      
    categoria_id:        str    
class TicketCompleto(BaseModel):
    code:        str
    id:          str
    titulo:      str | None = ""
    descripcion: str | None = ""
    client_id:   str  
class ConfirmacionTicketCompleto(BaseModel):
    id: str
class CorreccionTicketCompleto(BaseModel):
    id:                  str
    tipo_nombre:         Optional[str] = None
    categoria_nombre:    str
    categoria_id:        str
    subcategoria_nombre: Optional[str] = None
    subcategoria_id:     Optional[str] = None

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

oauth2_scheme_admin = OAuth2PasswordBearer(tokenUrl="/no-aplica", auto_error=False)

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

def verificar_admin(
    token: str = Depends(oauth2_scheme_admin),
    basic: HTTPBasicCredentials = Depends(HTTPBasic(auto_error=False)),
):
    # Camino 1: Bearer JWT (api-admin reenviando el token del usuario)
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except JWTError:
            raise HTTPException(status_code=401, detail="Token inválido o expirado")
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail=f"Rol '{payload.get('role')}' no autorizado")
        return payload.get("sub")

    # Camino 2: Basic Auth (n8n u otro cliente de servicio)
    if basic:
        query = text("SELECT username, password_hash, role, is_active FROM api_users WHERE username = :u")
        with engine.connect() as conn:
            user = conn.execute(query, {"u": basic.username}).mappings().first()
        if not user or not user["is_active"] or not verify_password(basic.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        if user["role"] != "admin":
            raise HTTPException(status_code=403, detail=f"Rol '{user['role']}' no autorizado")
        return user["username"]

    raise HTTPException(status_code=401, detail="Falta autenticación", headers={"WWW-Authenticate": "Bearer"})
    
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cargar_modelo_tipo():

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

def cargar_threshold_desde_db():
    global THRESHOLD
    query = text("SELECT valor FROM ml_config WHERE clave = 'confidence_threshold'")
    try:
        with engine.connect() as conn:
            row = conn.execute(query).mappings().first()
        if row:
            THRESHOLD = float(row["valor"])
            logger.info(f"Threshold cargado desde DB: {THRESHOLD}")
    except Exception as e:
        logger.error(f"No se pudo cargar threshold desde DB, usando default: {e}")
 
# Cargar al arranque
cargar_modelo_categoria()
cargar_modelo_subcategoria()
cargar_modelo_tipo() 
cargar_threshold_desde_db()

# mapa de categorias
_cats_df = pd.read_csv("data/categorias-activas.csv", sep=";")
MAPA_NOMBRE_A_ID = dict(zip(_cats_df["name"], _cats_df["id"]))

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

# # funcion upsert para tabla de resumen de tickets pendientes
# def upsert_resumen_feedback(
#     ticket_id, titulo, descripcion,
#     dimension,
#     valor, valor_id, confianza
# ):
#     columnas = {
#         "tipo":         ("tipo_valor",         "tipo_id",         "tipo_confianza",         "tipo_revision"),
#         "categoria":    ("categoria_valor",     "categoria_id",    "categoria_confianza",    "categoria_revision"),
#         "subcategoria": ("subcategoria_valor",  "subcategoria_id", "subcategoria_confianza", "subcategoria_revision"),
#     }
#     col_valor, col_id, col_conf, col_rev = columnas[dimension]

#     query = text(f"""
#         INSERT INTO ticket_feedback_resumen (
#             id, incident_title, description,
#             {col_valor}, {col_id}, {col_conf}, {col_rev},
#             fecha_actualizacion
#         )
#         VALUES (
#             :id, :titulo, :descripcion,
#             :valor, :valor_id, :confianza, 'pendiente',
#             NOW()
#         )
#         ON CONFLICT (id) DO UPDATE SET
#             {col_valor} = EXCLUDED.{col_valor},
#             {col_id}    = EXCLUDED.{col_id},
#             {col_conf}  = EXCLUDED.{col_conf},
#             {col_rev}   = 'pendiente',
#             incident_title      = EXCLUDED.incident_title,
#             description         = EXCLUDED.description,
#             fecha_actualizacion = NOW()
#     """)

#     try:
#         with engine.connect() as conn:
#             conn.execute(query, {
#                 "id":        ticket_id,
#                 "titulo":    titulo,
#                 "descripcion": descripcion,
#                 "valor":     valor,
#                 "valor_id":  valor_id,
#                 "confianza": confianza
#             })
#             conn.commit()
#         logger.info(f"[resumen] upsert {dimension}: {ticket_id}")
#     except Exception as e:
#         logger.error(f"Error en upsert_resumen_feedback ({dimension}): {e}")

# # funcion upsert para registrar tipo cuando se corrija todo el ticket
# def _upsert_correccion_tipo_feedback(conn, ticket_id, tipo_id_corregido, resumen_row, ml_revision):
#     titulo         = resumen_row["incident_title"]
#     descripcion    = resumen_row["description"]
#     valor_original = resumen_row["tipo_valor"]
#     id_original    = resumen_row["tipo_id"]
#     conf_original  = resumen_row["tipo_confianza"]

#     query = text("""
#         INSERT INTO tickets_feedback (
#             id, incident_title, description,
#             padtypes_id_predicho, tipo_predicho,
#             confianza, fecha,
#             ml_revision, used_for_training, padtypes_id_corregido
#         )
#         VALUES (
#             :id, :titulo, :descripcion,
#             :id_original, :valor_original,
#             :conf_original, NOW(),
#             :ml_revision, false, :tipo_id_corregido
#         )
#         ON CONFLICT (id) DO UPDATE SET
#             padtypes_id_corregido = EXCLUDED.padtypes_id_corregido,
#             ml_revision            = :ml_revision
#     """)
#     conn.execute(query, {
#         "id": ticket_id, "titulo": titulo, "descripcion": descripcion,
#         "id_original": id_original, "valor_original": valor_original,
#         "conf_original": conf_original, "tipo_id_corregido": tipo_id_corregido,
#         "ml_revision": ml_revision
#     })

# # funcion upsert para registrar categoria cuando se corrija todo el ticket
# def _upsert_correccion_categoria_feedback(
#     conn, ticket_id, client_id, cliente_nombre,
#     tipo_modelo, id_corregido, resumen_row, ml_revision
# ):
#     titulo = resumen_row["incident_title"]
#     descripcion = resumen_row["description"]

#     if tipo_modelo == "categoria":
#         valor_original = resumen_row["categoria_valor"]
#         id_original    = resumen_row["categoria_id"]
#         conf_original  = resumen_row["categoria_confianza"]
#     else:
#         valor_original = resumen_row["subcategoria_valor"]
#         id_original    = resumen_row["subcategoria_id"]
#         conf_original  = resumen_row["subcategoria_confianza"]

#     query = text("""
#         INSERT INTO categoria_feedback (
#             id, incident_title, description,
#             client_id, cliente_nombre,
#             categoria_predicha, categoria_id_predicha,
#             confianza, tipo_modelo, fecha,
#             ml_revision, used_for_training, categoria_id_corregida
#         )
#         VALUES (
#             :id, :titulo, :descripcion,
#             :client_id, :cliente_nombre,
#             :valor_original, :id_original,
#             :conf_original, :tipo_modelo, NOW(),
#             :ml_revision, false, :id_corregido
#         )
#         ON CONFLICT (id, tipo_modelo) DO UPDATE SET
#             categoria_id_corregida = EXCLUDED.categoria_id_corregida,
#             ml_revision            = :ml_revision
#     """)
#     conn.execute(query, {
#         "id": ticket_id, "titulo": titulo, "descripcion": descripcion,
#         "client_id": client_id, "cliente_nombre": cliente_nombre,
#         "valor_original": valor_original, "id_original": id_original,
#         "conf_original": conf_original, "tipo_modelo": tipo_modelo,
#         "id_corregido": id_corregido, "ml_revision": ml_revision
#     })

# # registrar baja confianza

# def registrar_baja_confianza_tipo(ticket_id, titulo, descripcion, padtypes_predicho, confianza):

#     mapa_tipos = {v: k for k, v in mapa_ids.items()}
#     tipo_predicho = mapa_tipos.get(padtypes_predicho, "Otros")

#     query = text("""
#         INSERT INTO tickets_feedback (
#             id,
#             incident_title,
#             description,
#             padtypes_id_predicho,
#             tipo_predicho,
#             confianza,
#             fecha,
#             ml_revision,
#             used_for_training,
#             padtypes_id_corregido
#         )
#         VALUES (
#             :id,
#             :titulo,
#             :descripcion,
#             :pad_id,
#             :tipo,
#             :confianza,
#             :fecha,
#             'pendiente',
#             false,
#             NULL
#         )
#         ON CONFLICT (id) DO NOTHING
#     """)

#     try:
#         with engine.connect() as conn:
#             conn.execute(query, {
#                 "id": ticket_id,
#                 "titulo": titulo,
#                 "descripcion": descripcion,
#                 "pad_id": padtypes_predicho,
#                 "tipo": tipo_predicho,
#                 "confianza": confianza,
#                 "fecha": datetime.now()
#             })
#             conn.commit()
#             logger.info(f"Ticket registrado por baja confianza: {ticket_id} - {tipo_predicho} ({confianza:.2f})")

#     except Exception as e:
#         logger.error(f"Error insertando en DB: {e}")

# ============================================================
# Persistencia de predicciones (tabla central `predicciones`)
# ============================================================

def _revision_inicial(confianza: float) -> str:
    """Toda predicción se registra. Si pasa el confidence_threshold
    no necesita revisión humana ('NA'); si no lo pasa, queda
    'pendiente' hasta que alguien la confirme o corrija."""
    return "pendiente" if confianza < THRESHOLD else "NA"


def registrar_prediccion(
    ticket_id: str,
    code: str | None = None,
    titulo: str | None = None,
    descripcion: str | None = None,
    client_id: str | None = None,
    cliente_nombre: str | None = None,
    tipo: dict | None = None,          # {"valor","id","confianza","modelo_version"}
    categoria: dict | None = None,
    subcategoria: dict | None = None,
):
    """
    Upsert de la fila de predicciones para un ticket. Solo se
    escriben las dimensiones que se pasen (no None); las demás
    conservan su valor anterior gracias al COALESCE. Se llama
    SIEMPRE que se predice algo, sin importar la confianza.
    """

    params = {
        "id": ticket_id, "code": code, "titulo": titulo, "descripcion": descripcion,
        "client_id": client_id, "cliente_nombre": cliente_nombre,

        "tipo_valor": tipo["valor"] if tipo else None,
        "tipo_id": tipo["id"] if tipo else None,
        "tipo_confianza": tipo["confianza"] if tipo else None,
        "tipo_modelo_version": tipo["modelo_version"] if tipo else None,
        "tipo_revision": _revision_inicial(tipo["confianza"]) if tipo else None,

        "categoria_valor": categoria["valor"] if categoria else None,
        "categoria_id": categoria["id"] if categoria else None,
        "categoria_confianza": categoria["confianza"] if categoria else None,
        "categoria_modelo_version": categoria["modelo_version"] if categoria else None,
        "categoria_revision": _revision_inicial(categoria["confianza"]) if categoria else None,

        "subcategoria_valor": subcategoria["valor"] if subcategoria else None,
        "subcategoria_id": subcategoria["id"] if subcategoria else None,
        "subcategoria_confianza": subcategoria["confianza"] if subcategoria else None,
        "subcategoria_modelo_version": subcategoria["modelo_version"] if subcategoria else None,
        "subcategoria_revision": _revision_inicial(subcategoria["confianza"]) if subcategoria else None,
    }

    query = text("""
        INSERT INTO predicciones (
            id, code, incident_title, description, client_id, cliente_nombre,
            tipo_predicho, tipo_id_predicho, tipo_confianza, tipo_modelo_version, tipo_revision,
            categoria_predicha, categoria_id_predicha, categoria_confianza, categoria_modelo_version, categoria_revision,
            subcategoria_predicha, subcategoria_id_predicha, subcategoria_confianza, subcategoria_modelo_version, subcategoria_revision,
            fecha_creacion, fecha_actualizacion
        )
        VALUES (
            :id, :code, :titulo, :descripcion, :client_id, :cliente_nombre,
            :tipo_valor, :tipo_id, :tipo_confianza, :tipo_modelo_version, :tipo_revision,
            :categoria_valor, :categoria_id, :categoria_confianza, :categoria_modelo_version, :categoria_revision,
            :subcategoria_valor, :subcategoria_id, :subcategoria_confianza, :subcategoria_modelo_version, :subcategoria_revision,
            NOW(), NOW()
        )
        ON CONFLICT (id) DO UPDATE SET
            code                = COALESCE(EXCLUDED.code, predicciones.code),
            incident_title      = COALESCE(EXCLUDED.incident_title, predicciones.incident_title),
            description         = COALESCE(EXCLUDED.description, predicciones.description),
            client_id           = COALESCE(EXCLUDED.client_id, predicciones.client_id),
            cliente_nombre      = COALESCE(EXCLUDED.cliente_nombre, predicciones.cliente_nombre),

            tipo_predicho        = COALESCE(EXCLUDED.tipo_predicho, predicciones.tipo_predicho),
            tipo_id_predicho      = COALESCE(EXCLUDED.tipo_id_predicho, predicciones.tipo_id_predicho),
            tipo_confianza        = COALESCE(EXCLUDED.tipo_confianza, predicciones.tipo_confianza),
            tipo_modelo_version   = COALESCE(EXCLUDED.tipo_modelo_version, predicciones.tipo_modelo_version),
            tipo_revision         = COALESCE(EXCLUDED.tipo_revision, predicciones.tipo_revision),

            categoria_predicha         = COALESCE(EXCLUDED.categoria_predicha, predicciones.categoria_predicha),
            categoria_id_predicha      = COALESCE(EXCLUDED.categoria_id_predicha, predicciones.categoria_id_predicha),
            categoria_confianza        = COALESCE(EXCLUDED.categoria_confianza, predicciones.categoria_confianza),
            categoria_modelo_version   = COALESCE(EXCLUDED.categoria_modelo_version, predicciones.categoria_modelo_version),
            categoria_revision         = COALESCE(EXCLUDED.categoria_revision, predicciones.categoria_revision),

            subcategoria_predicha        = COALESCE(EXCLUDED.subcategoria_predicha, predicciones.subcategoria_predicha),
            subcategoria_id_predicha     = COALESCE(EXCLUDED.subcategoria_id_predicha, predicciones.subcategoria_id_predicha),
            subcategoria_confianza       = COALESCE(EXCLUDED.subcategoria_confianza, predicciones.subcategoria_confianza),
            subcategoria_modelo_version  = COALESCE(EXCLUDED.subcategoria_modelo_version, predicciones.subcategoria_modelo_version),
            subcategoria_revision        = COALESCE(EXCLUDED.subcategoria_revision, predicciones.subcategoria_revision),

            fecha_actualizacion = NOW()
    """)

    try:
        with engine.connect() as conn:
            conn.execute(query, params)
            conn.commit()
        logger.info(f"[predicciones] upsert ticket={ticket_id}")
    except Exception as e:
        logger.error(f"Error en registrar_prediccion: {e}")


def _guardar_correccion(
    conn, prediccion_id: str, campo: str,
    valor_original, valor_id_original,
    valor_corregido, valor_id_corregido,
    accion: str, revisor_username: str | None = None
):
    """
    Guarda (o actualiza) la revisión humana de un campo de una
    predicción en `correcciones`, y refleja el nuevo estado en
    predicciones.<campo>_revision. Estas filas son las que luego
    arman los datasets de reentrenamiento (filtrando por campo y
    used_for_training=false).
    """
    revisor_id = None
    if revisor_username:
        row = conn.execute(
            text("SELECT id FROM api_users WHERE username = :u"),
            {"u": revisor_username}
        ).mappings().first()
        revisor_id = row["id"] if row else None

    query = text("""
        INSERT INTO correcciones (
            prediccion_id, campo, valor_original, valor_id_original,
            valor_corregido, valor_id_corregido, accion, revisor_id, fecha_revision
        )
        VALUES (
            :prediccion_id, :campo, :valor_original, :valor_id_original,
            :valor_corregido, :valor_id_corregido, :accion, :revisor_id, NOW()
        )
        ON CONFLICT (prediccion_id, campo) DO UPDATE SET
            valor_corregido    = EXCLUDED.valor_corregido,
            valor_id_corregido = EXCLUDED.valor_id_corregido,
            accion             = EXCLUDED.accion,
            revisor_id         = EXCLUDED.revisor_id,
            fecha_revision     = NOW()
    """)
    conn.execute(query, {
        "prediccion_id": prediccion_id, "campo": campo,
        "valor_original": valor_original, "valor_id_original": valor_id_original,
        "valor_corregido": valor_corregido, "valor_id_corregido": valor_id_corregido,
        "accion": accion, "revisor_id": revisor_id
    })

    conn.execute(
        text(f"UPDATE predicciones SET {campo}_revision = :accion, fecha_actualizacion = NOW() WHERE id = :id"),
        {"accion": accion, "id": prediccion_id}
    )

def _ejecutar_entrenamiento_background(job_id: str, script: str):
    """
    Corre el script de entrenamiento en background y actualiza
    training_jobs cuando termina (exito o error).
    """

    proceso = subprocess.run(
        ["python", script],
        cwd=CATEGORY_SCRIPTS_DIR,
        capture_output=True,
        text=True
    )

    estado = "completado" if proceso.returncode == 0 else "error"

    update_query = text("""
        UPDATE training_jobs
        SET estado = :estado,
            fin = :fin,
            returncode = :returncode,
            stdout = :stdout,
            stderr = :stderr
        WHERE id = :id
    """)

    try:
        with engine.begin() as conn:
            conn.execute(update_query, {
                "id": job_id,
                "estado": estado,
                "fin": datetime.now(),
                "returncode": proceso.returncode,
                "stdout": proceso.stdout,
                "stderr": proceso.stderr
            })
    except Exception as e:
        logger.error(f"No se pudo actualizar training_jobs para {job_id}: {e}")


def _iniciar_entrenamiento(tipo: str, script: str, background_tasks: BackgroundTasks):

    job_id = str(uuid.uuid4())

    insert_query = text("""
        INSERT INTO training_jobs (id, tipo, estado, script, inicio)
        VALUES (:id, :tipo, 'en_progreso', :script, :inicio)
    """)

    with engine.begin() as conn:
        conn.execute(insert_query, {
            "id": job_id,
            "tipo": tipo,
            "script": script,
            "inicio": datetime.now()
        })

    background_tasks.add_task(_ejecutar_entrenamiento_background, job_id, script)

    return job_id

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
            # upsert_resumen_feedback(ticket_id, titulo, descripcion, tipo_modelo, categoria_predicha, categoria_id, confianza)
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
class ConfigValor(BaseModel):
    valor: str

@app.get("/config/{clave}")
def obtener_config(clave: str, username: str = Depends(autenticar_usuario)):
    query = text("SELECT valor, actualizado_en FROM ml_config WHERE clave = :clave")
    with engine.connect() as conn:
        row = conn.execute(query, {"clave": clave}).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"No existe la clave '{clave}' en ml_config")

    return {"clave": clave, "valor": row.valor, "actualizado_en": row.actualizado_en}


@app.put("/config/{clave}")
def actualizar_config(clave: str, payload: ConfigValor, username: str = Depends(autenticar_usuario)):
    update_query = text("""
        UPDATE ml_config
        SET valor = :valor, actualizado_en = now()
        WHERE clave = :clave
    """)

    with engine.connect() as conn:
        result = conn.execute(update_query, {"clave": clave, "valor": payload.valor})
        conn.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"No existe la clave '{clave}' en ml_config")

    return {"clave": clave, "valor": payload.valor}

@app.post("/predict")

def predecir_tipo(ticket: Ticket, username: str = Depends(autenticar_usuario)):

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

    registrar_prediccion(
        ticket_id=ticket.id, code=ticket.code, titulo=ticket.titulo, descripcion=ticket.descripcion,
        tipo={"valor": categoria, "id": tipo_id, "confianza": confianza, "modelo_version": version_modelo}
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

# enpoint de prediccion completa con registros de baja confianza

@app.post("/predict/completo")
def predecir_ticket_completo(ticket: TicketCompleto, username: str = Depends(autenticar_usuario)):

    # ---------- TIPO ----------
    texto_tipo = limpiar_texto(ticket.titulo or "") + " " + limpiar_texto(ticket.descripcion or "")

    tipo_nombre, tipo_id, tipo_confianza = "Otros", mapa_ids.get("Otros"), 0.0
    if texto_tipo.strip():
        tipo_nombre    = modelo.predict([texto_tipo])[0]
        probabilidades = modelo.predict_proba([texto_tipo])[0]
        tipo_confianza = float(max(probabilidades))
        tipo_id        = mapa_ids[tipo_nombre]

    # ---------- CATEGORÍA ----------
    cliente_nombre = modelo_categoria["mapa_clientes"].get(ticket.client_id.upper(), "/")
    categoria_nombre, categoria_id, categoria_confianza = "/", "/", 0.0

    if cliente_nombre != "/":
        cats_cliente = modelo_categoria["mapa_cliente_categorias"].get(cliente_nombre, [])
        if cats_cliente:
            le_cat              = modelo_categoria["label_encoder"]
            indices_validos_cat = [i for i, cls in enumerate(le_cat.classes_) if cls in cats_cliente]

            titulo_limpio = limpiar_texto(ticket.titulo or "")
            desc_limpia   = limpiar_texto(ticket.descripcion or "")
            texto_cat = f"[{cliente_nombre}] {titulo_limpio} {titulo_limpio} {titulo_limpio} {desc_limpia}".strip()[:1200]

            if texto_cat.strip():
                top_cat              = _predecir_con_filtro(embedder_categoria, modelo_categoria, texto_cat, indices_validos_cat)
                categoria_nombre     = top_cat[0]["nombre"]
                categoria_confianza  = top_cat[0]["probabilidad"]
                categoria_id         = MAPA_NOMBRE_A_ID.get(categoria_nombre, "/")

    # ---------- SUBCATEGORÍA ----------
    subcat_nombre, subcategoria_id, subcat_confianza = "", "", 0.0

    if categoria_nombre != "/":
        clave   = (cliente_nombre, categoria_nombre)
        subcats = modelo_subcategoria["mapa_padre_subcategorias"].get(clave, [])
        if not subcats:
            subcats = modelo_subcategoria["mapa_solo_padre_subcats"].get(categoria_nombre, [])

        if subcats:
            le_sub              = modelo_subcategoria["label_encoder"]
            indices_validos_sub = [i for i, cls in enumerate(le_sub.classes_) if cls in subcats]

            titulo_limpio = limpiar_texto(ticket.titulo or "")
            desc_limpia   = limpiar_texto(ticket.descripcion or "")
            texto_sub = (
                f"[{cliente_nombre}][{categoria_nombre}] "
                f"{titulo_limpio} {titulo_limpio} {titulo_limpio} {desc_limpia}"
            ).strip()[:1200]

            if texto_sub.strip():
                top_sub          = _predecir_con_filtro(embedder_subcategoria, modelo_subcategoria, texto_sub, indices_validos_sub)
                subcat_nombre    = top_sub[0]["nombre"]
                subcat_confianza = top_sub[0]["probabilidad"]
                subcategoria_id  = MAPA_NOMBRE_A_ID.get(subcat_nombre, "")

    # ---------- REGISTRO: siempre, con las tres dimensiones juntas ----------
    registrar_prediccion(
        ticket_id=ticket.id, code=ticket.code, titulo=ticket.titulo, descripcion=ticket.descripcion,
        client_id=ticket.client_id, cliente_nombre=cliente_nombre,
        tipo={"valor": tipo_nombre, "id": tipo_id, "confianza": tipo_confianza, "modelo_version": version_modelo},
        categoria={"valor": categoria_nombre, "id": categoria_id, "confianza": categoria_confianza, "modelo_version": version_categoria},
        subcategoria={"valor": subcat_nombre, "id": subcategoria_id, "confianza": subcat_confianza, "modelo_version": version_subcategoria},
    )

    return {
        "code": ticket.code,
        "id":   ticket.id,
        "cliente": cliente_nombre,
        "tipo":         {"valor": tipo_nombre,     "id": tipo_id,         "confianza": tipo_confianza},
        "categoria":    {"valor": categoria_nombre, "id": categoria_id,    "confianza": categoria_confianza},
        "subcategoria": {"valor": subcat_nombre,    "id": subcategoria_id, "confianza": subcat_confianza}
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

# endpoint para crear dataset para categoria y subcategoria

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CATEGORY_SCRIPTS_DIR = os.path.join(BASE_DIR, "PredictCategory")

@app.post("/build-dataset-category")
def build_dataset_category(username: str = Depends(autenticar_usuario)):
 
    proceso = subprocess.run(
        ["python", "build_training_dataset_category.py"],
        cwd=CATEGORY_SCRIPTS_DIR,
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

# endpoint para ejecutar entrenamiento del modelo tipo

@app.post("/train")

def train_model(username: str = Depends(verificar_admin)):

    proceso = subprocess.run(
        ["python", "train_model.py"],
        capture_output=True,
        text=True
    )
    return {
        "status": "training executed",
        "output": proceso.stdout
    }

# endpoint para ejecutar entrenamiento de categoria (asincrono)

@app.post("/train-category")
def train_category_model(background_tasks: BackgroundTasks, username: str = Depends(verificar_admin)):

    job_id = _iniciar_entrenamiento("categoria", "train_categorymodel.py", background_tasks)

    return {
        "status": "entrenamiento iniciado",
        "tipo": "categoria",
        "job_id": job_id
    }
 
# endpoint para ejecutar entrenamiento de subcategoria (asincrono)

@app.post("/train-subcategory")
def train_subcategory_model(background_tasks: BackgroundTasks, username: str = Depends(verificar_admin)):

    job_id = _iniciar_entrenamiento("subcategoria", "train_subcategory_model.py", background_tasks)

    return {
        "status": "entrenamiento iniciado",
        "tipo": "subcategoria",
        "job_id": job_id
    }

@app.get("/train-status/{job_id}")
def train_status(job_id: str, username: str = Depends(autenticar_usuario)):

    query = text("""
        SELECT id, tipo, estado, script, inicio, fin, returncode, stdout, stderr
        FROM training_jobs
        WHERE id = :id
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {"id": job_id})
        job = result.mappings().first()

    if not job:
        raise HTTPException(status_code=404, detail="job_id no encontrado")

    return dict(job)

# endpoint para ejecutar evaluación del modelo tipo
 
@app.post("/evaluate")
def evaluate_model(username: str = Depends(autenticar_usuario)):
 
    query = text("""
        SELECT accuracy, f1_score
        FROM models
        WHERE activo = true AND tipo = 'padtypes'
        ORDER BY fecha_entrenamiento DESC
        LIMIT 1
    """)
 
    modelo_activo = None
 
    try:
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
        if data["promovido"]:
            # Libera el slot de "activo" para este tipo antes de insertar, o el INSERT de abajo viola unico_modelo_activo_por_tipo si ya habia otro modelo de tipo activo.
            deactivate_query = text("""
                UPDATE models
                SET activo = false
                WHERE tipo = :tipo AND activo = true AND archivo != :archivo
            """)
            conn.execute(deactivate_query, {
                "tipo": "padtypes",
                "archivo": data["modelo_nuevo"]
            })
 
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

# endpoint para ejecutar evaluación del modelo de categoria
 
@app.post("/evaluate-category")
def evaluate_category_model(username: str = Depends(autenticar_usuario)):
 
    query = text("""
        SELECT accuracy, f1_score
        FROM models
        WHERE activo = true AND tipo = 'categoria'
        ORDER BY fecha_entrenamiento DESC
        LIMIT 1
    """)
 
    modelo_activo = None
 
    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            modelo_activo = result.mappings().first()
    except Exception as e:
        logger.error(f"Error consultando el modelo activo (categoria): {e}")
 
    accuracy_actual = modelo_activo["accuracy"] if modelo_activo else None
    f1_actual = modelo_activo["f1_score"] if modelo_activo else None
 
    proceso = subprocess.run(
        [
            "python",
            "evaluate_model_categoria.py",
            str(accuracy_actual),
            str(f1_actual)
        ],
        cwd=CATEGORY_SCRIPTS_DIR,
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
        if data["promovido"]:
            deactivate_query = text("""
                UPDATE models
                SET activo = false
                WHERE tipo = :tipo AND activo = true AND archivo != :archivo
            """)
            conn.execute(deactivate_query, {
                "tipo": "categoria",
                "archivo": data["modelo_nuevo"]
            })
 
        conn.execute(query, {
            "nombre": "clasificador_categoria",
            "version": data["version_nuevo"],
            "archivo": data["modelo_nuevo"],
            "accuracy": data["accuracy_new"],
            "f1": data["f1_new"],
            "fecha": datetime.now(),
            "activo": data["promovido"],
            "tipo": "categoria"
        })
        conn.commit()
 
    return {
        "status": "evaluation executed",
        "metrics": data
    }
 
# endpoint para ejecutar evaluación del modelo de subcategoria
 
@app.post("/evaluate-subcategory")
def evaluate_subcategory_model(username: str = Depends(autenticar_usuario)):
 
    query = text("""
        SELECT accuracy, f1_score
        FROM models
        WHERE activo = true AND tipo = 'subcategoria'
        ORDER BY fecha_entrenamiento DESC
        LIMIT 1
    """)
 
    modelo_activo = None
 
    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            modelo_activo = result.mappings().first()
    except Exception as e:
        logger.error(f"Error consultando el modelo activo (subcategoria): {e}")
 
    accuracy_actual = modelo_activo["accuracy"] if modelo_activo else None
    f1_actual = modelo_activo["f1_score"] if modelo_activo else None
 
    proceso = subprocess.run(
        [
            "python",
            "evaluate_model_subcategoria.py",
            str(accuracy_actual),
            str(f1_actual)
        ],
        cwd=CATEGORY_SCRIPTS_DIR,
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
        if data["promovido"]:
            deactivate_query = text("""
                UPDATE models
                SET activo = false
                WHERE tipo = :tipo AND activo = true AND archivo != :archivo
            """)
            conn.execute(deactivate_query, {
                "tipo": "subcategoria",
                "archivo": data["modelo_nuevo"]
            })
 
        conn.execute(query, {
            "nombre": "clasificador_subcategoria",
            "version": data["version_nuevo"],
            "archivo": data["modelo_nuevo"],
            "accuracy": data["accuracy_new"],
            "f1": data["f1_new"],
            "fecha": datetime.now(),
            "activo": data["promovido"],
            "tipo": "subcategoria"
        })
        conn.commit()
 
    return {
        "status": "evaluation executed",
        "metrics": data
    }

TipoModelo = Literal["padtypes", "categoria", "subcategoria"]
 
 
def _cargar_modelo_por_tipo(tipo: TipoModelo):
    if tipo == "padtypes":
        cargar_modelo_tipo()
    elif tipo == "categoria":
        cargar_modelo_categoria()
    elif tipo == "subcategoria":
        cargar_modelo_subcategoria()
 
 
def _info_modelo_por_tipo(tipo: TipoModelo):
    if tipo == "padtypes":
        return {
            "tipo": tipo,
            "version": version_modelo,
            "clases": list(modelo.classes_) if modelo is not None else []
        }
    elif tipo == "categoria":
        return {
            "tipo": tipo,
            "version": version_categoria,
            "clases": list(modelo_categoria["label_encoder"].classes_) if modelo_categoria else []
        }
    elif tipo == "subcategoria":
        return {
            "tipo": tipo,
            "version": version_subcategoria,
            "clases": list(modelo_subcategoria["label_encoder"].classes_) if modelo_subcategoria else []
        }
 
 
# endpoint para recargar modelo (padtypes | categoria | subcategoria)
 
@app.post("/reload-model")
def reload_model(tipo: TipoModelo, username: str = Depends(autenticar_usuario)):
 
    try:
        _cargar_modelo_por_tipo(tipo)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo recargar el modelo de '{tipo}': {e}"
        )
 
    info = _info_modelo_por_tipo(tipo)
 
    return {
        "status": "modelo recargado",
        "tipo": tipo,
        "version": info["version"]
    }
 
 
# endpoint informacion del modelo (padtypes | categoria | subcategoria)
 
@app.get("/model-info")
def model_info(tipo: TipoModelo):
    return _info_modelo_por_tipo(tipo)
 
 
# endpoint para activar un modelo especifico (padtypes | categoria | subcategoria)
 
@app.post("/set-model")
def set_model(nombre_modelo: str, tipo: TipoModelo, username: str = Depends(autenticar_usuario)):
 
    query_buscar = text("""
        SELECT archivo
        FROM models
        WHERE archivo = :archivo AND tipo = :tipo
    """)
 
    query_reset = text("""
        UPDATE models
        SET activo = false
        WHERE activo = true AND tipo = :tipo
    """)
 
    query_activate = text("""
        UPDATE models
        SET activo = true
        WHERE archivo = :archivo AND tipo = :tipo
        RETURNING version
    """)
 
    try:
        with engine.begin() as conn:
 
            # verificar que existe PARA ESE TIPO
            result = conn.execute(query_buscar, {"archivo": nombre_modelo, "tipo": tipo})
            existe = result.mappings().first()
 
            if not existe:
                return {"error": f"modelo '{nombre_modelo}' no existe en DB para tipo='{tipo}'"}
 
            # desactivar solo los del mismo tipo
            conn.execute(query_reset, {"tipo": tipo})
 
            # activar el nuevo
            result = conn.execute(query_activate, {"archivo": nombre_modelo, "tipo": tipo})
            row = result.fetchone()
 
        # recargar el modelo correspondiente en memoria
        _cargar_modelo_por_tipo(tipo)
 
        return {
            "status": "modelo actualizado",
            "tipo": tipo,
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
def obtener_tickets_pendientes(limit: int = 10, username: str = Depends(autenticar_usuario)):
    query = text("""
        SELECT
            id, code, incident_title, description, cliente_nombre,
            tipo_predicho, tipo_id_predicho, tipo_confianza, tipo_revision,
            categoria_predicha, categoria_id_predicha, categoria_confianza, categoria_revision,
            subcategoria_predicha, subcategoria_id_predicha, subcategoria_confianza, subcategoria_revision,
            fecha_creacion
        FROM predicciones
        WHERE notificado = FALSE
          AND (
              tipo_revision         = 'pendiente' OR
              categoria_revision    = 'pendiente' OR
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

# enpoint para consultar estado de un solo ticket
@app.get("/feedback/resumen/{id}")
def obtener_resumen_ticket(id: str, username: str = Depends(autenticar_usuario)):
    query = text("SELECT * FROM predicciones WHERE id = :id")
    try:
        with engine.connect() as conn:
            row = conn.execute(query, {"id": id}).mappings().fetchone()
        if not row:
            return {"error": "ticket no encontrado"}
        return dict(row)
    except Exception as e:
        return {"error": "fallo interno", "detalle": str(e)}

# endpoint para marcar correos enviados en la tabla maestra

@app.post("/feedback/correo-enviado")
def marcar_correo_enviado(ids: List[str] = Body(...), username: str = Depends(autenticar_usuario)):
    query = text("""
        UPDATE predicciones
        SET notificado = TRUE, fecha_actualizacion = NOW()
        WHERE id = ANY(:ids)
        AND notificado = FALSE
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

# enpoints de notificacion de errores

# pendientes de notificar
 
@app.get("/tickets-fallidos/hay-pendientes")
def hay_tickets_fallidos_pendientes(username: str = Depends(autenticar_usuario)):
    query = text("""
        SELECT COUNT(*) AS total
        FROM tickets_guardado_fallido
        WHERE notificado = FALSE
    """)
    try:
        with engine.connect() as conn:
            total = conn.execute(query).scalar()
        return {"hay_pendientes": total > 0, "total": total}
    except Exception as e:
        return {"error": "fallo en consulta", "detalle": str(e)}

# endpoint para recuperar el detalle de los tickets con errores
 
@app.get("/tickets-fallidos/pendientes")
def obtener_tickets_fallidos_pendientes(limit: int = 50, username: str = Depends(autenticar_usuario)):
    query = text("""
        SELECT
            id, incidente_codigo, tipo, categoria, subcategoria,
            paso, mensaje_error, fecha_deteccion
        FROM tickets_guardado_fallido
        WHERE notificado = FALSE
        ORDER BY fecha_deteccion ASC
        LIMIT :limit
    """)
    try:
        with engine.connect() as conn:
            rows = conn.execute(query, {"limit": limit}).mappings().all()
        return {"total": len(rows), "tickets": [dict(r) for r in rows]}
    except Exception as e:
        return {"error": "fallo en consulta", "detalle": str(e)}

# endpoint para marcar como notificados los errores ya enviados por correo
 
@app.post("/tickets-fallidos/notificado")
def marcar_tickets_fallidos_notificados(ids: List[int] = Body(..., embed=True), username: str = Depends(autenticar_usuario)):
    query = text("""
        UPDATE tickets_guardado_fallido
        SET notificado = TRUE, fecha_notificado = NOW()
        WHERE id = ANY(:ids)
          AND notificado = FALSE
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
        return {"error": "fallo interno", "detalle": str(e)}

# endpoint para confirmar ticket

@app.post("/feedback/confirm")
def confirmar_ticket_completo(
    payload: ConfirmacionTicketCompleto,
    username: str = Depends(autenticar_usuario)
):
    try:
        with engine.begin() as conn:
            pred = conn.execute(
                text("SELECT * FROM predicciones WHERE id = :id"),
                {"id": payload.id}
            ).mappings().fetchone()

            if not pred:
                return {"error": "ticket no encontrado en predicciones"}

            campos_actualizados = []

            if pred["tipo_revision"] == "pendiente":
                _guardar_correccion(
                    conn, payload.id, "tipo",
                    pred["tipo_predicho"], pred["tipo_id_predicho"],
                    pred["tipo_predicho"], pred["tipo_id_predicho"],
                    "confirmado", username
                )
                campos_actualizados.append("tipo")

            if pred["categoria_revision"] == "pendiente":
                _guardar_correccion(
                    conn, payload.id, "categoria",
                    pred["categoria_predicha"], pred["categoria_id_predicha"],
                    pred["categoria_predicha"], pred["categoria_id_predicha"],
                    "confirmado", username
                )
                campos_actualizados.append("categoria")

            if pred["subcategoria_revision"] == "pendiente":
                _guardar_correccion(
                    conn, payload.id, "subcategoria",
                    pred["subcategoria_predicha"], pred["subcategoria_id_predicha"],
                    pred["subcategoria_predicha"], pred["subcategoria_id_predicha"],
                    "confirmado", username
                )
                campos_actualizados.append("subcategoria")

            if not campos_actualizados:
                return {"status": "sin cambios", "detalle": "ninguna dimensión estaba pendiente"}

        return {"status": "confirmado", "ticket_id": payload.id, "campos_actualizados": campos_actualizados}
    except Exception as e:
        return {"error": "fallo interno", "detalle": str(e)}
    
@app.post("/feedback/corregir")
def corregir_ticket_completo(
    payload: CorreccionTicketCompleto,
    username: str = Depends(autenticar_usuario)
):
    try:
        with engine.begin() as conn:
            pred = conn.execute(
                text("SELECT * FROM predicciones WHERE id = :id"),
                {"id": payload.id}
            ).mappings().fetchone()

            if not pred:
                return {"error": "ticket no encontrado en predicciones"}

            campos_actualizados = []

            if payload.tipo_nombre:
                if payload.tipo_nombre not in mapa_ids:
                    return {"error": "tipo invalido", "tipos_validos": list(mapa_ids.keys())}
                tipo_id_corregido = mapa_ids[payload.tipo_nombre]
                _guardar_correccion(
                    conn, payload.id, "tipo",
                    pred["tipo_predicho"], pred["tipo_id_predicho"],
                    payload.tipo_nombre, tipo_id_corregido,
                    "corregido", username
                )
                campos_actualizados.append("tipo")

            _guardar_correccion(
                conn, payload.id, "categoria",
                pred["categoria_predicha"], pred["categoria_id_predicha"],
                payload.categoria_nombre, payload.categoria_id,
                "corregido", username
            )
            campos_actualizados.append("categoria")

            if payload.subcategoria_id:
                _guardar_correccion(
                    conn, payload.id, "subcategoria",
                    pred["subcategoria_predicha"], pred["subcategoria_id_predicha"],
                    payload.subcategoria_nombre, payload.subcategoria_id,
                    "corregido", username
                )
                campos_actualizados.append("subcategoria")

        return {"status": "corregido", "ticket_id": payload.id, "campos_actualizados": campos_actualizados}
    except Exception as e:
        return {"error": "fallo interno", "detalle": str(e)}

# endpoint para recuperar estado de tickets de feedback por medio de id

@app.get("/feedback/revision/{ticket_id}")
def obtener_revision_ticket(ticket_id: str, username: str = Depends(autenticar_usuario)):
 
    query = text("""
        SELECT id, incident_title, tipo_predicho, tipo_confianza, fecha_creacion, tipo_revision
        FROM predicciones
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
            "confianza": row["tipo_confianza"],
            "fecha": str(row["fecha_creacion"]) if row["fecha_creacion"] else None,
            "ml_revision": row["tipo_revision"],
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
            COUNT(*) as total_predicciones,
            SUM(CASE WHEN tipo_revision = 'NA' THEN 1 ELSE 0 END) as auto_aceptados,
            SUM(CASE WHEN tipo_revision = 'pendiente' THEN 1 ELSE 0 END) as pendientes,
            SUM(CASE WHEN tipo_revision = 'confirmado' THEN 1 ELSE 0 END) as confirmados,
            SUM(CASE WHEN tipo_revision = 'corregido' THEN 1 ELSE 0 END) as corregidos,
            AVG(tipo_confianza) as confianza_promedio
        FROM predicciones
        WHERE tipo_predicho IS NOT NULL
    """)

    with engine.connect() as conn:
        result = conn.execute(query).mappings().first()
    
    return result

# endpoint para obtener precision real de todos los tickets revisados, ¿cuántos estaban bien clasificados?

@app.get("/metrics/accuracy")
def accuray(username: str = Depends(autenticar_usuario)):

    query = text("""
        SELECT
            COUNT(*) FILTER (WHERE p.tipo_id_predicho = c.valor_id_corregido) * 1.0 /
            NULLIF(COUNT(*), 0)
            AS accuracy
        FROM predicciones p
        JOIN correcciones c ON c.prediccion_id = p.id AND c.campo = 'tipo'
        WHERE c.accion IN ('confirmado', 'corregido')
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

    registrar_prediccion(
        ticket_id=ticket.id, code=ticket.code, titulo=ticket.titulo, descripcion=ticket.descripcion,
        client_id=ticket.client_id, cliente_nombre=cliente_nombre,
        categoria={"valor": categoria_nombre, "id": categoria_id, "confianza": confianza, "modelo_version": version_categoria}
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

# -------------- enpoints para recuperar categorias validas--------------

@app.get("/categoria/opciones")
def opciones_categoria(client_id: str, username: str = Depends(autenticar_usuario)):
    cliente_nombre = modelo_categoria["mapa_clientes"].get(client_id.upper(), "/")
    if cliente_nombre == "/":
        return {"cliente": None, "opciones": []}

    cats_cliente = modelo_categoria["mapa_cliente_categorias"].get(cliente_nombre, [])
    opciones = [
        {"nombre": nombre, "id": MAPA_NOMBRE_A_ID.get(nombre, "/")}
        for nombre in cats_cliente
    ]
    return {"cliente": cliente_nombre, "opciones": opciones}

@app.get("/subcategoria/opciones")
def opciones_subcategoria(client_id: str, categoria: str, username: str = Depends(autenticar_usuario)):
    cliente_nombre = modelo_categoria["mapa_clientes"].get(client_id.upper(), "/")
    if cliente_nombre == "/":
        return {"cliente": None, "opciones": []}

    clave   = (cliente_nombre, categoria)
    subcats = modelo_subcategoria["mapa_padre_subcategorias"].get(clave, [])
    if not subcats:
        subcats = modelo_subcategoria["mapa_solo_padre_subcats"].get(categoria, [])

    opciones = [
        {"nombre": nombre, "id": MAPA_NOMBRE_A_ID.get(nombre, "/")}
        for nombre in subcats
    ]
    return {"cliente": cliente_nombre, "categoria": categoria, "opciones": opciones}

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

    registrar_prediccion(
        ticket_id=ticket.id, code=ticket.code, titulo=ticket.titulo, descripcion=ticket.descripcion,
        client_id=ticket.client_id, cliente_nombre=cliente_nombre,
        subcategoria={"valor": subcat_nombre, "id": subcategoria_id, "confianza": confianza, "modelo_version": version_subcategoria}
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

