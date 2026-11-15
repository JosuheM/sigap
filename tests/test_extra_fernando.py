def test_stock_sin_sesion_devuelve_401(client):
    r = client.get("/api/stock")
    assert r.status_code == 401


def test_login_con_clave_incorrecta_devuelve_401(client):
    r = client.post("/api/auth/login",
                    json={"username": "admin", "password": "mala"})
    assert r.status_code == 401