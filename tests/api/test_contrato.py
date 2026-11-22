from contratos import (ERROR_DE_VALIDACION, LISTADO_PEDIDOS, RESPUESTA_PEDIDO,
                       RESPUESTA_RECEPCION, validar)
from conftest import PO_URL


def test_contrato_pedido_creado(orden):
    validar({"data": orden}, RESPUESTA_PEDIDO)


def test_contrato_pedido_leido(api, orden):
    r = api.get(f"{PO_URL}/{orden['name']}")

    assert r.status_code == 200, r.text
    validar(r.json(), RESPUESTA_PEDIDO)


def test_contrato_listado_de_pedidos(api):
    r = api.get(PO_URL)

    assert r.status_code == 200, r.text
    validar(r.json(), LISTADO_PEDIDOS)


def test_contrato_recepcion_presentada(docs):
    pedido = docs.pedido(cantidad=10)

    r = docs.recibir(pedido, 10)

    assert r.status_code == 200, r.text
    validar(r.json(), RESPUESTA_RECEPCION)


def test_contrato_error_de_validacion(docs):
    pedido = docs.pedido(cantidad=10)

    r = docs.recibir(pedido, 11)

    assert r.status_code == 417, r.text
    validar(r.json(), ERROR_DE_VALIDACION)
