"""Prepara un ERPNext recién creado: empresa, proveedor, ítems y llaves de API.

El pipeline copia este archivo dentro del contenedor y lo ejecuta con:
    bench --site frontend execute frappe.seed_qa.run
Es idempotente: si algo ya existe, no lo vuelve a crear.
"""
from datetime import date

import frappe
from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

EMPRESA = "Compras QA SpA"
ABREVIATURA = "CQS"
PROVEEDOR = "Proveedor Demo Ltda"
ITEMS = ["TORN-M8", "TUER-M8"]
SALIDA = "/tmp/seed_qa.env"


def crear_empresa():
    if frappe.get_all("Company"):
        print("La empresa ya existe")
        return
    hoy = date.today()
    setup_complete({
        "language": "english",
        "country": "Chile",
        "currency": "CLP",
        "timezone": "America/Santiago",
        "full_name": "Admin QA",
        "email": "admin-qa@example.com",
        "password": "QA-Admin-2026!",
        "company_name": EMPRESA,
        "company_abbr": ABREVIATURA,
        "company_tagline": "QA",
        "fy_start_date": f"{hoy.year}-01-01",
        "fy_end_date": f"{hoy.year}-12-31",
        "chart_of_accounts": "Standard",
        "domains": ["Distribution"],
    })
    frappe.db.commit()
    print("Asistente de configuración completado")


def primer_grupo(doctype):
    return frappe.db.get_value(doctype, {"is_group": 0}, "name")


def crear(doctype, filtros, datos):
    if frappe.db.exists(doctype, filtros):
        print(f"{doctype} ya existe")
        return
    frappe.get_doc({"doctype": doctype, **datos}).insert(ignore_permissions=True)
    print(f"{doctype} creado")


def crear_llaves():
    from frappe.core.doctype.user.user import generate_keys

    secreto = generate_keys("Administrator")["api_secret"]
    frappe.db.commit()
    clave = frappe.db.get_value("User", "Administrator", "api_key")
    with open(SALIDA, "w") as archivo:
        archivo.write(f"ERP_KEY={clave}\nERP_SECRET={secreto}\n")
    print("Llaves de API generadas")


def run():
    frappe.set_user("Administrator")
    crear_empresa()
    crear("Supplier", {"supplier_name": PROVEEDOR}, {
        "supplier_name": PROVEEDOR,
        "supplier_group": primer_grupo("Supplier Group"),
    })
    for codigo in ITEMS:
        crear("Item", {"item_code": codigo}, {
            "item_code": codigo,
            "item_name": codigo,
            "item_group": primer_grupo("Item Group"),
            "stock_uom": "Nos",
            "is_stock_item": 1,
        })
    frappe.db.commit()
    crear_llaves()
