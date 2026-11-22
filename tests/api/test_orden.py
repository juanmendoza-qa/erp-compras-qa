from conftest import PO_URL


def test_orden_creada_por_el_fixture_existe(api, orden):
    r = api.get(f"{PO_URL}/{orden['name']}")

    assert r.status_code == 200, r.text
    assert r.json()["data"]["supplier"] == "Proveedor Demo Ltda"