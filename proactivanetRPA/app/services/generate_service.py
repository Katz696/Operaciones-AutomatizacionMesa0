"""
Motor de plantillas para generación de tickets sintéticos.
Dos dominios: requerimiento | incidente
Basado en ejemplos reales de la mesa de servicio.
"""

import random
import uuid
from datetime import datetime
from faker import Faker
from typing import Optional
from app.config_tickets import FIXED_FIELDS, CATEGORIES

fake = Faker("es_ES")


# ─────────────────────────────────────────────────────────────────────────────
#  BANCO DE PLANTILLAS
# ─────────────────────────────────────────────────────────────────────────────

TEMPLATES = {

    "requerimiento": {
        "subjects": [
            "REQUERIMIENTO WEB SIR {sistema} / {accion}",
            "{codigo} / Enkontrol: {empresa} / {accion}",
            "{codigo} / {empresa} / {accion}",
            "SOLICITUD {sistema} / {accion}",
            "REQUERIMIENTO {sistema} - {empresa}",
            "{accion} en {sistema}",
            "{codigo} / {empresa} / Configuración {sistema}",
        ],
        "aperturas": [
            "Buen día,",
            "Buenos días,",
            "Buenas tardes,",
            "Buen día, espero se encuentre bien.",
        ],
        "cuerpos": [
            "Solicito de su apoyo para {detalle}.",
            "Solicito su apoyo para {detalle}, ya que actualmente {problema}.",
            "Por medio del presente solicito {detalle} para {empresa}.",
            "Solicito de su apoyo para que en {sistema} se {detalle}.",
            "Requiero su apoyo con {detalle} dado que {problema}.",
        ],
        "detalles": [
            "activar el ambiente de QA para realizar pruebas ya que no existe para {empresa}",
            "agregar una columna con el tiempo de respuesta en el reporte de {sistema}",
            "agregar y eliminar cuentas en Azure para las empresas ya creadas",
            "configurar los accesos de {count} usuarios en Enkontrol versión 9",
            "habilitar el módulo de {modulo} en el ambiente de producción",
            "actualizar las licencias de Microsoft 365 Apps for Enterprise para {empresa}",
            "crear el ambiente de pruebas para {empresa} en {sistema}",
            "asignar usuarios y grupos de seguridad en {sistema}",
            "revisar y corregir el reporte de {modulo} que no muestra la fecha de reingreso",
            "ampliar el espacio en disco en {count} GB para el servidor de {empresa}",
            "configurar la VPN para acceso remoto del equipo de {empresa}",
            "dar de alta {count} usuarios nuevos en el sistema Enkontrol",
        ],
        "problemas": [
            "no existe dicho ambiente para {empresa}",
            "la configuración actual no permite realizar las pruebas requeridas",
            "el reporte no refleja los cambios realizados el {fecha}",
            "los usuarios no tienen acceso desde el pasado {fecha}",
            "el módulo fue desactivado tras la última actualización",
        ],
        "cierres": [
            "Quedo atento. Saludos.",
            "Quedo al pendiente y agradezco el apoyo. Saludos.",
            "Agradezco el apoyo. Quedo a sus órdenes.",
            "Quedo pendiente. Gracias.",
            "En espera de su respuesta. Saludos.",
        ],
    },

    "incidente": {
        "subjects": [
            "WEB SIRR {empresa} / {problema_corto}",
            "{codigo} / {empresa} / {problema_corto}",
            "Problemas con {sistema}",
            "{sistema} {empresa} - {problema_corto}",
            "{empresa} / {sistema} no disponible",
            "{codigo}-{sufijo} / {empresa} / {sistema} - {problema_corto}",
            "ERROR {sistema} / {empresa}",
        ],
        "aperturas": [
            "Hola, buenos días,",
            "Buen día,",
            "Buenas tardes,",
            "Hola, buenas tardes,",
        ],
        "cuerpos": [
            "Me pueden ayudar de favor, {detalle}.",
            "Solicito su apoyo, {detalle}.",
            "Me pueden apoyar, {detalle}.",
            "Favor de apoyar con lo siguiente: {detalle}.",
            "Reporto el siguiente problema: {detalle}.",
            "Requiero apoyo urgente, {detalle}.",
        ],
        "detalles": [
            "no puedo entrar a {sistema} de {empresa}, se queda congelado y no avanza",
            "no se tiene alcance a los servidores de Azure por la VPN que apunta hacia el sitio",
            "el {sistema} no me deja realizar llamadas, muestra un error en pantalla",
            "la plataforma {sistema} no está disponible para los usuarios de {empresa}",
            "el sistema {sistema} presenta intermitencias desde las {hora} de hoy",
            "no es posible acceder a {sistema}, la pantalla se queda en blanco al iniciar sesión",
            "se cayó el servicio de {sistema} para el cliente {empresa}",
            "el Agent Desktop no conecta con el servidor, impide operar al equipo de {empresa}",
            "los usuarios de {empresa} no pueden autenticarse en {sistema} desde el {fecha}",
            "la VPN de {empresa} no responde, se validaron IPs locales y no hay alcance a Azure",
            "{sistema} genera error al intentar guardar, se adjunta captura de pantalla",
            "el módulo de {modulo} en {sistema} no carga para ningún usuario de {empresa}",
        ],
        "cierres": [
            "Gracias.",
            "Gracias, quedo en espera.",
            "Quedo al pendiente. Gracias.",
            "En espera de su apoyo. Gracias.",
            "",
        ],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
#  DATOS FICTICIOS COHERENTES CON EL CONTEXTO
# ─────────────────────────────────────────────────────────────────────────────

EMPRESAS = [
    "YUCASA", "BE GRAND", "CONAUTO", "GC", "CHANGAN", "AUTOFIN",
    "GRUPO NORTE", "INMOBILIA", "CASAS GEO", "VINTE", "ARQ STUDIO",
    "CONSTRUCTORA ALFA", "DESARROLLOS DEL BAJÍO", "MEGACABLE", "SIGMA",
]

SISTEMAS = [
    "Web SIRR", "Enkontrol", "Agent Desktop", "Portal SIR",
    "Autofinanciamiento", "ERP Corporativo", "CRM", "Portal de Clientes",
    "Sistema de Reportes", "Plataforma QA", "Azure AD", "VPN Corporativa",
]

MODULOS = [
    "autofinanciamiento", "reportes", "facturación", "cobranza",
    "recursos humanos", "inventario", "compras", "contabilidad",
    "nómina", "proyectos",
]

ACCIONES = [
    "Agregar y eliminar cuentas en Azure",
    "Activar ambiente de QA",
    "Configuración de accesos",
    "Alta de usuarios",
    "Actualización de licencias Microsoft 365",
    "Habilitación de módulo",
    "Configuración de VPN",
    "Asignación de grupos de seguridad",
    "Revisión de reporte",
    "Migración de datos",
    "Ampliación de espacio en disco",
    "Creación de ambiente de pruebas",
]

PROBLEMAS_CORTOS = [
    "Plataforma no disponible",
    "No carga el sistema",
    "Error al iniciar sesión",
    "Pantalla congelada",
    "No responde el servidor",
    "Caída de servicio",
    "Error en módulo",
    "Sin acceso a Azure",
    "VPN sin respuesta",
    "Intermitencia en plataforma",
]


def _ctx() -> dict:
    return {
        "empresa":        random.choice(EMPRESAS),
        "sistema":        random.choice(SISTEMAS),
        "modulo":         random.choice(MODULOS),
        "accion":         random.choice(ACCIONES),
        "problema_corto": random.choice(PROBLEMAS_CORTOS),
        "codigo":         str(random.randint(1000, 9999)),
        "sufijo":         str(random.randint(1, 5)),
        "count":          random.randint(1, 20),
        "fecha":          fake.date_this_year().strftime("%d/%m/%Y"),
        "hora":           f"{random.randint(7, 17)}:{random.choice(['00', '15', '30', '45'])}",
    }


def _fill(template: str, ctx: dict) -> str:
    try:
        return template.format(**ctx)
    except KeyError:
        return template


# ─────────────────────────────────────────────────────────────────────────────
#  GENERADORES DE TÍTULO Y DESCRIPCIÓN
# ─────────────────────────────────────────────────────────────────────────────

def _make_title(domain: str) -> str:
    t = TEMPLATES[domain]
    ctx = _ctx()
    title = _fill(random.choice(t["subjects"]), ctx)
    return f"Mesa Cero - {title}"


def _make_description(domain: str) -> str:
    t = TEMPLATES[domain]
    ctx = _ctx()

    apertura = random.choice(t["aperturas"])
    detalle  = _fill(random.choice(t["detalles"]), ctx)
    problema = _fill(random.choice(t["problemas"]), ctx) if "problemas" in t else ""
    cuerpo   = _fill(random.choice(t["cuerpos"]), {**ctx, "detalle": detalle, "problema": problema})
    cierre   = random.choice(t["cierres"])

    parts = [apertura, "", cuerpo]
    if cierre:
        parts += ["", cierre]

    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
#  FUNCIÓN PÚBLICA
# ─────────────────────────────────────────────────────────────────────────────

def _random_creation_date() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def build_tickets(
    count: int,
    category_key: Optional[str] = None,
    seed: Optional[int] = None,
    include_meta: bool = True,
) -> list[dict]:
    tickets = []

    for i in range(count):
        if seed is not None:
            random.seed(seed + i)
            Faker.seed(seed + i)

        if category_key and category_key in CATEGORIES:
            cat = CATEGORIES[category_key]
        else:
            cat = random.choice(list(CATEGORIES.values()))

        # dominio: si la key contiene "requerimiento" → requerimiento, si no → incidente
        domain = "requerimiento" if "requerimiento" in cat["key"] else "incidente"

        ticket: dict = {
            **FIXED_FIELDS,
            "Title":            _make_title(domain),
            "Description":      _make_description(domain),
            "CreationDate":     _random_creation_date(),
            "PadCategories_id": cat["PadCategories_id"],
        }

        if include_meta:
            ticket["_meta"] = {
                "synthetic_id":         str(uuid.uuid4()),
                "category_key":         cat["key"],
                "expected_category_id": cat["PadCategories_id"],
                "domain":               domain,
                "seed":                 seed,
                "generated_at":         datetime.now().isoformat(),
            }

        tickets.append(ticket)

    return tickets