import time
from functools import wraps
from app.utils.logger import log

def retry(max_retries=3, delay=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    log("warning", "Retry failed",
                        attempt=attempt, error=str(e))

                    if attempt == max_retries:
                        raise e

                    time.sleep(delay)
        return wrapper
    return decorator