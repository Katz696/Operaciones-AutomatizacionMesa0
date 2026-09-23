import os
from datetime import datetime, timedelta

import bcrypt
from jose import jwt

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 60 * 8))  # 8 horas por defecto

if not JWT_SECRET:
    raise RuntimeError(
        "Falta la variable de entorno JWT_SECRET. "
        "Generar una con: python -c \"import secrets; print(secrets.token_hex(32))\""
    )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def crear_access_token(username: str, role: str) -> str:
    expira = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": username, "role": role, "exp": expira}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decodificar_token(token: str) -> dict:
    # jwt.decode ya lanza JWTError si expiró o la firma no coincide
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
