from conftest import BASE_URL


def test_cliente_autenticado_lista_ordenes(api):
    r = api.get(f"{BASE_URL}/api/resource/Purchase Order")

    assert r.status_code == 200, r.text