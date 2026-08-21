from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from app.utils.logger import log
from app.utils.screenshots import take_screenshot
from dotenv import load_dotenv
import os
import re
from datetime import datetime
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import Playwright, expect

from sqlalchemy import create_engine, text

load_dotenv()

BASE_URL = "https://servicedesk.gconsultores.com.mx/proactivanet/servicedesk/default.paw"
LOGIN_URL = "https://servicedesk.gconsultores.com.mx/proactivanet/library/loginform/default.paw"
STATE_FILE = "state.json"
USER = os.getenv("PROACTIVA_USER")
PASS = os.getenv("PROACTIVA_PASSWORD")
ACENTO = "\u00b4"

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

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

def search_and_open_ticket(page, context, incident_code, tipo, categoria, subcategoria):
    try:
        ensure_session(context, page, USER, PASS)
    except Exception as e:
        _registrar_error_automatizacion(incident_code, tipo, categoria, subcategoria, "sesion",
                                         f"Error al establecer sesión: {e}")
        raise Exception(f"Error al establecer sesión antes de buscar ticket '{incident_code}': {e}")

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
        _registrar_error_automatizacion(incident_code, tipo, categoria, subcategoria, "busqueda",
                                         f"Timeout al buscar el ticket en el top frame: {e}")
        raise Exception(f"Timeout al intentar buscar el ticket '{incident_code}' en el top frame: {e}")
    except Exception as e:
        take_screenshot(page, "search_input_error")
        _registrar_error_automatizacion(incident_code, tipo, categoria, subcategoria, "busqueda",
                                         f"Error al buscar el ticket: {e}")
        raise Exception(f"Error al buscar el ticket '{incident_code}': {e}")

    # Esperar resultados
    try:
        content_frame = page.frame_locator("iframe[name='pawContentFrame']")
        right_frame = content_frame.frame_locator("iframe[name='rightFrame']")
        rows = right_frame.locator("#pawTheTb tbody tr[class*='pawPTableTbDtTr']")
        rows.first.wait_for(timeout=10000)
    except PlaywrightTimeoutError as e:
        take_screenshot(page, "results_timeout")
        _registrar_error_automatizacion(incident_code, tipo, categoria, subcategoria, "busqueda_resultados",
                                         f"Timeout esperando resultados de búsqueda: {e}")
        raise Exception(f"Timeout esperando resultados de búsqueda para '{incident_code}': {e}")
    except Exception as e:
        take_screenshot(page, "results_error")
        _registrar_error_automatizacion(incident_code, tipo, categoria, subcategoria, "busqueda_resultados",
                                         f"Error al cargar resultados de búsqueda: {e}")
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
        _registrar_error_automatizacion(incident_code, tipo, categoria, subcategoria, "abrir_ticket",
                                         f"Error al abrir el ticket: {e}")
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
        log("info", "Modo edición activado")
    except PlaywrightTimeoutError as e:
        take_screenshot(page, "edit_button_timeout")
        _registrar_error_automatizacion(incident_code, tipo, categoria, subcategoria, "modo_edicion",
                                         f"Timeout al activar modo edición: {e}")
        raise Exception(f"Timeout al activar modo edición del ticket '{incident_code}': {e}")
    except Exception as e:
        take_screenshot(page, "edit_button_error")
        _registrar_error_automatizacion(incident_code, tipo, categoria, subcategoria, "modo_edicion",
                                         f"Error al activar modo edición: {e}")
        raise Exception(f"Error al activar modo edición del ticket '{incident_code}': {e}")

    # Ejecutar pasos de edición

    try:
        select_ticket_type(page, tipo)
    except Exception as e:
        _registrar_error_automatizacion(incident_code, tipo, categoria, subcategoria, "tipo",
                                         f"Error al seleccionar tipo de ticket: {e}")
        raise Exception(f"Error al seleccionar tipo de ticket '{tipo}': {e}")

    try:
        select_category_and_subcategory(page, categoria, subcategoria)
    except Exception as e:
        _registrar_error_automatizacion(incident_code, tipo, categoria, subcategoria, "categoria",
                                         f"Error al seleccionar categoría '{categoria}/{subcategoria}': {e}")
        raise Exception(f"Error al seleccionar categoría '{categoria}/{subcategoria}': {e}")

    try:
        fill_additional_info(page)
    except Exception as e:
        _registrar_error_automatizacion(incident_code, tipo, categoria, subcategoria, "informacion_adicional",
                                         f"Error al llenar información adicional: {e}")
        raise Exception(f"Error al llenar información adicional: {e}")

    try:
        save_ticket(page, incident_code, tipo, categoria, subcategoria)
    except Exception as e:
        raise Exception(f"Error al guardar el ticket '{incident_code}': {e}")

