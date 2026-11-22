import pytest
from conftest import PO_URL


def estado_del_pedido(api, pedido):
    r = api.get(f"{PO_URL}/{pedido['name']}")
    r.raise_for_status()
    return r.json()["data"]


def test_recepcion_parcial_deja_el_pedido_abierto(api, docs):
    pedido = docs.pedido(cantidad=10)

    r = docs.recibir(pedido, 5)

    assert r.status_code == 200, r.text
    actual = estado_del_pedido(api, pedido)
    assert actual["per_received"] == 50
    assert actual["status"] == "To Receive and Bill"


def test_segunda_recepcion_completa_el_pedido(api, docs):
    pedido = docs.pedido(cantidad=10)
    assert docs.recibir(pedido, 5).status_code == 200

    r = docs.recibir(pedido, 5)

    assert r.status_code == 200, r.text
    actual = estado_del_pedido(api, pedido)
    assert actual["per_received"] == 100
    assert actual["status"] == "To Bill"


# Un solo dato cambia entre casos: la cantidad recibida de un pedido de 10.
CANTIDADES = [
    pytest.param(10, True, id="cantidad-exacta"),
    pytest.param(11, False, id="una-unidad-de-mas"),
    pytest.param(15, False, id="cinco-unidades-de-mas"),
]


@pytest.mark.parametrize("recibida, aceptada", CANTIDADES)
def test_recepcion_no_supera_lo_pedido(docs, recibida, aceptada):
    pedido = docs.pedido(cantidad=10)

    r = docs.recibir(pedido, recibida)

    if aceptada:
        assert r.status_code == 200, r.text
    else:
        assert r.status_code == 417, f"{r.status_code}: {r.text}"
        assert "over limit" in r.text, r.text
