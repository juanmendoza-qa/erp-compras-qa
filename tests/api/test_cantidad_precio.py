import pytest

from conftest import PO_URL, orden_base

CASOS = [
    pytest.param(1, 100, True, id="valido"),
    pytest.param(0, 100, False, id="cantidad-cero"),
    pytest.param(-5, 100, False, id="cantidad-negativa"),
    pytest.param("abc", 100, False, id="cantidad-no-numerica"),
    pytest.param(1, -100, False, id="precio-negativo"),
]


@pytest.mark.parametrize("cantidad, precio, valida", CASOS)
def test_cantidad_y_precio_de_la_orden(api, cantidad, precio, valida):
    r = api.post(PO_URL, json=orden_base(cantidad=cantidad, precio=precio))
    try:
        if valida:
            assert r.status_code == 200, r.text
        else:
            # Un dato inválido debe dar error del pedido (4xx), no caída del servidor (5xx)
            assert 400 <= r.status_code < 500, f"{r.status_code}: {r.text}"
    finally:
        # Si el ERP aceptó una orden que debía rechazar, no la dejamos viva
        if r.ok:
            api.delete(f"{PO_URL}/{r.json()['data']['name']}")