def select_client(page, cliente_nombre: str):

    right_frame_content = (
        page.locator("iframe[name='pawContentFrame']").content_frame
        .locator("iframe[name='rightFrame']").content_frame
    )

    client_table = right_frame_content.locator("table#padCustomers_id")

    # Abrir buscador

    client_table.wait_for(state="visible")

    btn = client_table.get_by_role(
        "button",
        name="Pulse para buscar el valor"
    )

    log("info", f"Botones encontrados: {btn.count()}")

    btn.first.click()

    page.wait_for_timeout(2000)

    # Buscar theIFrame

    search_frame = None

    for frame in page.frames:
        if frame.name == "theIFrame":
            search_frame = frame
            break

    if search_frame is None:
        raise Exception("No existe ningún frame llamado 'theIFrame'")

    log("info", "Frame encontrado")

    # Buscar campo

    locator = search_frame.locator("#pawDlgSearchStr")


    if locator.count() == 0:

        log("warning", "===== HTML DEL FRAME =====")
        log("warning", search_frame.locator("body").inner_html())

        raise Exception(
            "No existe #pawDlgSearchStr dentro de theIFrame"
        )

    locator.fill(cliente_nombre)

    log("info", "Texto escrito")

    aceptar = search_frame.get_by_role(
        "button",
        name="Aceptar"
    )

    log("info", f"Botones Aceptar: {aceptar.count()}")

    aceptar.click()

    page.wait_for_timeout(1500)

    # Buscar resultados

    log("info", "===== RESULTADOS =====")

    resultados = right_frame_content.get_by_text(cliente_nombre)

    log("info", f"Coincidencias: {resultados.count()}")

    if resultados.count() > 0:
        resultados.last.click()
        log("info", "Cliente seleccionado")
    else:
        log("warning", "No apareció el resultado")

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

