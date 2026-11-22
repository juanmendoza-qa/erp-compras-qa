"""Contratos (JSON Schema) de las respuestas clave del ERP.

Cada esquema fija lo que el resto del sistema necesita de la respuesta: qué campos
trae y de qué tipo. No prohíbe campos extra, porque ERPNext agrega muchos y puede
sumar más en una actualización; lo que rompe a quien consume la API es que falte
un campo o cambie de tipo.
"""
from jsonschema import Draft202012Validator

LINEA_PEDIDO = {
    "type": "object",
    "required": ["item_code", "qty", "rate", "amount"],
    "properties": {
        "item_code": {"type": "string"},
        "qty": {"type": "number"},
        "rate": {"type": "number"},
        "amount": {"type": "number"},
    },
}

PEDIDO = {
    "type": "object",
    "required": ["name", "supplier", "company", "docstatus", "status", "grand_total", "items"],
    "properties": {
        "name": {"type": "string", "pattern": r"^PUR-ORD-\d{4}-\d{5}$"},
        "supplier": {"type": "string"},
        "company": {"type": "string"},
        "docstatus": {"type": "integer", "enum": [0, 1, 2]},
        "status": {"type": "string"},
        "grand_total": {"type": "number"},
        "items": {"type": "array", "minItems": 1, "items": LINEA_PEDIDO},
    },
}

RECEPCION = {
    "type": "object",
    "required": ["name", "supplier", "docstatus", "items"],
    "properties": {
        "name": {"type": "string", "pattern": r"^MAT-PRE-\d{4}-\d{5}$"},
        "supplier": {"type": "string"},
        "docstatus": {"type": "integer", "const": 1},
        "items": {"type": "array", "minItems": 1, "items": {
            "type": "object",
            "required": ["item_code", "qty"],
            "properties": {"item_code": {"type": "string"}, "qty": {"type": "number"}},
        }},
    },
}

# Respuesta con el pedido dentro de "data" (API de recursos: crear, leer).
RESPUESTA_PEDIDO = {
    "type": "object", "required": ["data"], "properties": {"data": PEDIDO},
}

LISTADO_PEDIDOS = {
    "type": "object",
    "required": ["data"],
    "properties": {"data": {"type": "array", "items": {
        "type": "object", "required": ["name"], "properties": {"name": {"type": "string"}},
    }}},
}

# Respuesta con el documento dentro de "message" (métodos como submit).
RESPUESTA_RECEPCION = {
    "type": "object", "required": ["message"], "properties": {"message": RECEPCION},
}

ERROR_DE_VALIDACION = {
    "type": "object",
    "required": ["exception", "exc_type", "_server_messages"],
    "properties": {
        "exception": {"type": "string"},
        "exc_type": {"type": "string"},
        "_server_messages": {"type": "string"},
    },
}


def validar(instancia, esquema):
    """Falla con TODAS las diferencias, no solo con la primera."""
    errores = sorted(Draft202012Validator(esquema).iter_errors(instancia),
                     key=lambda e: list(e.absolute_path))
    detalle = [f"{'/'.join(map(str, e.absolute_path)) or '(raíz)'}: {e.message}" for e in errores]
    assert not detalle, "El contrato no se cumple:\n" + "\n".join(detalle)
