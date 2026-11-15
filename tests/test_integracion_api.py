"""Pruebas de integración: API REST + servicios + repositorios + SQLite."""
import pytest

pytestmark = pytest.mark.integracion


def test_login_correcto_e_incorrecto(client):
    assert client.post("/api/auth/login", json={
        "username": "admin", "password": "mala"}).status_code == 401
    r = client.post("/api/auth/login", json={
        "username": "admin", "password": "Admin#2026"})
    assert r.status_code == 200 and r.get_json()["rol"] == "admin"


def test_endpoint_protegido_sin_sesion(client):
    assert client.get("/api/stock").status_code == 401


def test_logout_cierra_sesion(admin):
    assert admin.get("/api/stock").status_code == 200
    admin.post("/api/auth/logout", json={})
    assert admin.get("/api/stock").status_code == 401


def test_crud_productor_y_parcela(admin):
    r = admin.post("/api/productores", json={
        "codigo": "P-0100", "nombre": "Nuevo", "comunidad": "C",
        "telefono": "999888777"})
    assert r.status_code == 201
    pid = r.get_json()["id"]
    r = admin.post(f"/api/productores/{pid}/parcelas", json={
        "nombre": "Alta", "area_ha": 2, "altitud_msnm": 3800})
    assert r.status_code == 201
    r = admin.put(f"/api/productores/{pid}", json={"comunidad": "Otra"})
    assert r.get_json()["comunidad"] == "Otra"
    r = admin.get(f"/api/productores/{pid}")
    assert len(r.get_json()["parcelas"]) == 1
    assert any(p["codigo"] == "P-0100"
               for p in admin.get("/api/productores").get_json())


def test_flujo_completo_pedido(admin):
    stock0 = {s["producto"]: s["disponible_kg"]
              for s in admin.get("/api/stock").get_json()}
    r = admin.post("/api/pedidos", json={"cliente_id": 1, "items": [
        {"producto_id": 1, "cantidad_kg": 200}]})
    assert r.status_code == 201
    pid = r.get_json()["id"]
    assert admin.post(f"/api/pedidos/{pid}/confirmar").status_code == 200
    stock1 = {s["producto"]: s["disponible_kg"]
              for s in admin.get("/api/stock").get_json()}
    assert stock1["Papa nativa"] == stock0["Papa nativa"] - 200
    assert admin.post(f"/api/pedidos/{pid}/despachar").status_code == 200
    assert admin.get(f"/api/pedidos/{pid}").get_json()["estado"] == \
        "despachado"
    traz = admin.get(f"/api/reportes/trazabilidad/{pid}").get_json()
    assert sum(x["kg"] for x in traz["lotes"]) == 200
    ventas = admin.get("/api/reportes/ventas").get_json()
    assert ventas[0]["producto"] == "Papa nativa"
    assert len(admin.get("/api/pedidos").get_json()) == 1


def test_stock_insuficiente_devuelve_409(admin):
    r = admin.post("/api/pedidos", json={"cliente_id": 1, "items": [
        {"producto_id": 1, "cantidad_kg": 999999}]})
    pid = r.get_json()["id"]
    r = admin.post(f"/api/pedidos/{pid}/confirmar")
    assert r.status_code == 409


def test_rollback_si_falla_a_mitad_del_pedido(admin):
    n0 = len(admin.get("/api/pedidos").get_json())
    r = admin.post("/api/pedidos", json={"cliente_id": 1, "items": [
        {"producto_id": 1, "cantidad_kg": 5},
        {"producto_id": 999, "cantidad_kg": 5}]})
    assert r.status_code == 404
    assert len(admin.get("/api/pedidos").get_json()) == n0


def test_lote_y_alertas(admin):
    r = admin.post("/api/lotes", json={
        "producto_id": 1, "parcela_id": 1, "fecha_cosecha": "2026-03-01",
        "cantidad_kg": 50, "calidad": "B"})
    assert r.status_code == 201
    assert admin.get("/api/alertas").status_code == 200


def test_crear_producto_cliente_y_usuario(admin):
    assert admin.post("/api/productos", json={
        "nombre": "Maíz", "precio_base": 4}).status_code == 201
    assert len(admin.get("/api/productos").get_json()) == 3
    assert admin.post("/api/clientes", json={
        "razon_social": "Otro", "tipo": "minorista"}).status_code == 201
    assert len(admin.get("/api/clientes").get_json()) == 3
    assert admin.post("/api/usuarios", json={
        "username": "nuevo", "password": "Nuevo#2026",
        "rol": "vendedor"}).status_code == 201


def test_cancelar_pedido_via_api(admin):
    pid = admin.post("/api/pedidos", json={"cliente_id": 2, "items": [
        {"producto_id": 2, "cantidad_kg": 10}]}).get_json()["id"]
    admin.post(f"/api/pedidos/{pid}/confirmar")
    r = admin.post(f"/api/pedidos/{pid}/cancelar")
    assert r.get_json()["estado"] == "cancelado"


def test_roles_acceden_a_lo_suyo(vendedor, acopiador):
    assert vendedor.post("/api/clientes", json={
        "razon_social": "V", "tipo": "minorista"}).status_code == 201
    assert acopiador.post("/api/productores", json={
        "codigo": "P-0200", "nombre": "A",
        "comunidad": "B"}).status_code == 201


def test_ruta_inexistente_y_ui(client):
    assert client.get("/api/nada").status_code == 404
    r = client.get("/")
    assert r.status_code == 200 and b"SIGAP" in r.data
