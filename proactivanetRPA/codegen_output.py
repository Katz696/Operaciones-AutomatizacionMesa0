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
    page.locator("iframe[name=\"pawMenuTopFrame\"]").content_frame.get_by_role("textbox").press("Enter")
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_role("cell", name="INC 2026-").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_role("button", name="Editar").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.locator(".pawDFMultiFunReqButtonOver").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.locator("#pawId37554849").get_by_text("/GCTI 01. Apoyo").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_text("GCTI 17. Soporte a equipo de cómputo personal").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_text("/GCTI 17. Soporte a equipo de cómputo personal").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.locator("#pawId37554849").get_by_role("button", name="Pulse para buscar el valor").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.locator("#ui-id-1").content_frame.locator("iframe[name=\"theIFrame\"]").content_frame.locator("#pawDlgSearchStr").fill("GCTI 17. Soporte a equipo de cómputo personal")
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.locator("#ui-id-1").content_frame.locator("iframe[name=\"theIFrame\"]").content_frame.get_by_role("button", name="Aceptar").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_text("/GCTI 17. Soporte a equipo de").nth(1).click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.locator("#pawId37554849").get_by_role("button", name="Pulse para buscar el valor").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.locator("#ui-id-3").content_frame.locator("iframe[name=\"theIFrame\"]").content_frame.get_by_role("button", name="Aceptar").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_title("/GCTI 17. Soporte a equipo de cómputo personal/17.1 Activación de office").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.locator("#pawId37554849").get_by_role("button", name="Pulse para buscar el valor").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.locator("#ui-id-5").content_frame.locator("iframe[name=\"theIFrame\"]").content_frame.get_by_role("button", name="Aceptar").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_title("/GCTI 17. Soporte a equipo de cómputo personal/17.2 Instalación de software bá").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.locator("#pawId37554849").get_by_role("button", name="Pulse para buscar el valor").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.locator("#ui-id-7").content_frame.locator("iframe[name=\"theIFrame\"]").content_frame.get_by_role("button", name="Aceptar").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_title("/GCTI 17. Soporte a equipo de cómputo personal/17.5 Actualización de Antivirus").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_text("/GCTI 17. Soporte a equipo de cómputo personal/17.5 Actualización de Antivirus").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.locator(".pawTreeNodeHeaderOver").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_role("cell", name="Incidente Pulse para seleccionar el valor", exact=True).click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.locator("#padTypes_id").get_by_text("Incidente").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.locator(".pawOptOver").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_text("Gconsultores", exact=True).click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.locator(".pawOptOver").click()
    page.locator("iframe[name=\"pawContentFrame\"]").content_frame.locator("iframe[name=\"rightFrame\"]").content_frame.get_by_role("button", name="Guardar cambios").click()
    page.close()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
