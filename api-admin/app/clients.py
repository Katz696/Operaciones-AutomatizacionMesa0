import os
import httpx

API_ML_BASE_URL = os.getenv("API_ML_BASE_URL", "http://api-ml:8000")


def api_ml_post(path: str, headers: dict, timeout: float = 30.0, **kwargs) -> httpx.Response:
    url = f"{API_ML_BASE_URL}{path}"
    with httpx.Client(timeout=timeout) as client:
        return client.post(url, headers=headers, **kwargs)