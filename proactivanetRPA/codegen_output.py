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
    page.locator("iframe[name=\"pawMenuTopFrame\"]").content_frame.get_by_role("textbox").click()
    page.locator("iframe[name=\"pawMenuTopFrame\"]").content_frame.get_by_role("textbox").fill("INC 2026-003937")
    page.locator("iframe[name=\"pawMenuTopFrame\"]").content_frame.get_by_title("Buscar - Incidencias /").get_by_role("button").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_role("cell", name="INC 2026-").click()
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_role("button", name="Editar").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.locator(".pawDFMultiFunSpanOver").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_text("Incidente", exact=True).click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.locator("#pawId866109592").get_by_text("/", exact=True).click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.locator(".pawTreeNodeHeaderOver > span > #pawExp").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.locator(".pawTreeNodeHeaderOver").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_text("INFORMACIÓN ADICIONAL", exact=True).click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_text("GENERAL", exact=True).click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_text("/GCTI 11. Soporte a SAP/11.1").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_text("FINBE01. Servicios de").click()
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_text("/FINBE01. Servicios de").click()
    page.close()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
