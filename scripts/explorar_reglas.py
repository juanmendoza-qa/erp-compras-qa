"""Exploración de reglas de negocio del ERP (no es un test).

Prueba, contra tu ERP local, cinco situaciones y muestra qué responde:
  1. Recibir MENOS de lo pedido            (recepción parcial)
  2. Recibir MÁS de lo pedido              (sobrerrecepción)
  3. Facturar un pedido SIN recepción      (factura sin recepción)
  4. Sacar más stock del que hay           (stock negativo)
  5. Sacar una cantidad que sí hay         (control: debe funcionar)

Cada escenario limpia lo que creó (cancela y borra), igual que los tests.
Uso:  python scripts/explorar_reglas.py
"""
import json
import os
import re
import sys
from datetime import date, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()
BASE = os.environ["ERP_URL"]
RECURSO = f"{BASE}/api/resource"
METODO = f"{BASE}/api/method"
EMPRESA = "Compras QA SpA"
BODEGA = "Stores - CQS"
ARTICULO = "TORN-M8"

s = requests.Session()
s.headers.update({
    "Authorization": f"token {os.environ['ERP_KEY']}:{os.environ['ERP_SECRET']}",
    "Accept": "application/json",
})

creados = []  # (doctype, name) de lo que hay que limpiar, en orden de creación


def mensaje(r):
    """Resume la respuesta: 'ok' o el motivo del rechazo, sin etiquetas HTML."""
    if r.ok:
        return "ok"
    try:
        d = r.json()
    except ValueError:
        return r.text[:200]
    if "_server_messages" in d:
        partes = []
        for m in json.loads(d["_server_messages"]):
            partes.append(re.sub(r"<[^>]+>", "", json.loads(m).get("message", "")))
        return " | ".join(partes)[:300]
    return str(d.get("exc_type") or d.get("exception") or d)[:300]


def mostrar(etiqueta, r):
    print(f"    {etiqueta}: HTTP {r.status_code} -> {mensaje(r)}")
    return r.ok


def limpio(doc):
    """Quita campos internos que trae un documento generado por el ERP."""
    doc = {k: v for k, v in doc.items() if k not in ("name", "__islocal", "__onload", "__unsaved")}
    doc["items"] = [
        {k: v for k, v in it.items() if k not in ("name", "__islocal", "__unsaved")}
        for it in doc.get("items", [])
    ]
    return doc


def insertar_y_validar(doc, etiqueta):
    """Inserta (borrador) y luego presenta (submit). Devuelve el doc presentado o None."""
    r = s.post(f"{METODO}/frappe.client.insert", json={"doc": doc})
    if not mostrar(f"{etiqueta} / guardar", r):
        return None
    datos = r.json()["message"]
    creados.append((datos["doctype"], datos["name"]))
    r = s.post(f"{METODO}/frappe.client.submit", json={"doc": datos})
    if not mostrar(f"{etiqueta} / presentar", r):
        return None
    return r.json()["message"]


def crear_orden(cantidad=10, precio=100):
    entrega = (date.today() + timedelta(days=7)).isoformat()
    doc = {
        "doctype": "Purchase Order",
        "supplier": "Proveedor Demo Ltda",
        "company": EMPRESA,
        "schedule_date": entrega,
        "items": [{"item_code": ARTICULO, "qty": cantidad, "rate": precio,
                   "warehouse": BODEGA, "schedule_date": entrega}],
    }
    return insertar_y_validar(doc, f"Pedido de {cantidad}")


def generar(metodo, pedido, cantidad=None):
    """Pide al ERP el borrador de recepción o factura a partir del pedido."""
    r = s.get(f"{METODO}/erpnext.buying.doctype.purchase_order.purchase_order.{metodo}",
              params={"source_name": pedido["name"]})
    if not r.ok:
        mostrar(f"generar desde pedido ({metodo})", r)
        return None
    doc = limpio(r.json()["message"])
    if cantidad is not None:
        doc["items"][0]["qty"] = cantidad
    return doc


def limpiar():
    """Cancela y borra, de lo último a lo primero, todo lo que se creó."""
    while creados:
        doctype, nombre = creados.pop()
        s.post(f"{METODO}/frappe.client.cancel", json={"doctype": doctype, "name": nombre})
        r = s.delete(f"{RECURSO}/{doctype}/{nombre}")
        if not r.ok:
            print(f"    !! no pude borrar {doctype} {nombre}: {mensaje(r)}")


def recepcion(cantidad_pedida, cantidad_recibida):
    pedido = crear_orden(cantidad_pedida)
    if pedido:
        borrador = generar("make_purchase_receipt", pedido, cantidad_recibida)
        if borrador:
            insertar_y_validar(borrador, f"Recepción de {cantidad_recibida}")


def factura_sin_recepcion():
    pedido = crear_orden(10)
    if pedido:
        borrador = generar("make_purchase_invoice", pedido)
        if borrador:
            insertar_y_validar(borrador, "Factura sin recepción")


def salida_de_stock(cantidad):
    doc = {
        "doctype": "Stock Entry",
        "stock_entry_type": "Material Issue",
        "company": EMPRESA,
        "items": [{"item_code": ARTICULO, "qty": cantidad, "s_warehouse": BODEGA}],
    }
    insertar_y_validar(doc, f"Salida de {cantidad}")


ESCENARIOS = [
    ("1. Recibir 5 de un pedido de 10 (parcial)", lambda: recepcion(10, 5)),
    ("2. Recibir 15 de un pedido de 10 (sobrerrecepción)", lambda: recepcion(10, 15)),
    ("3. Facturar un pedido sin recepción", factura_sin_recepcion),
    ("4. Sacar 1.000.000 unidades de stock (negativo)", lambda: salida_de_stock(1_000_000)),
    ("5. Sacar 1 unidad sin stock previo (control)", lambda: salida_de_stock(1)),
]

if __name__ == "__main__":
    for titulo, escenario in ESCENARIOS:
        print(titulo)
        try:
            escenario()
        finally:
            limpiar()
    print("Listo. Lo presentado quedó cancelado (no se puede borrar); los borradores se borraron.")
    sys.exit(0)
