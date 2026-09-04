import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://servicedesk.gconsultores.com.mx/proactivanet/library/loginform/default.paw?pawLoginFormSrcUrl=%2fproactivanet%2fservicedesk%2fdefault.paw&pawLoginFormStatus=1&pawLoginFormSec=0")
    page.locator("#theUName").click()
    page.locator("#theUName").fill("MSN0ROBOT")
    page.locator("#thePwd").click()
    page.locator("#thePwd").fill("ServicioMesa0ProcesaTicketsAgil2026!")
    page.get_by_role("button", name="Acceso usuario").click()
    page.locator("iframe[name=\"pawMenuTabFrame\"]").content_frame.get_by_role("cell").nth(4).click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_role("link", name="Nuevas").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_role("cell", name="REQ 2026-004529").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.locator("#pawFormPageLoadingOverlay").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.locator("#pawFormPageLoadingOverlay").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_role("row", name="Atendido por la empresa::").get_by_role("button").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_text("Gconsultores - OP").nth(2).click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_role("table", name="Forma de servicio").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_text("Soporte 5 x").nth(1).click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_role("cell", name="Operación Continua Pulse para").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_role("cell", name="Operación Continua Pulse para").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_role("cell", name="Operación Continua Pulse para").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_role("table", name="Medio").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_text("Portal").nth(4).click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_role("table", name="CI´S").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_text("NINGUNO", exact=True).nth(1).click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_role("cell", name="Pulse para seleccionar el valor", exact=True).nth(5).click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_role("cell", name="Pulse para seleccionar el valor", exact=True).nth(5).click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.locator(".pawDFMultiFunOver > tbody > .pawDFMultiFunTr > .pawDFMultiFunTd0").click()
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_role("button", name="Cancelar cambios").click()
    page.close()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
