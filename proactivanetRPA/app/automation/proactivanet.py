from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from app.utils.logger import log
from app.utils.screenshots import take_screenshot
from dotenv import load_dotenv
import os
import re
from playwright.sync_api import Playwright, expect

load_dotenv()

BASE_URL = "https://servicedesk.gconsultores.com.mx/proactivanet/servicedesk/default.paw"
LOGIN_URL = "https://servicedesk.gconsultores.com.mx/proactivanet/library/loginform/default.paw"
STATE_FILE = "state.json"
USER = os.getenv("PROACTIVA_USER")
PASS = os.getenv("PROACTIVA_PASSWORD")
ACENTO = "\u00b4"


def is_logged_in(page):
    try:
        return "loginform" not in page.url.lower()
    except Exception as e:
        log("warning", "No se pudo verificar si hay sesión activa", error=str(e))
        return False


def login(page, username, password):
    try:
        page.goto(LOGIN_URL)
        page.fill("#theUName", username)
        page.fill("#thePwd", password)
        page.click("#divLogOutLoginUserPass > input[type=checkbox]")
        page.click("#theSubmitBtn")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)
        log("info", "Login ejecutado correctamente")
    except PlaywrightTimeoutError as e:
        take_screenshot(page, "login_timeout")
        raise Exception(f"Timeout durante el login: {e}")
    except Exception as e:
        take_screenshot(page, "login_error")
        raise Exception(f"Error inesperado durante el login: {e}")


def ensure_session(context, page, username, password):
    try:
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
    except PlaywrightTimeoutError as e:
        take_screenshot(page, "session_goto_timeout")
        raise Exception(f"Timeout al navegar a BASE_URL: {e}")

    if is_logged_in(page):
        log("info", "Sesión válida reutilizada")
        return

    log("info", "Sesión inválida, haciendo login...")
    login(page, username, password)

    try:
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
    except PlaywrightTimeoutError as e:
        take_screenshot(page, "post_login_goto_timeout")
        raise Exception(f"Timeout al navegar a BASE_URL después del login: {e}")

    if not is_logged_in(page):
        take_screenshot(page, "login_failed")
        raise Exception("Login falló: la sesión no se estableció correctamente después del login")

    try:
        context.storage_state(path=STATE_FILE)
        log("info", "Nueva sesión guardada")
    except Exception as e:
        log("warning", "No se pudo guardar el estado de sesión", error=str(e))


