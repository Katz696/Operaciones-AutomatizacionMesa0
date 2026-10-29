from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response

from .clients import api_ml_request
from .dependencies import requerir_rol

router = APIRouter(
    prefix="/datasets",
    tags=["datasets"],
    dependencies=[Depends(requerir_rol("admin"))],
)


def _forward_auth_header(request: Request) -> dict:
    auth = request.headers.get("authorization")
    if not auth:
        raise HTTPException(status_code=401, detail="Falta token de autenticación")
    return {"Authorization": auth}


def _json_o_error(resp):
    """Devuelve el JSON de api-ml o relanza su error conservando status y detail
    (el detail puede ser un dict, p. ej. en errores de estructura del CSV)."""
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=resp.status_code, detail=detail)
    return resp.json()


def _llamar(method: str, path: str, request: Request, **kwargs):
    try:
        return api_ml_request(method, path, _forward_auth_header(request), **kwargs)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error consultando api-ml: {e}")


@router.get("")
def listar(request: Request):
    return _json_o_error(_llamar("GET", "/datasets", request))


@router.get("/{key}/preview")
def preview(key: str, request: Request, limit: int = 50, offset: int = 0):
    resp = _llamar("GET", f"/datasets/{key}/preview", request,
                   params={"limit": limit, "offset": offset})
    return _json_o_error(resp)


@router.get("/{key}/download")
def descargar(key: str, request: Request):
    resp = _llamar("GET", f"/datasets/{key}/download", request)
    if resp.status_code >= 400:
        _json_o_error(resp)
    return Response(
        content=resp.content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{key}.csv"'},
    )


@router.put("/{key}")
def reemplazar(key: str, request: Request, archivo: UploadFile = File(...)):
    contenido = archivo.file.read()
    resp = _llamar(
        "PUT", f"/datasets/{key}", request, timeout=60.0,
        files={"archivo": (archivo.filename or f"{key}.csv", contenido, "text/csv")},
    )
    return _json_o_error(resp)


@router.delete("/{key}")
def eliminar(key: str, request: Request):
    return _json_o_error(_llamar("DELETE", f"/datasets/{key}", request))