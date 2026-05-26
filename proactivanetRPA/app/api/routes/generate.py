from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from app.api.routes.tickets import autenticar_usuario   # reutiliza tu auth existente
from app.services.generate_service import build_tickets
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class SyntheticTicket(BaseModel):
    Title: str
    Description: str
    CreationDate: str
    FederatedCode: Optional[str] = None
    PanUsers_idSource: str
    PanLocations_id: Optional[str] = None
    PawSvcAuthUsers_idCreator: str
    PadSources_id: str
    PadStatus_id: str
    PadTypes_id: Optional[str] = None
    PadPortfolio_id: Optional[str] = None
    PadCategories_id: str
    PadPriorities_id: Optional[str] = None
    PadUrgencies_id: Optional[str] = None
    PadImpacts_id: Optional[str] = None
    SendUserNotification: bool

class SyntheticTicketWithMeta(SyntheticTicket):
    _meta: Optional[dict] = None

    class Config:
        extra = "allow"   # permite el campo _meta sin romper la validación

class GenerateResponse(BaseModel):
    count: int
    tickets: List[dict]    # dict para que _meta pase sin conflicto de serialización


# ── Endpoint ──────────────────────────────────────────────────────────────────

VALID_CATEGORIES = [
    "incidente_red",
    "incidente_hardware",
    "incidente_software",
    "requerimiento_acceso",
    "requerimiento_instalacion",
]

@router.get(
    "/tickets/generate",
    response_model=GenerateResponse,
    summary="Genera tickets sintéticos listos para POST /api/Incidents",
    tags=["Generación sintética"],
)
async def generate_tickets(
    count: int = Query(default=1, ge=1, le=100, description="Cantidad de tickets (1–100)"),
    category: Optional[str] = Query(
        default=None,
        description=f"Categoría fija. Opciones: {', '.join(VALID_CATEGORIES)}. Omitir = aleatoria."
    ),
    seed: Optional[int] = Query(default=None, description="Seed para reproducibilidad en pruebas"),
    include_meta: bool = Query(default=True, description="Incluye _meta con trazabilidad interna"),
    username: str = Depends(autenticar_usuario),
):
    if category and category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Categoría '{category}' no válida. Opciones: {VALID_CATEGORIES}",
        )

    logger.info(f"[{username}] Generando {count} tickets sintéticos | category={category} seed={seed}")

    tickets = build_tickets(
        count=count,
        category_key=category,
        seed=seed,
        include_meta=include_meta,
    )

    logger.info(f"[{username}] {len(tickets)} tickets generados correctamente")
    return GenerateResponse(count=len(tickets), tickets=tickets)