def select_category_and_subcategory(page, categoria_principal: str, subcategoria: str):

    right_frame_content = (
        page.locator("iframe[name='pawContentFrame']").content_frame
        .locator("iframe[name='rightFrame']").content_frame
    )

    category_table = right_frame_content.locator("table#padCategories_id")
    category_table.wait_for(state="visible", timeout=10000)

    target_full = f"/{categoria_principal}/{subcategoria}"

    log("info", f"Buscando categoría: {categoria_principal}")
    log("info", f"Ruta objetivo: {target_full}")

    # Abrir el buscador, llenar y aceptar

    search_btn = category_table.get_by_role("button", name="Pulse para buscar el valor")
    if search_btn.count() == 0:
        raise Exception("No se encontró el botón de búsqueda de categoría.")
    search_btn.first.click()
    page.wait_for_timeout(800)

    search_frame = next((f for f in page.frames if f.name == "theIFrame"), None)
    if search_frame is None:
        raise Exception("No apareció el frame del buscador.")

    search_input = search_frame.locator("#pawDlgSearchStr")
    search_input.wait_for(state="visible", timeout=10000)
    search_input.fill(categoria_principal)

    search_frame.get_by_role("button", name="Aceptar").click()
    right_frame_content.locator(".ui-dialog").wait_for(state="hidden", timeout=10000)
    page.wait_for_timeout(800)

    # Seleccionar directamente el resultado con la ruta completa
    # El atributo 'title' SIEMPRE trae el texto completo sin truncar

    title_el = right_frame_content.get_by_title(target_full, exact=True)

    if title_el.count() > 0:
        title_el.first.click()
        log("info", f"Categoría/subcategoría seleccionada por title: {target_full}")
        return

    # Respaldo: JS tolerante a truncamiento en innerText, por si el elemento no expone 'title'.
    right_frame_real = next((f for f in page.frames if f.name == "rightFrame"), None)
    if not right_frame_real:
        raise Exception("No se encontró el frame real 'rightFrame' para buscar la categoría")

    clicked = right_frame_real.evaluate(f"""
        () => {{
            const targetFull = {repr(target_full)};
            const candidates = Array.from(document.querySelectorAll('span, div, td, a, li'));
            const matches = candidates.filter(e => {{
                const titleAttr = (e.getAttribute && e.getAttribute('title')) || '';
                if (titleAttr.trim() === targetFull) return true;
                const text = (e.innerText || e.textContent || '').trim();
                if (!text.startsWith('/')) return false;
                if (text === targetFull) return true;
                if (text.endsWith('...')) {{
                    const stripped = text.slice(0, -3);
                    return targetFull.startsWith(stripped);
                }}
                return false;
            }});
            if (matches.length === 0) return null;
            matches.sort((a, b) =>
                (b.innerText || b.textContent || '').length -
                (a.innerText || a.textContent || '').length
            );
            const el = matches[0];
            el.click();
            return (el.innerText || el.textContent || '').trim();
        }}
    """)

    if not clicked:
        log("warning", "===== TEXTO DEL FORMULARIO (body de rightFrame) =====")
        log("warning", right_frame_content.locator("body").inner_text())

        raise Exception(
            f"No se pudo seleccionar la ruta '{target_full}'."
        )

    log("info", f"✔ Categoría/subcategoría seleccionada (respaldo JS): {clicked}")

def fill_additional_info(page):
    try:
        page.locator("iframe[name=\"pawContentFrame\"]").content_frame \
            .locator("iframe[name=\"rightFrame\"]").content_frame \
            .locator("span.pawFormPageTabStripIndexTabLabel", has_text="INFORMACIÓN ADICIONAL") \
            .click()
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

    # Forma de servicio — localizado por fila
    try:
        fs_span = page.locator("iframe[name=\"pawContentFrame\"]").content_frame \
            .locator("iframe[name=\"rightFrame\"]").content_frame \
            .get_by_role("row").filter(has_text="Forma de servicio") \
            .get_by_role("button")
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
            .get_by_role("row").filter(has_text="Medio:") \
            .get_by_role("button")
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
    except PlaywrightTimeoutError:
        take_screenshot(page, "select_option_option_timeout")
        log("warning", "La opción no apareció en el tiempo esperado, continuando...")
        return

    try:
        popup = page.locator("iframe[name=\"pawContentFrame\"]").content_frame \
            .locator("iframe[name=\"rightFrame\"]").content_frame \
            .locator(".pawDFSelPopup")
        popup.first.wait_for(state="hidden", timeout=5000)
    except PlaywrightTimeoutError:
        log("warning", "El popup de selección no se cerró solo; forzando cierre con Escape")
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)

# Validación del guardado

def _verificar_modo_lectura(right_frame_real, timeout=10000):
    """
    Un guardado exitoso regresa el formulario a modo lectura, lo cual
    se confirma con la reaparición de #pageEditBtn.
    """
    try:
        right_frame_real.locator("#pageEditBtn").wait_for(state="visible", timeout=timeout)
        return True
    except PlaywrightTimeoutError:
        return False


