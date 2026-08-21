from playwright.sync_api import sync_playwright
from app.automation.proactivanet import ensure_session, search_and_open_ticket
from dotenv import load_dotenv
import os

load_dotenv()

USER = os.getenv("PROACTIVA_USER")
PASS = os.getenv("PROACTIVA_PASSWORD")

# --- datos de prueba, edítalos según el ticket que quieras probar ---
INCIDENT_CODE = "INC 2026-003937"
TIPO = "Incidente"
CATEGORIA_PRINCIPAL = "GCTI 11. Soporte a SAP"
CATEGORIA_SECUNDARIA = "11.1 Falla de SAP"
CLIENTE = "Gconsultores"
# ---------------------------------------------------------------

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=500)  # slow_mo para ver cada acción
    context = browser.new_context()
    page = context.new_page()

    ensure_session(context, page, USER, PASS)

    search_and_open_ticket(
    page=page,
    context=context,
    incident_code=INCIDENT_CODE,
    # cliente="Gconsultores",
    tipo=TIPO,
    categoria=CATEGORIA_PRINCIPAL,
    subcategoria=CATEGORIA_SECUNDARIA
    )

    # input("Presiona ENTER para cerrar el navegador...")
    browser.close()