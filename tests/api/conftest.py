import os
from datetime import date, timedelta

import pytest
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ["ERP_URL"]
RECURSO = f"{BASE_URL}/api/resource"
METODO = f"{BASE_URL}/api/method"
PO_URL = f"{RECURSO}/Purchase Order"


def orden_base(cantidad=1, precio=100):
    """Orden de compra válida. Los casos negativos cambian solo un argumento."""
    entrega = (date.today() + timedelta(days=7)).isoformat()
    return {
        "supplier": "Proveedor Demo Ltda",
        "company": "Compras QA SpA",
        "schedule_date": entrega,
        "items": [
            {
                "item_code": "TORN-M8",
                "qty": cantidad,
                "rate": precio,
                "warehouse": "Stores - CQS",
                "schedule_date": entrega,
            }
        ],
    }


@pytest.fixture
def api():
    with requests.Session() as sesion:
        sesion.headers.update({
            "Authorization": f"token {os.environ['ERP_KEY']}:{os.environ['ERP_SECRET']}",
            "Accept": "application/json",
        })
        yield sesion


@pytest.fixture
def orden(api):
    # Preparación: crea una orden válida
    r = api.post(PO_URL, json=orden_base())
    r.raise_for_status()
    datos = r.json()["data"]
    yield datos
    # Limpieza: corre aunque la prueba falle
    api.delete(f"{PO_URL}/{datos['name']}")

class Documentos:
    """Crea documentos del ERP durante un test y los deja limpios al terminar.

    Un documento presentado (submitted) con asientos de stock o contables no se
    puede borrar en ERPNext: la limpieza correcta es cancelarlo, y eso agrega
    un asiento de reversión. Un borrador sí se borra.
    """

    def __init__(self, api):
        self.api = api
        self.creados = []  # (doctype, name), en orden de creación

    def guardar(self, doc):
        r = self.api.post(f"{METODO}/frappe.client.insert", json={"doc": doc})
        r.raise_for_status()
        datos = r.json()["message"]
        self.creados.append((datos["doctype"], datos["name"]))
        return datos

    def presentar(self, datos):
        """Devuelve la respuesta tal cual, para poder comprobar rechazos."""
        return self.api.post(f"{METODO}/frappe.client.submit", json={"doc": datos})

    def pedido(self, cantidad=10, precio=100):
        orden = orden_base(cantidad=cantidad, precio=precio)
        orden["doctype"] = "Purchase Order"
        r = self.presentar(self.guardar(orden))
        r.raise_for_status()
        return r.json()["message"]

    def borrador_desde(self, ruta, origen, cantidad=None):
        """Pide al ERP el borrador de un documento a partir de otro (pedido o recepción)."""
        r = self.api.get(f"{METODO}/{ruta}", params={"source_name": origen["name"]})
        r.raise_for_status()
        doc = {k: v for k, v in r.json()["message"].items()
               if k not in ("name", "__islocal", "__onload", "__unsaved")}
        doc["items"] = [{k: v for k, v in it.items()
                         if k not in ("name", "__islocal", "__unsaved")}
                        for it in doc["items"]]
        if cantidad is not None:
            doc["items"][0]["qty"] = cantidad
        return doc

    def recibir(self, pedido, cantidad):
        ruta = "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt"
        borrador = self.borrador_desde(ruta, pedido, cantidad)
        return self.presentar(self.guardar(borrador))

    def facturar(self, pedido, cantidad=None):
        """Factura directa desde el pedido, sin pasar por la recepción."""
        ruta = "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_invoice"
        borrador = self.borrador_desde(ruta, pedido, cantidad)
        return self.presentar(self.guardar(borrador))

    def facturar_recepcion(self, recepcion, cantidad=None):
        """Factura generada desde una recepción."""
        ruta = "erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_purchase_invoice"
        borrador = self.borrador_desde(ruta, recepcion, cantidad)
        return self.presentar(self.guardar(borrador))

    def limpiar(self):
        problemas = []
        for doctype, nombre in reversed(self.creados):
            r = self.api.get(f"{RECURSO}/{doctype}/{nombre}")
            if not r.ok:
                continue
            estado = r.json()["data"]["docstatus"]
            if estado == 1:
                c = self.api.post(f"{METODO}/frappe.client.cancel",
                                  json={"doctype": doctype, "name": nombre})
                if not c.ok:
                    problemas.append(f"no pude cancelar {doctype} {nombre}: {c.text[:200]}")
            elif estado == 0:
                self.api.delete(f"{RECURSO}/{doctype}/{nombre}")
        assert not problemas, "; ".join(problemas)


@pytest.fixture
def docs(api):
    d = Documentos(api)
    yield d
    d.limpiar()
