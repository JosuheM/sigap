"""Pruebas de aceptación automatizadas (Given/When/Then) por historia."""
import pytest

pytestmark = pytest.mark.aceptacion


def test_hu01_registrar_productor_con_parcela(acopiador):
    """HU-01: Como acopiador quiero registrar un productor y sus parcelas."""
    # Given un acopiador autenticado
    # When registra un productor con una parcela
    pid = acopiador.post("/api/productores", json={
        "codigo": "P-0300", "nombre": "Productor Anónimo 3",
        "comunidad": "Comunidad C"}).get_json()["id"]
    acopiador.post(f"/api/productores/{pid}/parcelas", json={
        "nombre": "P3", "area_ha": 1.2, "altitud_msnm": 3500})
    # Then el productor aparece con su parcela
    ficha = acopiador.get(f"/api/productores/{pid}").get_json()
    assert ficha["codigo"] == "P-0300" and len(ficha["parcelas"]) == 1


def test_hu02_registrar_lote_actualiza_inventario(acopiador):
    """HU-02: Como acopiador quiero registrar lotes para ver el inventario."""
    antes = {s["producto_id"]: s["disponible_kg"]
             for s in acopiador.get("/api/stock").get_json()}
    acopiador.post("/api/lotes", json={
        "producto_id": 2, "parcela_id": 1, "fecha_cosecha": "2026-03-10",
        "cantidad_kg": 80, "calidad": "A"})
    despues = {s["producto_id"]: s["disponible_kg"]
               for s in acopiador.get("/api/stock").get_json()}
    assert despues[2] == antes[2] + 80


def test_hu03_pedido_mayorista_recibe_descuento(vendedor):
    """HU-03: Como vendedor quiero cotizar con descuento por volumen."""
    ped = vendedor.post("/api/pedidos", json={"cliente_id": 1, "items": [
        {"producto_id": 1, "cantidad_kg": 500}]}).get_json()
    assert ped["items"][0]["precio_unit"] == 2.88
    assert ped["total"] == 1440.0


def test_hu04_no_se_confirma_sin_stock(vendedor):
    """HU-04: El sistema no debe vender más de lo que hay en inventario."""
    pid = vendedor.post("/api/pedidos", json={"cliente_id": 2, "items": [
        {"producto_id": 2, "cantidad_kg": 100000}]}).get_json()["id"]
    r = vendedor.post(f"/api/pedidos/{pid}/confirmar")
    assert r.status_code == 409 and "insuficiente" in r.get_json()["error"]


def test_hu05_trazabilidad_hasta_productor(vendedor):
    """HU-05: Como vendedor quiero saber de qué productores viene un pedido."""
    pid = vendedor.post("/api/pedidos", json={"cliente_id": 1, "items": [
        {"producto_id": 1, "cantidad_kg": 600}]}).get_json()["id"]
    vendedor.post(f"/api/pedidos/{pid}/confirmar")
    traz = vendedor.get(f"/api/reportes/trazabilidad/{pid}").get_json()
    productores = {x["productor"] for x in traz["lotes"]}
    assert productores == {"P-0001", "P-0002"}


def test_hu06_alerta_de_stock_bajo(vendedor):
    """HU-06: Como administrador quiero ser alertado por stock bajo."""
    pid = vendedor.post("/api/pedidos", json={"cliente_id": 2, "items": [
        {"producto_id": 2, "cantidad_kg": 250}]}).get_json()["id"]
    vendedor.post(f"/api/pedidos/{pid}/confirmar")
    alertas = vendedor.get("/api/alertas").get_json()
    assert any("Quinua" in a["mensaje"] for a in alertas)


def test_hu07_reporte_de_ventas(vendedor):
    """HU-07: Como vendedor quiero un reporte de ventas por producto."""
    pid = vendedor.post("/api/pedidos", json={"cliente_id": 2, "items": [
        {"producto_id": 1, "cantidad_kg": 10}]}).get_json()["id"]
    vendedor.post(f"/api/pedidos/{pid}/confirmar")
    ventas = vendedor.get("/api/reportes/ventas").get_json()
    assert ventas[0]["monto"] == 32.0
