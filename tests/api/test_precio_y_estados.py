import pytest
import requests
from conftest import METODO, PO_URL, orden_base


# C04. Pedido de 10 a $100. Cambia solo el precio de la factura.
PRECIOS = [
    pytest.param(100, True, id="mismo-precio-del-pedido"),
    pytest.param(101, False, id="un-peso-mas-caro"),
]


@pytest.mark.parametrize("precio, aceptada", PRECIOS)
def test_factura_respeta_el_precio_del_pedido(docs, precio, aceptada):
    pedido = docs.pedido(cantidad=10, precio=100)

    r = docs.facturar(pedido, precio=precio)

    if aceptada:
        assert r.status_code == 200, r.text
    else:
        assert r.status_code == 417, f"{r.status_code}: {r.text[:300]}"


# C07. Estados del pedido.
def test_pedido_en_borrador_no_se_puede_recibir(docs):
    borrador = docs.guardar({**orden_base(cantidad=10), "doctype": "Purchase Order"})

    try:
        r = docs.recibir(borrador, 5)
    except requests.HTTPError:
        return  # el ERP lo rechazó al generar la recepción
    assert r.status_code == 417, f"{r.status_code}: {r.text[:300]}"


def test_pedido_confirmado_no_admite_cambiar_cantidades(api, docs):
    pedido = docs.pedido(cantidad=10)
    linea = pedido["items"][0]["name"]

    r = api.put(f"{PO_URL}/{pedido['name']}", json={"items": [{"name": linea, "qty": 20}]})

    assert r.status_code == 417, f"{r.status_code}: {r.text[:300]}"
    actual = api.get(f"{PO_URL}/{pedido['name']}").json()["data"]
    assert actual["items"][0]["qty"] == 10


# C08. Cancelar una recepción revierte sus efectos.
def test_cancelar_la_recepcion_devuelve_el_stock_y_reabre_el_pedido(api, docs):
    pedido = docs.pedido(cantidad=10)
    antes = docs.stock_disponible()
    recepcion = docs.recibir(pedido, 10).json()["message"]
    assert docs.stock_disponible() == antes + 10

    r = api.post(f"{METODO}/frappe.client.cancel",
                 json={"doctype": "Purchase Receipt", "name": recepcion["name"]})

    assert r.status_code == 200, r.text
    assert docs.stock_disponible() == antes
    actual = api.get(f"{PO_URL}/{pedido['name']}").json()["data"]
    assert actual["per_received"] == 0
    assert actual["status"] == "To Receive and Bill"
