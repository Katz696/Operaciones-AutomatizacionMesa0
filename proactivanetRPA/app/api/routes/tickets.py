from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List
from app.services.ticket_service import process_tickets_batch_async
import os
import logging
import asyncio
import time
from datetime import datetime

# autentificacion imports
from fastapi.security import HTTPBasic, HTTPBasicCredentials, OAuth2PasswordBearer
import secrets
import bcrypt

from jose import jwt, JWTError

from sqlalchemy import create_engine, text

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/no-aplica", auto_error=False)
security = HTTPBasic(auto_error=False)

# ------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

router = APIRouter()

_batch_lock = asyncio.Lock()
_batch_start_time: float | None = None

class TicketItem(BaseModel):
    code: str
    # cliente: str
    tipo: str
    categoria: str
    subcategoria: str

class TicketBatchRequest(BaseModel):
    tickets: List[TicketItem]

class TicketResult(BaseModel):
    code: str
    status: str        # "success" | "error"
    message: str

class TicketBatchResponse(BaseModel):
    total: int
    success: int
    failed: int
    results: List[TicketResult]

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

# funcion para autentificar usuario

def autenticar_usuario(
    token: str = Depends(oauth2_scheme),
    credentials: HTTPBasicCredentials = Depends(security),
):
    # Camino 1: Bearer JWT (api-admin reenviando el token del usuario logueado)
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except JWTError:
            raise HTTPException(status_code=401, detail="Token inválido o expirado")

        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Token inválido")
        return username

    # Camino 2: Basic Auth (n8n u otros clientes de servicio, como ya funcionaba)
    if credentials:
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
        if not verify_password(credentials.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas",
                headers={"WWW-Authenticate": "Basic"},
            )

        return user["username"]

    raise HTTPException(status_code=401, detail="Falta autenticación", headers={"WWW-Authenticate": "Bearer"})
    
    
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.post("/tickets/batch", response_model=TicketBatchResponse)
async def process_tickets(
    payload: TicketBatchRequest,
    username: str = Depends(autenticar_usuario)
):
    global _batch_start_time

    if not payload.tickets:
        raise HTTPException(status_code=400, detail="La lista de tickets está vacía")

    if _batch_lock.locked():
        segundos_transcurridos = int(time.time() - _batch_start_time) if _batch_start_time else 0
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Ya hay un batch en procesamiento "
                f"(lleva {segundos_transcurridos}s en ejecución). "
                f"Intenta de nuevo en unos momentos."
            )
        )

    async with _batch_lock:
        _batch_start_time = time.time()
        logger.info(f"[{username}] Iniciando batch de {len(payload.tickets)} tickets")
        try:
            results = await process_tickets_batch_async(payload.tickets)
        finally:
            # siempre se limpia aunque falle el proceso
            _batch_start_time = None
            logger.info(f"[{username}] Batch finalizado")

    success = sum(1 for r in results if r["status"] == "success")
    failed = len(results) - success

    return TicketBatchResponse(
        total=len(results),
        success=success,
        failed=failed,
        results=[TicketResult(**r) for r in results]
    )