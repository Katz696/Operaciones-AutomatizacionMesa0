import re
from typing import Literal, Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .database import engine
from .dependencies import obtener_usuario_actual

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

# ---- AJUSTAR A TU RBAC ----------------------------------------------------
# Única fuente de verdad de los roles. La vista los pide a GET /usuarios/roles,
# así que si cambias esta tupla no hay que tocar el frontend.
ROLES_VALIDOS = ("admin", "revisor")
ROL_ADMIN = "admin"
# ---------------------------------------------------------------------------

Estado = Literal["todos", "activos", "inactivos"]

# Sin ':' ni espacios: api-proactivanet usa estos usuarios con HTTP Basic, y Basic
# separa usuario y contraseña en el primer ':'.
USERNAME_RE = re.compile(r"[A-Za-z0-9._@-]+")

COLUMNAS_USUARIO = "id, username, role, is_active, created_at"


# ---------- Autorización ----------

def requerir_admin(usuario: dict = Depends(obtener_usuario_actual)) -> dict:
    if usuario.get("role") != ROL_ADMIN:
        raise HTTPException(status_code=403, detail="Solo un administrador puede gestionar usuarios.")
    return usuario


def _es_actual(usuario: dict, fila) -> bool:
    """¿La fila de api_users es la cuenta que está haciendo la petición?"""
    actual_id = usuario.get("id")
    actual_username = usuario.get("username") or usuario.get("sub")
    if actual_id is not None and str(actual_id) == str(fila["id"]):
        return True
    return actual_username is not None and actual_username == fila["username"]


# ---------- Helpers ----------

def _hash_password(password: str) -> str:
    # Hash bcrypt estándar ($2b$...): compatible con la verificación de api-proactivanet.
    # Si api-admin ya tiene su función de hash en el login, usa esa en su lugar.
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _validar_rol(role: str) -> None:
    if role not in ROLES_VALIDOS:
        raise HTTPException(status_code=422, detail=f"Rol no válido. Opciones: {', '.join(ROLES_VALIDOS)}.")


def _obtener(conn, usuario_id: int):
    fila = conn.execute(
        text("SELECT id, username, role, is_active FROM api_users WHERE id = :id"),
        {"id": usuario_id},
    ).mappings().first()
    if not fila:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return fila


def _validar_password(v: str) -> str:
    # bcrypt solo considera los primeros 72 bytes; los caracteres con acento ocupan más de uno.
    if len(v.encode("utf-8")) > 72:
        raise ValueError("La contraseña no puede pasar de 72 bytes.")
    return v


# ---------- Modelos de entrada ----------

class UsuarioNuevo(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=72)
    role: str
    is_active: bool = True

    @field_validator("username")
    @classmethod
    def _username(cls, v: str) -> str:
        v = v.strip()
        if not USERNAME_RE.fullmatch(v):
            raise ValueError("El usuario solo puede tener letras, números, punto, guion, guion bajo y @.")
        return v

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return _validar_password(v)


class CambioRol(BaseModel):
    role: str


class CambioActivo(BaseModel):
    is_active: bool


class CambioPassword(BaseModel):
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return _validar_password(v)


# ---------- Consultas ----------

@router.get("/roles")
def roles(usuario: dict = Depends(requerir_admin)):
    return {"roles": list(ROLES_VALIDOS)}


