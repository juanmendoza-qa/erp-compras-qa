import pytest


def recibir_diez(docs):
    """Deja stock en la bodega: pedido de 10 y recepción completa."""
    pedido = docs.pedido(cantidad=10)
    r = docs.recibir(pedido, 10)
    assert r.status_code == 200, r.text


def test_salida_descuenta_el_stock(docs):
    recibir_diez(docs)
    antes = docs.stock_disponible()

    r = docs.sacar(4)

    assert r.status_code == 200, r.text
    assert docs.stock_disponible() == antes - 4


# Cambia solo cuánto se saca por encima de lo disponible.
EXCESO = [
    pytest.param(0, True, id="todo-lo-disponible"),
    pytest.param(1, False, id="una-unidad-de-mas"),
]


@pytest.mark.parametrize("exceso, aceptada", EXCESO)
def test_salida_no_deja_el_stock_negativo(docs, exceso, aceptada):
    recibir_diez(docs)
    disponible = docs.stock_disponible()

    r = docs.sacar(disponible + exceso)

    if aceptada:
        assert r.status_code == 200, r.text
        assert docs.stock_disponible() == 0
    else:
        assert r.status_code == 417, f"{r.status_code}: {r.text}"
        assert r.json()["exc_type"] == "NegativeStockError", r.text
