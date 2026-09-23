import bcrypt
from fastapi import FastAPI, HTTPException, Depends, status
from sqlalchemy import text

from .database import engine
from .security import verify_password, crear_access_token
from .dependencies import obtener_usuario_actual, requerir_rol
from .schemas import LoginRequest, TokenResponse, UsuarioCreate, UsuarioOut, ConfigValor
from .predicciones import router as predicciones_router
from .predicciones import router as predicciones_router
from .modelos import router as modelos_router
from .metricas import router as metricas_router
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(
    title="API Admin - Consola de Clasificación de Tickets",
    version="0.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predicciones_router)
app.include_router(predicciones_router)
app.include_router(modelos_router)
app.include_router(metricas_router)


@app.get("/health")
def health_check():
    resultado = {"api": "ok"}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        resultado["database"] = "ok"
    except Exception:
        resultado["database"] = "error"
    return resultado



# ============================================================
# Autenticación
# ============================================================

@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    query = text("""
        SELECT username, password_hash, role, is_active
        FROM api_users
        WHERE username = :username
    """)
    with engine.connect() as conn:
        user = conn.execute(query, {"username": payload.username}).mappings().first()

    if not user or not user["is_active"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    token = crear_access_token(user["username"], user["role"])
    return TokenResponse(access_token=token, role=user["role"])


@app.get("/auth/me")
def quien_soy(usuario: dict = Depends(obtener_usuario_actual)):
    return usuario


# ============================================================
# Gestión de usuarios (solo admin)
# ============================================================

@app.get("/users", response_model=list[UsuarioOut])
def listar_usuarios(usuario: dict = Depends(requerir_rol("admin"))):
    query = text("SELECT id, username, role, is_active FROM api_users ORDER BY id")
    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()
    return list(rows)


@app.post("/users", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def crear_usuario(payload: UsuarioCreate, usuario: dict = Depends(requerir_rol("admin"))):
    if payload.role not in ("admin", "revisor", "lectura"):
        raise HTTPException(status_code=400, detail="role debe ser admin | revisor | lectura")

    password_hash = bcrypt.hashpw(
        payload.password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    query = text("""
        INSERT INTO api_users (username, password_hash, role, is_active, created_at)
        VALUES (:username, :password_hash, :role, true, now())
        RETURNING id, username, role, is_active
    """)
    try:
        with engine.begin() as conn:
            row = conn.execute(query, {
                "username": payload.username,
                "password_hash": password_hash,
                "role": payload.role
            }).mappings().first()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo crear el usuario: {e}")

    return dict(row)


@app.patch("/users/{user_id}/estado")
def cambiar_estado_usuario(
    user_id: int, activo: bool,
    usuario: dict = Depends(requerir_rol("admin"))
):
    query = text("UPDATE api_users SET is_active = :activo WHERE id = :id RETURNING id")
    with engine.begin() as conn:
        row = conn.execute(query, {"activo": activo, "id": user_id}).first()
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"id": user_id, "is_active": activo}


# ============================================================
# Configuración (ml_config)
# ============================================================

@app.get("/config")
def listar_config(usuario: dict = Depends(obtener_usuario_actual)):
    query = text("SELECT clave, valor, actualizado_en FROM ml_config ORDER BY clave")
    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()
    return list(rows)


@app.get("/config/{clave}")
def obtener_config(clave: str, usuario: dict = Depends(obtener_usuario_actual)):
    query = text("SELECT valor, actualizado_en FROM ml_config WHERE clave = :clave")
    with engine.connect() as conn:
        row = conn.execute(query, {"clave": clave}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No existe la clave '{clave}' en ml_config")
    return dict(row)


@app.put("/config/{clave}")
def actualizar_config(
    clave: str, payload: ConfigValor,
    usuario: dict = Depends(requerir_rol("admin"))
):
    query = text("""
        UPDATE ml_config
        SET valor = :valor, actualizado_en = now()
        WHERE clave = :clave
        RETURNING clave, valor, actualizado_en
    """)
    with engine.begin() as conn:
        row = conn.execute(query, {"clave": clave, "valor": payload.valor}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No existe la clave '{clave}' en ml_config")
    return dict(row)
