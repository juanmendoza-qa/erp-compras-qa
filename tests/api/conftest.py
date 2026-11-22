import os

import pytest
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ["ERP_URL"]


@pytest.fixture
def api():
    with requests.Session() as sesion:
        sesion.headers.update({
            "Authorization": f"token {os.environ['ERP_KEY']}:{os.environ['ERP_SECRET']}",
            "Accept": "application/json",
        })
        yield sesion