def search_and_open_ticket(page, context, incident_code, tipo):
    try:
        ensure_session(context, page, USER, PASS)
    except Exception as e:
        raise Exception(f"Error al establecer sesión antes de buscar ticket '{incident_code}': {e}")

    # take_screenshot(page, "before_search")

    # Buscar en el top frame
    try:
        top_frame = page.frame_locator("iframe[name='pawMenuTopFrame']")
        page.wait_for_timeout(2000)
        search_input = top_frame.locator("#pawTheFind input")
        search_input.wait_for(timeout=10000)
        search_input.fill("")
        search_input.fill(incident_code)
        search_input.press("Enter")
        log("info", f"Búsqueda ejecutada para ticket '{incident_code}'")
    except PlaywrightTimeoutError as e:
        take_screenshot(page, "search_input_timeout")
        raise Exception(f"Timeout al intentar buscar el ticket '{incident_code}' en el top frame: {e}")
    except Exception as e:
        take_screenshot(page, "search_input_error")
        raise Exception(f"Error al buscar el ticket '{incident_code}': {e}")

    # Esperar resultados
    try:
        content_frame = page.frame_locator("iframe[name='pawContentFrame']")
        right_frame = content_frame.frame_locator("iframe[name='rightFrame']")
        rows = right_frame.locator("#pawTheTb tbody tr[class*='pawPTableTbDtTr']")
        rows.first.wait_for(timeout=10000)
        # take_screenshot(page, f"results_{incident_code}")
    except PlaywrightTimeoutError as e:
        take_screenshot(page, "results_timeout")
        raise Exception(f"Timeout esperando resultados de búsqueda para '{incident_code}': {e}")
    except Exception as e:
        take_screenshot(page, "results_error")
        raise Exception(f"Error al cargar resultados de búsqueda para '{incident_code}': {e}")

    # Abrir el ticket
    try:
        row = rows.filter(has_text=incident_code).first
        if row.count() == 0:
            raise Exception(f"Ticket '{incident_code}' no encontrado en los resultados")
        row.click()
        log("info", "Ticket abierto", incident_code=incident_code)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(6000)
    except Exception as e:
        take_screenshot(page, "open_ticket_error")
        raise Exception(f"Error al abrir el ticket '{incident_code}': {e}")

    # Click en pestaña GENERAL y botón editar
    try:
        page.locator("iframe[name=\"pawContentFrame\"]").content_frame \
            .locator("iframe[name=\"rightFrame\"]").content_frame \
            .locator("span").filter(has_text="GENERAL").nth(1).click()

        search_edit_button = right_frame.locator("#pageEditBtn img")
        search_edit_button.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(6000)
        # take_screenshot(page, "after_edit_click")
        log("info", "Modo edición activado")
    except PlaywrightTimeoutError as e:
        take_screenshot(page, "edit_button_timeout")
        raise Exception(f"Timeout al activar modo edición del ticket '{incident_code}': {e}")
    except Exception as e:
        take_screenshot(page, "edit_button_error")
        raise Exception(f"Error al activar modo edición del ticket '{incident_code}': {e}")

    # Ejecutar pasos de edición
    try:
        select_ticket_type(page, tipo)
    except Exception as e:
        save_ticket(page)  # Intentar guardar antes de salir por error
        raise Exception(f"Error al seleccionar tipo de ticket '{tipo}': {e}")

    try:
        select_category(page, "/")
    except Exception as e:
        raise Exception(f"Error al seleccionar categoría '/': {e}")

    try:
        fill_additional_info(page)
    except Exception as e:
        raise Exception(f"Error al llenar información adicional: {e}")

    try:
        save_ticket(page)
    except Exception as e:
        raise Exception(f"Error al guardar el ticket '{incident_code}': {e}")


def select_ticket_type(page, tipo_nombre: str):
    try:
        type_span = page.locator("iframe[name=\"pawContentFrame\"]").content_frame \
            .locator("iframe[name=\"rightFrame\"]").content_frame \
            .locator("#padTypes_id > tbody > .pawDFMultiFunTr > .pawDFMultiFunTd1")

        option = page.locator("iframe[name=\"pawContentFrame\"]").content_frame \
            .locator("iframe[name=\"rightFrame\"]").content_frame \
            .get_by_text(tipo_nombre, exact=True)

        select_option(page, type_span, option)
        log("info", f"Tipo de ticket '{tipo_nombre}' seleccionado")
    except PlaywrightTimeoutError as e:
        take_screenshot(page, "ticket_type_timeout")
        raise Exception(f"Timeout al seleccionar el tipo de ticket '{tipo_nombre}': {e}")
    except Exception as e:
        take_screenshot(page, "ticket_type_error")
        raise Exception(f"Error al seleccionar el tipo de ticket '{tipo_nombre}': {e}")


