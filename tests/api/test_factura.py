import pytest


# Pedido de 10 y recepción de 5. Cambia solo la cantidad facturada desde la recepción.
DESDE_RECEPCION = [
    pytest.param(5, True, id="lo-recibido"),
    pytest.param(6, False, id="una-unidad-mas-de-lo-recibido"),
]


@pytest.mark.parametrize("facturada, aceptada", DESDE_RECEPCION)
def test_factura_desde_recepcion_no_supera_lo_recibido(docs, facturada, aceptada):
    pedido = docs.pedido(cantidad=10)
    recepcion = docs.recibir(pedido, 5)
    assert recepcion.status_code == 200, recepcion.text

    r = docs.facturar_recepcion(recepcion.json()["message"], facturada)

    if aceptada:
        assert r.status_code == 200, r.text
    else:
        assert r.status_code == 417, f"{r.status_code}: {r.text}"


# Pedido de 10 sin recepción. Cambia solo la cantidad facturada directo desde el pedido.
DESDE_PEDIDO = [
    pytest.param(10, True, id="lo-pedido"),
    pytest.param(11, False, id="una-unidad-mas-de-lo-pedido"),
]


@pytest.mark.parametrize("facturada, aceptada", DESDE_PEDIDO)
def test_factura_directa_no_supera_lo_pedido(docs, facturada, aceptada):
    pedido = docs.pedido(cantidad=10)

    r = docs.facturar(pedido, facturada)

    if aceptada:
        assert r.status_code == 200, r.text
    else:
        assert r.status_code == 417, f"{r.status_code}: {r.text}"


def test_factura_directa_puede_superar_lo_recibido_con_la_configuracion_actual(docs):
    """Documenta una decisión de configuración, no un defecto.

    Riesgo R3 (solo se paga lo que se recibió): con "Purchase Receipt Required"
    en "No" (Buying Settings, valor por defecto), el ERP deja facturar el pedido
    completo aunque solo se haya recibido una parte. Si el negocio exige recibir
    antes de pagar, ese ajuste debe ser "Yes", y este test debería invertirse.
    """
    pedido = docs.pedido(cantidad=10)
    assert docs.recibir(pedido, 5).status_code == 200

    r = docs.facturar(pedido, 10)

    assert r.status_code == 200, f"{r.status_code}: {r.text[:300]}"
