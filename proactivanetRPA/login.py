from playwright.sync_api import sync_playwright

def save_session():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # visible para login
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://servicedesk.gconsultores.com.mx/proactivanet/library/loginform/default.paw")

        print(" Inicia sesión manualmente...")
        input("Presiona ENTER cuando ya estés logueado...")

        context.storage_state(path="state.json")

        print(" Sesión guardada en state.json")
        browser.close()

save_session()