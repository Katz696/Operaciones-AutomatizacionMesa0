import os
import httpx

API_ML_BASE_URL = os.getenv("API_ML_BASE_URL", "http://api-ml:8000")


def api_ml_post(path: str, headers: dict, timeout: float = 30.0, **kwargs) -> httpx.Response:
    url = f"{API_ML_BASE_URL}{path}"
    with httpx.Client(timeout=timeout) as client:
<<<<<<< HEAD
        return client.post(url, headers=headers, **kwargs)

def api_ml_request(method: str, path: str, headers: dict, timeout: float = 30.0, **kwargs) -> httpx.Response:
    url = f"{API_ML_BASE_URL}{path}"
    with httpx.Client(timeout=timeout) as client:
        return client.request(method, url, headers=headers, **kwargs)
=======
        return client.post(url, headers=headers, **kwargs)
>>>>>>> 0cd777d9e435266f99d7e0b5f43263882b102b18
