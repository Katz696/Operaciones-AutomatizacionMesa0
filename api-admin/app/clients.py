import os
import httpx

API_ML_BASE_URL = os.getenv("API_ML_BASE_URL", "http://api-ml:8000")
API_ML_SERVICE_USER = os.getenv("API_ML_SERVICE_USER")
API_ML_SERVICE_PASSWORD = os.getenv("API_ML_SERVICE_PASSWORD")


def _auth() -> httpx.BasicAuth:
    if not API_ML_SERVICE_USER or not API_ML_SERVICE_PASSWORD:
        raise RuntimeError(
            "Faltan API_ML_SERVICE_USER / API_ML_SERVICE_PASSWORD: "
            "api-admin necesita un usuario de servicio dado de alta en api_users "
            "para llamar a los endpoints protegidos de api-ml."
        )
    return httpx.BasicAuth(API_ML_SERVICE_USER, API_ML_SERVICE_PASSWORD)


def api_ml_post(path: str, timeout: float = 30.0, **kwargs) -> httpx.Response:
    url = f"{API_ML_BASE_URL}{path}"
    with httpx.Client(timeout=timeout) as client:
        return client.post(url, auth=_auth(), **kwargs)