def select_category(page, categoria_nombre: str):
    right_frame = next(
        (f for f in page.frames if f.name == "rightFrame"), None
    )

    if not right_frame:
        raise Exception("No se encontró rightFrame al intentar seleccionar categoría")

    try:
        right_frame.wait_for_selector("#padCategories_id", timeout=15000)
    except PlaywrightTimeoutError as e:
        take_screenshot(page, "category_selector_timeout")
        raise Exception(f"Timeout esperando el selector de categorías '#padCategories_id': {e}")

    try:
        btn = page.locator("iframe[name=\"pawContentFrame\"]").content_frame \
            .locator("iframe[name=\"rightFrame\"]").content_frame \
            .locator("#padCategories_id > tbody > .pawDFMultiFunReqTr > td:nth-child(4)")
        btn.click()
        page.wait_for_timeout(1500)
        # take_screenshot(page, "category_popup_open")
    except PlaywrightTimeoutError as e:
        take_screenshot(page, "category_btn_timeout")
        raise Exception(f"Timeout al abrir el popup de categorías: {e}")
    except Exception as e:
        take_screenshot(page, "category_btn_error")
        raise Exception(f"Error al abrir el popup de categorías: {e}")

    try:
        clicked = right_frame.evaluate(f"""
            () => {{
                const target = {repr(categoria_nombre)}.trim();

                const candidates = Array.from(document.querySelectorAll(
                    'ul li, .pawDropDown li, .pawList li, [class*="List"] li, [class*="list"] li'
                ));

                let el = candidates.find(e => {{
                    const text = (e.innerText || e.textContent || '').trim();
                    return text === target;
                }});

                if (!el) {{
                    const all = Array.from(document.querySelectorAll('span, div, td'));
                    el = all.find(e => {{
                        const directText = Array.from(e.childNodes)
                            .filter(n => n.nodeType === Node.TEXT_NODE)
                            .map(n => n.textContent.trim())
                            .join('').trim();
                        const rect = e.getBoundingClientRect();
                        return directText === target && rect.width > 0 && rect.height > 0;
                    }});
                }}

                if (el) {{
                    el.click();
                    return 'ok:' + (el.innerText || el.textContent || '').trim();
                }}

                const visible = Array.from(document.querySelectorAll('li, span'))
                    .filter(e => {{
                        const rect = e.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0 && (e.innerText || '').trim().length > 0;
                    }})
                    .slice(0, 20)
                    .map(e => JSON.stringify((e.innerText || '').trim()));
                return 'not_found. Visible: ' + visible.join(', ');
            }}
        """)
    except Exception as e:
        take_screenshot(page, "category_js_error")
        raise Exception(f"Error al ejecutar JS para seleccionar categoría '{categoria_nombre}': {e}")

    if isinstance(clicked, str) and clicked.startswith("ok:"):
        log("info", f"Categoría '{categoria_nombre}' seleccionada correctamente")
        # take_screenshot(page, "category_selected")
        return

    log("info", f"[DEBUG] select_category result: {clicked}")
    # take_screenshot(page, "select_category_failed")
    raise Exception(
        f"No se pudo seleccionar la categoría '{categoria_nombre}'. "
        f"Elementos visibles en pantalla: {clicked}"
    )