def _registrar_error_automatizacion(incident_code, tipo, categoria, subcategoria, paso, mensaje_error):
    # insertar en la base de datos los errores tanto de time out o de seleccion etc
    query = text("""
        INSERT INTO tickets_guardado_fallido
            (incidente_codigo, tipo, categoria, subcategoria,
             paso, mensaje_error, fecha_deteccion, notificado)
        VALUES (:incidente_codigo, :tipo, :categoria, :subcategoria,
                :paso, :mensaje_error, :fecha_deteccion, :notificado)
    """)
    try:
        with engine.connect() as conn:
            conn.execute(query, {
                "incidente_codigo": incident_code,
                "tipo": tipo,
                "categoria": categoria,
                "subcategoria": subcategoria,
                "paso": paso,
                "mensaje_error": mensaje_error,
                "fecha_deteccion": datetime.now(),
                "notificado": False,
            })
            conn.commit()
        log("info", "Error de automatización registrado en base de datos",
            incident_code=incident_code, paso=paso)
    except Exception as db_error:
        # No se re-lanza: si la BD también falla, al menos queda el log y el screenshot.
        log("error", "No se pudo registrar el error de automatización en base de datos",
            incident_code=incident_code, paso=paso, db_error=str(db_error))


def save_ticket(page, incident_code=None, tipo=None, categoria=None, subcategoria=None):
    right_frame_real = next(
        (f for f in page.frames if f.name == "rightFrame"), None
    )
    if not right_frame_real:
        raise Exception("No se encontró el frame 'rightFrame' al intentar guardar el ticket")

    # Proactivanet reporta errores de validación mediante un windows alert
    dialog_info = {"appeared": False, "message": None}

    def handle_dialog(dialog):
        dialog_info["appeared"] = True
        dialog_info["message"] = dialog.message
        log("warning", "Diálogo de error detectado al guardar ticket", mensaje=dialog.message)
        dialog.accept()

    page.on("dialog", handle_dialog)

    try:
        save_btn = right_frame_real.locator("#pageSaveBtn img")
        save_btn.wait_for(state="visible", timeout=10000)
        save_btn.click()
        # Margen para que, de aparecer, el diálogo nativo dispare el evento
        # y el handler lo cierre antes de continuar.
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)
    except PlaywrightTimeoutError as e:
        take_screenshot(page, "save_btn_timeout")
        page.remove_listener("dialog", handle_dialog)
        _registrar_error_automatizacion(incident_code, tipo, categoria, subcategoria, "guardado",
                                         f"Timeout al intentar guardar: {e}")
        raise Exception(f"Timeout al intentar guardar el ticket: {e}")
    except Exception as e:
        take_screenshot(page, "save_error")
        page.remove_listener("dialog", handle_dialog)
        _registrar_error_automatizacion(incident_code, tipo, categoria, subcategoria, "guardado",
                                         f"Error inesperado al guardar: {e}")
        raise Exception(f"Error al guardar el ticket: {e}")

    page.remove_listener("dialog", handle_dialog)

    # Caso 1: Proactivanet mostró un alert de validación (campos vacíos, etc.)
    if dialog_info["appeared"]:
        take_screenshot(page, "save_validation_error")
        _registrar_error_automatizacion(incident_code, tipo, categoria, subcategoria, "guardado",
                                         dialog_info["message"])
        raise Exception(
            f"El ticket '{incident_code}' no se guardó — Proactivanet reportó: {dialog_info['message']}"
        )

    # Caso 2: no hubo alert, pero tampoco se confirma el regreso a modo lectura
    if not _verificar_modo_lectura(right_frame_real):
        take_screenshot(page, "save_unconfirmed")
        _registrar_error_automatizacion(
            incident_code, tipo, categoria, subcategoria, "guardado",
            "No se pudo confirmar el guardado: no reapareció el botón de edición (#pageEditBtn) tras guardar",
        )
        raise Exception(
            f"No se pudo confirmar que el ticket '{incident_code}' se guardó correctamente"
        )

    # Caso 3: guardado confirmado
    log("info", "Ticket guardado y verificado correctamente", incident_code=incident_code)