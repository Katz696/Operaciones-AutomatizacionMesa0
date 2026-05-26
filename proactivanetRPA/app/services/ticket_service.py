from playwright.sync_api import sync_playwright
from app.automation.proactivanet import search_and_open_ticket, ensure_session
from app.utils.logger import log
import os
import asyncio

USER = os.getenv("PROACTIVA_USER")
PASS = os.getenv("PROACTIVA_PASSWORD")


def process_tickets_batch(tickets) -> list[dict]:
    """
    Abre UNA sola sesión de Playwright y procesa todos los tickets secuencialmente.
    Retorna una lista de resultados por ticket.
    """
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Establecer sesión una sola vez
        try:
            ensure_session(context, page, USER, PASS)
            log("info", "Sesión iniciada para el batch")
        except Exception as e:
            log("error", "No se pudo establecer sesión, abortando batch", error=str(e))
            browser.close()
            # Marcar todos como fallidos si no hay sesión
            return [
                {
                    "code": t.code,
                    "status": "error",
                    "message": f"No se pudo establecer sesión: {e}"
                }
                for t in tickets
            ]

        # Procesar cada ticket
        for ticket in tickets:
            log("info", f"Procesando ticket {ticket.code} | Categoría: {ticket.categoria}")
            try:
                search_and_open_ticket(
                    page=page,
                    context=context,
                    incident_code=ticket.code,
                    tipo=ticket.categoria
                )
                results.append({
                    "code": ticket.code,
                    "status": "success",
                    "message": "Ticket procesado correctamente"
                })
                log("info", f"✓ Ticket {ticket.code} completado")

            except Exception as e:
                log("error", f"✗ Error en ticket {ticket.code}", error=str(e))
                results.append({
                    "code": ticket.code,
                    "status": "error",
                    "message": str(e)
                })
                # Intentar recuperar la sesión para el siguiente ticket
                try:
                    ensure_session(context, page, USER, PASS)
                    log("info", f"Sesión recuperada después del error en {ticket.code}")
                except Exception as recovery_error:
                    log("error", "No se pudo recuperar la sesión", error=str(recovery_error))

        browser.close()
        log("info", f"Batch completado: {len(results)} tickets procesados")

    return results

async def process_tickets_batch_async(tickets) -> list[dict]:
    return await asyncio.to_thread(process_tickets_batch, tickets)