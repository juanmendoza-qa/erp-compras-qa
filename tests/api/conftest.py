import os
from datetime import date, timedelta

import pytest
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ["ERP_URL"]
PO_URL = f"{BASE_URL}/api/resource/Purchase Order"


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