@router.get("/resumen")
def resumen(usuario: dict = Depends(requerir_admin)):
    q_totales = text("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE is_active IS TRUE) AS activos,
            COUNT(*) FILTER (WHERE is_active IS NOT TRUE) AS inactivos
        FROM api_users
    """)
    q_roles = text("""
        SELECT role, COUNT(*) AS total
        FROM api_users
        GROUP BY role
        ORDER BY total DESC, role
    """)
    with engine.connect() as conn:
        totales = conn.execute(q_totales).mappings().first()
        por_rol = conn.execute(q_roles).mappings().all()

    return {**dict(totales), "por_rol": [dict(r) for r in por_rol]}


@router.get("")
def listar(
    estado: Estado = "todos",
    role: Optional[str] = None,
    buscar: Optional[str] = None,
    usuario: dict = Depends(requerir_admin),
):
    condiciones: list[str] = []
    params: dict = {}

    # Fragmentos fijos: nada de lo que manda el usuario se interpola en el SQL.
    if estado == "activos":
        condiciones.append("u.is_active IS TRUE")
    elif estado == "inactivos":
        condiciones.append("u.is_active IS NOT TRUE")

    if role:
        condiciones.append("u.role = :role")
        params["role"] = role

    if buscar:
        condiciones.append("u.username ILIKE :buscar")
        params["buscar"] = f"%{buscar}%"

    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""

    # correcciones.revisor_id apunta a api_users.id: con eso se ve cuánto ha revisado cada cuenta.
    # Se cuentan tickets distintos porque correcciones guarda una fila por campo corregido.
    query = text(f"""
        SELECT
            u.id, u.username, u.role, u.is_active, u.created_at,
            COUNT(DISTINCT c.prediccion_id) AS tickets_revisados,
            MAX(c.fecha_revision) AS ultima_revision
        FROM api_users u
        LEFT JOIN correcciones c ON c.revisor_id = u.id
        {where}
        GROUP BY u.id
        ORDER BY u.is_active DESC NULLS LAST, u.username
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, params).mappings().all()

    items = [{**dict(r), "es_actual": _es_actual(usuario, r)} for r in rows]
    return {"total": len(items), "items": items}


# ---------- Acciones ----------

@router.post("", status_code=201)
def crear(body: UsuarioNuevo, usuario: dict = Depends(requerir_admin)):
    _validar_rol(body.role)

    try:
        with engine.begin() as conn:
            existe = conn.execute(
                text("SELECT 1 FROM api_users WHERE lower(username) = lower(:u)"),
                {"u": body.username},
            ).first()
            if existe:
                raise HTTPException(status_code=409, detail="Ya existe un usuario con ese nombre.")

            fila = conn.execute(
                text(f"""
                    INSERT INTO api_users (username, password_hash, role, is_active, created_at)
                    VALUES (:u, :h, :r, :a, NOW())
                    RETURNING {COLUMNAS_USUARIO}
                """),
                {"u": body.username, "h": _hash_password(body.password), "r": body.role, "a": body.is_active},
            ).mappings().first()
    except IntegrityError:
        # Carrera entre dos altas con el mismo nombre: gana la restricción UNIQUE de la tabla.
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese nombre.")

    return dict(fila)


@router.post("/{usuario_id}/rol")
def cambiar_rol(usuario_id: int, body: CambioRol, usuario: dict = Depends(requerir_admin)):
    _validar_rol(body.role)

    with engine.begin() as conn:
        objetivo = _obtener(conn, usuario_id)
        if _es_actual(usuario, objetivo) and body.role != objetivo["role"]:
            raise HTTPException(status_code=400, detail="No puedes cambiar tu propio rol.")

        fila = conn.execute(
            text(f"UPDATE api_users SET role = :role WHERE id = :id RETURNING {COLUMNAS_USUARIO}"),
            {"role": body.role, "id": usuario_id},
        ).mappings().first()

    return dict(fila)


@router.post("/{usuario_id}/activo")
def cambiar_activo(usuario_id: int, body: CambioActivo, usuario: dict = Depends(requerir_admin)):
    with engine.begin() as conn:
        objetivo = _obtener(conn, usuario_id)
        if _es_actual(usuario, objetivo) and not body.is_active:
            raise HTTPException(status_code=400, detail="No puedes desactivar tu propia cuenta.")

        fila = conn.execute(
            text(f"UPDATE api_users SET is_active = :a WHERE id = :id RETURNING {COLUMNAS_USUARIO}"),
            {"a": body.is_active, "id": usuario_id},
        ).mappings().first()

    return dict(fila)


@router.post("/{usuario_id}/password")
def restablecer_password(usuario_id: int, body: CambioPassword, usuario: dict = Depends(requerir_admin)):
    with engine.begin() as conn:
        _obtener(conn, usuario_id)
        conn.execute(
            text("UPDATE api_users SET password_hash = :h WHERE id = :id"),
            {"h": _hash_password(body.password), "id": usuario_id},
        )

    return {"status": "ok"}