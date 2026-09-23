"""
Script para insertar un nuevo usuario en la tabla api_users.
Uso: python crear_admin.py

Requiere las variables de entorno:
  - DATABASE_URL  (misma que usan api-proactivanet / api-ml)

Requiere las librerías: sqlalchemy, psycopg2-binary, bcrypt
    pip install sqlalchemy psycopg2-binary bcrypt
"""

import os
import sys
from datetime import datetime, timezone

import bcrypt
from sqlalchemy import create_engine, text

# ---- Configuración del nuevo usuario ----
NUEVO_USERNAME = "administrador"
NUEVA_PASSWORD = "Password01"  # contraseña provisional, cambiarla después
NUEVO_ROLE = "admin"           # ajustar según los valores que uses en RBAC
IS_ACTIVE = True


def main():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: la variable de entorno DATABASE_URL no está definida.")
        sys.exit(1)

    # Generar el hash bcrypt de la contraseña
    password_hash = bcrypt.hashpw(
        NUEVA_PASSWORD.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    engine = create_engine(database_url, pool_pre_ping=True)

    insert_query = text(
        """
        INSERT INTO api_users (username, password_hash, is_active, created_at, role)
        VALUES (:username, :password_hash, :is_active, :created_at, :role)
        ON CONFLICT (username) DO NOTHING
        RETURNING username
        """
    )

    with engine.begin() as conn:
        result = conn.execute(
            insert_query,
            {
                "username": NUEVO_USERNAME,
                "password_hash": password_hash,
                "is_active": IS_ACTIVE,
                "created_at": datetime.now(timezone.utc),
                "role": NUEVO_ROLE,
            },
        )
        row = result.fetchone()

    if row:
        print(f"Usuario '{NUEVO_USERNAME}' creado correctamente con role='{NUEVO_ROLE}'.")
    else:
        print(
            f"No se insertó ningún registro: probablemente ya existe un usuario "
            f"'{NUEVO_USERNAME}' (constraint UNIQUE en username)."
        )


if __name__ == "__main__":
    main()