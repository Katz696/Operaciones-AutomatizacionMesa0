# ── Campos fijos (UUIDs reales de tu instancia) ───────────────────────────────
FIXED_FIELDS: dict = {
    "FederatedCode": None,
    "PanUsers_idSource": "c74ab835-d02f-46c7-ac8a-2fcff1ea8b10",
    "PanLocations_id": None,
    "PawSvcAuthUsers_idCreator": "b95d5c71-25a7-418a-a3fe-23a69b7876c0",
    "PadSources_id": "ddcd3ae0-8fe7-4f2f-9bda-32d8fb99450f",
    "PadStatus_id": "42a6fbb5-5743-4f11-b822-a5e9b88e52c7",
    "PadTypes_id": None,
    "PadPortfolio_id": None,
    "PadPriorities_id": None,
    "PadUrgencies_id": None,
    "PadImpacts_id": None,
    "SendUserNotification": True,
}

# UUID único de categoría para todos los tickets
CATEGORY_ID = "797849a4-e7c3-4094-b7d8-a7df7390f0c2"

CATEGORIES: dict = {
    "incidente_red":            {"key": "incidente_red",            "domain": "red",          "PadCategories_id": CATEGORY_ID},
    "incidente_hardware":       {"key": "incidente_hardware",       "domain": "hardware",      "PadCategories_id": CATEGORY_ID},
    "incidente_software":       {"key": "incidente_software",       "domain": "software",      "PadCategories_id": CATEGORY_ID},
    "requerimiento_acceso":     {"key": "requerimiento_acceso",     "domain": "acceso",        "PadCategories_id": CATEGORY_ID},
    "requerimiento_instalacion":{"key": "requerimiento_instalacion","domain": "instalacion",   "PadCategories_id": CATEGORY_ID},
}