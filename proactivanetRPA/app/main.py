from fastapi import FastAPI
from app.api.routes.tickets import router as tickets_router
from app.api.routes.generate import router as generate_router

app = FastAPI(
    title="Proactivanet Automation API",
    description="Automatización de tickets via Playwright",
    version="1.0.0"
)

app.include_router(tickets_router, prefix="/api/v1")

app.include_router(generate_router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "ok"}