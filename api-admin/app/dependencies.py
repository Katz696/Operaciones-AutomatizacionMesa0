from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from .security import decodificar_token

# tokenUrl es solo informativo para la doc /docs (Swagger), no un endpoint real que se llame internamente
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def obtener_usuario_actual(token: str = Depends(oauth2_scheme)) -> dict:
    credenciales_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o token expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decodificar_token(token)
        username = payload.get("sub")
        role = payload.get("role")
        if username is None or role is None:
            raise credenciales_invalidas
    except JWTError:
        raise credenciales_invalidas

    return {"username": username, "role": role}


def requerir_rol(*roles_permitidos: str):
    """
    Uso: Depends(requerir_rol("admin")) o Depends(requerir_rol("admin", "revisor"))
    """
    def _verificar(usuario: dict = Depends(obtener_usuario_actual)) -> dict:
        if usuario["role"] not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rol '{usuario['role']}' no autorizado para esta acción"
            )
        return usuario
    return _verificar


def obtener_token_crudo(token: str = Depends(oauth2_scheme)) -> str:
    """
    Igual que obtener_usuario_actual pero devuelve el JWT tal cual,
    para reenviarlo a api-ml (que valida ese mismo token con el
    mismo JWT_SECRET) en vez de generar credenciales aparte.
    """
    return token