def fill_additional_info(page):
    try:
        page.locator("iframe[name=\"pawContentFrame\"]").content_frame \
            .locator("iframe[name=\"rightFrame\"]").content_frame \
            .get_by_text("INFORMACIÓN ADICIONAL").click()
        log("info", "Pestaña 'INFORMACIÓN ADICIONAL' abierta")
    except PlaywrightTimeoutError as e:
        take_screenshot(page, "additional_info_tab_timeout")
        raise Exception(f"Timeout al abrir la pestaña 'INFORMACIÓN ADICIONAL': {e}")
    except Exception as e:
        take_screenshot(page, "additional_info_tab_error")
        raise Exception(f"Error al abrir la pestaña 'INFORMACIÓN ADICIONAL': {e}")

    # Empresa
    try:
        emp_span = page.locator("iframe[name=\"pawContentFrame\"]").content_frame \
            .locator("iframe[name=\"rightFrame\"]").content_frame \
            .get_by_role("row", name="Atendido por la empresa::").get_by_role("button")
        option = page.locator("iframe[name=\"pawContentFrame\"]").content_frame \
            .locator("iframe[name=\"rightFrame\"]").content_frame \
            .get_by_text("Gconsultores - OP", exact=True)
        select_option(page, emp_span, option)
        log("info", "Campo 'Atendido por la empresa' completado")
    except Exception as e:
        take_screenshot(page, "campo_empresa_error")
        raise Exception(f"Error al seleccionar 'Atendido por la empresa': {e}")

    # Forma de servicio
    try:
        fs_span = page.locator("iframe[name=\"pawContentFrame\"]").content_frame \
            .locator("iframe[name=\"rightFrame\"]").content_frame \
            .get_by_role("button", name="Pulse para seleccionar el").nth(4)
        option = page.locator("iframe[name=\"pawContentFrame\"]").content_frame \
            .locator("iframe[name=\"rightFrame\"]").content_frame \
            .get_by_text("Soporte 5 x")
        select_option(page, fs_span, option)
        log("info", "Campo 'Forma de servicio' completado")
    except Exception as e:
        take_screenshot(page, "campo_forma_servicio_error")
        raise Exception(f"Error al seleccionar 'Forma de servicio': {e}")

    # Medio
    try:
        medio_span = page.locator("iframe[name=\"pawContentFrame\"]").content_frame \
            .locator("iframe[name=\"rightFrame\"]").content_frame \
            .get_by_role("button", name="Pulse para seleccionar el").nth(5)
        option_medio = page.locator("iframe[name=\"pawContentFrame\"]").content_frame \
            .locator("iframe[name=\"rightFrame\"]").content_frame \
            .get_by_text("Portal", exact=True)
        select_option(page, medio_span, option_medio)
        log("info", "Campo 'Medio' completado")
    except Exception as e:
        take_screenshot(page, "campo_medio_error")
        raise Exception(f"Error al seleccionar 'Medio': {e}")

    # CI'S
    try:
        ci_span = page.locator("iframe[name=\"pawContentFrame\"]").content_frame \
            .locator("iframe[name=\"rightFrame\"]").content_frame \
            .get_by_role("table", name="CI´S")
        option_ci = page.locator("iframe[name=\"pawContentFrame\"]").content_frame \
            .locator("iframe[name=\"rightFrame\"]").content_frame \
            .get_by_text("NINGUNO", exact=True)
        select_option(page, ci_span, option_ci)
        log("info", "Campo 'CI´S' completado")
    except Exception as e:
        take_screenshot(page, "campo_cis_error")
        raise Exception(f"Error al seleccionar 'CI´S': {e}")

    # Subtipo
    try:
        subtipo_span = page.locator("iframe[name=\"pawContentFrame\"]").content_frame \
            .locator("iframe[name=\"rightFrame\"]").content_frame \
            .get_by_role("table", name="Aplica para la subcategoria")
        option_subtipo = page.locator("iframe[name=\"pawContentFrame\"]").content_frame \
            .locator("iframe[name=\"rightFrame\"]").content_frame \
            .get_by_text("Operación Continua").nth(1)
        select_option(page, subtipo_span, option_subtipo)
        log("info", "Campo 'Subtipo' completado")
    except Exception as e:
        take_screenshot(page, "campo_subtipo_error")
        raise Exception(f"Error al seleccionar 'Subtipo': {e}")


def select_option(page, span, option):
    try:
        span.wait_for(state="visible", timeout=10000)
        span.click()
    except PlaywrightTimeoutError as e:
        take_screenshot(page, "select_option_span_timeout")
        raise Exception(f"Timeout esperando que el selector sea visible: {e}")
    except Exception as e:
        take_screenshot(page, "select_option_span_error")
        raise Exception(f"Error al hacer click en el selector: {e}")

    try:
        option.wait_for(state="visible", timeout=5000)
        option.click()
        log("info", "Opción seleccionada correctamente")
        # take_screenshot(page, "option_selected")
    except PlaywrightTimeoutError:
        take_screenshot(page, "select_option_option_timeout")
        log("warning", "La opción no apareció en el tiempo esperado, continuando...")


def save_ticket(page):
    right_frame_real = next(
        (f for f in page.frames if f.name == "rightFrame"), None
    )
    if not right_frame_real:
        raise Exception("No se encontró el frame 'rightFrame' al intentar guardar el ticket")

    try:
        save_btn = right_frame_real.locator("#pageSaveBtn img")
        save_btn.wait_for(state="visible", timeout=10000)
        save_btn.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)
        # take_screenshot(page, "after_save")
        log("info", "Ticket guardado correctamente")
    except PlaywrightTimeoutError as e:
        take_screenshot(page, "save_btn_timeout")
        raise Exception(f"Timeout al intentar guardar el ticket: {e}")
    except Exception as e:
        take_screenshot(page, "save_error")
        raise Exception(f"Error al guardar el ticket: {e}")