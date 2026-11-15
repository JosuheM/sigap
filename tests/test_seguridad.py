"""Pruebas de seguridad alineadas con OWASP Top 10 (2021)."""
import pytest

pytestmark = pytest.mark.seguridad


def test_a01_control_de_acceso_por_rol(vendedor, acopiador):
    """A01 Broken Access Control: cada rol solo ejecuta lo permitido."""
    assert vendedor.post("/api/lotes", json={}).status_code == 403
    assert vendedor.post("/api/productores", json={}).status_code == 403
    assert acopiador.post("/api/pedidos", json={}).status_code == 403
    assert acopiador.get("/api/reportes/ventas").status_code == 403
    assert acopiador.post("/api/usuarios", json={}).status_code == 403
    assert vendedor.post("/api/productos", json={}).status_code == 403


def test_a02_hash_de_contrasena(app):
    """A02 Cryptographic Failures: contraseñas con hash salado."""
    import sqlite3
    conn = sqlite3.connect(app.config["DATABASE"])
    hashes = [r[0] for r in conn.execute("SELECT password_hash FROM usuario")]
    assert all(h.startswith(("scrypt:", "pbkdf2:")) for h in hashes)
    assert "Admin#2026" not in "".join(hashes)


@pytest.mark.parametrize("payload", [
    "' OR '1'='1", "'; DROP TABLE productor;--", "P-0001' OR 1=1 --"])
def test_a03_inyeccion_sql(admin, payload):
    """A03 Injection: consultas parametrizadas neutralizan la inyección."""
    r = admin.post("/api/productores", json={
        "codigo": "P-0900", "nombre": payload, "comunidad": payload})
    assert r.status_code == 201
    assert r.get_json()["nombre"] == payload
    assert admin.get("/api/productores").status_code == 200
    assert admin.post("/api/auth/login", json={
        "username": payload, "password": payload}).status_code == 401


def test_a03_validacion_de_entrada(admin):
    r = admin.post("/api/productores", json={
        "codigo": "MALO", "nombre": "x", "comunidad": "y"})
    assert r.status_code == 400
    r = admin.post("/api/lotes", json={
        "producto_id": 1, "parcela_id": 1, "fecha_cosecha": "no-fecha",
        "cantidad_kg": 1, "calidad": "A"})
    assert r.status_code == 400


def test_a05_cabeceras_de_seguridad(client):
    """A05 Security Misconfiguration: cabeceras defensivas."""
    h = client.get("/").headers
    assert h["X-Content-Type-Options"] == "nosniff"
    assert h["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in h["Content-Security-Policy"]


def test_a05_cookie_httponly_samesite(client):
    r = client.post("/api/auth/login", json={
        "username": "admin", "password": "Admin#2026"})
    cookie = r.headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Strict" in cookie


def test_a07_bloqueo_por_intentos_fallidos(client):
    """A07 Identification and Authentication Failures."""
    for _ in range(5):
        assert client.post("/api/auth/login", json={
            "username": "admin", "password": "x"}).status_code == 401
    r = client.post("/api/auth/login", json={
        "username": "admin", "password": "Admin#2026"})
    assert r.status_code == 429


def test_a07_politica_de_contrasena(admin):
    r = admin.post("/api/usuarios", json={
        "username": "debil", "password": "123", "rol": "vendedor"})
    assert r.status_code == 400


def test_a04_content_type_obligatorio(admin):
    r = admin.post("/api/productores", data="codigo=P-0001",
                   content_type="application/x-www-form-urlencoded")
    assert r.status_code == 415


def test_no_filtra_detalles_internos(admin):
    r = admin.get("/api/productores/99999")
    assert r.status_code == 404
    assert "Traceback" not in r.get_data(as_text=True)
