import pytest

from sigap.app import crear_app
from seed import sembrar


@pytest.fixture()
def app(tmp_path):
    ruta = str(tmp_path / "test.db")
    app = crear_app({"DATABASE": ruta, "TESTING": True, "SECRET_KEY": "t"})
    sembrar(ruta)
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, user="admin", pwd="Admin#2026"):
    r = client.post("/api/auth/login",
                    json={"username": user, "password": pwd})
    assert r.status_code == 200, r.get_json()
    return client


@pytest.fixture()
def admin(client):
    return login(client)


@pytest.fixture()
def vendedor(app):
    c = app.test_client()
    return login(c, "ventas1", "Ventas#2026")


@pytest.fixture()
def acopiador(app):
    c = app.test_client()
    return login(c, "acopio1", "Acopio#2026")
