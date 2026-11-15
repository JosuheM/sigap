"""Pruebas de regresión: invariantes críticos que no deben romperse."""
import pytest

pytestmark = pytest.mark.regresion


def test_rg01_cancelar_dos_veces_no_duplica_stock(admin):
    """Riesgo: cancelar dos veces podría reponer el inventario dos veces."""
    base = {s["producto_id"]: s["disponible_kg"]
            for s in admin.get("/api/stock").get_json()}
    pid = admin.post("/api/pedidos", json={"cliente_id": 2, "items": [
        {"producto_id": 1, "cantidad_kg": 30}]}).get_json()["id"]
    admin.post(f"/api/pedidos/{pid}/confirmar")
    assert admin.post(f"/api/pedidos/{pid}/cancelar").status_code == 200
    assert admin.post(f"/api/pedidos/{pid}/cancelar").status_code == 409
    final = {s["producto_id"]: s["disponible_kg"]
             for s in admin.get("/api/stock").get_json()}
    assert final == base


def test_rg02_confirmar_dos_veces_no_descuenta_dos_veces(admin):
    """Riesgo: reconfirmar un pedido podría descontar el stock otra vez."""
    pid = admin.post("/api/pedidos", json={"cliente_id": 2, "items": [
        {"producto_id": 1, "cantidad_kg": 25}]}).get_json()["id"]
    admin.post(f"/api/pedidos/{pid}/confirmar")
    stock = admin.get("/api/stock").get_json()[0]["disponible_kg"]
    assert admin.post(f"/api/pedidos/{pid}/confirmar").status_code == 409
    assert admin.get("/api/stock").get_json()[0]["disponible_kg"] == stock


def test_rg03_confirmacion_parcial_no_deja_stock_a_medias(admin):
    """Riesgo: con falta de un producto no se descuenta el otro."""
    stock0 = admin.get("/api/stock").get_json()
    pid = admin.post("/api/pedidos", json={"cliente_id": 2, "items": [
        {"producto_id": 1, "cantidad_kg": 10},
        {"producto_id": 2, "cantidad_kg": 99999}]}).get_json()["id"]
    assert admin.post(f"/api/pedidos/{pid}/confirmar").status_code == 409
    assert admin.get("/api/stock").get_json() == stock0


def test_rg04_precio_se_congela_al_crear_pedido(admin):
    """El precio de un pedido no cambia si luego sube el precio base."""
    pid = admin.post("/api/pedidos", json={"cliente_id": 2, "items": [
        {"producto_id": 1, "cantidad_kg": 10}]}).get_json()["id"]
    admin.post("/api/productos", json={"nombre": "Otro", "precio_base": 99})
    assert admin.get(f"/api/pedidos/{pid}").get_json()["total"] == 32.0
