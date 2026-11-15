"""Pruebas de rendimiento: latencia de endpoints críticos."""
import statistics
import time

import pytest

pytestmark = pytest.mark.rendimiento

MUESTRAS = 100
LIMITE_P95_MS = 200


def medir(fn, n=MUESTRAS):
    tiempos = []
    for _ in range(n):
        t0 = time.perf_counter()
        r = fn()
        tiempos.append((time.perf_counter() - t0) * 1000)
        assert r.status_code < 400
    tiempos.sort()
    return statistics.mean(tiempos), tiempos[int(0.95 * n) - 1]


def test_latencia_consulta_stock(admin):
    media, p95 = medir(lambda: admin.get("/api/stock"))
    print(f"\nRENDIMIENTO stock media={media:.2f}ms p95={p95:.2f}ms")
    assert p95 < LIMITE_P95_MS


def test_latencia_crear_pedido(admin):
    carga = {"cliente_id": 2, "items": [{"producto_id": 1,
                                         "cantidad_kg": 1}]}
    media, p95 = medir(lambda: admin.post("/api/pedidos", json=carga))
    print(f"\nRENDIMIENTO crear_pedido media={media:.2f}ms p95={p95:.2f}ms")
    assert p95 < LIMITE_P95_MS


def test_latencia_confirmar_pedido_fifo(admin):
    ids = [admin.post("/api/pedidos", json={"cliente_id": 2, "items": [
        {"producto_id": 1, "cantidad_kg": 1}]}).get_json()["id"]
        for _ in range(MUESTRAS)]
    it = iter(ids)
    media, p95 = medir(
        lambda: admin.post(f"/api/pedidos/{next(it)}/confirmar"))
    print(f"\nRENDIMIENTO confirmar media={media:.2f}ms p95={p95:.2f}ms")
    assert p95 < LIMITE_P95_MS


def test_latencia_reporte_con_volumen(admin):
    for _ in range(150):
        pid = admin.post("/api/pedidos", json={"cliente_id": 1, "items": [
            {"producto_id": 1, "cantidad_kg": 1}]}).get_json()["id"]
        admin.post(f"/api/pedidos/{pid}/confirmar")
    media, p95 = medir(lambda: admin.get("/api/reportes/ventas"))
    print(f"\nRENDIMIENTO reporte(150 pedidos) media={media:.2f}ms "
          f"p95={p95:.2f}ms")
    assert p95 < LIMITE_P95_MS
