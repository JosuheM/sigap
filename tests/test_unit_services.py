"""Pruebas unitarias de servicios y repositorios sobre SQLite en memoria."""
import pytest

from sigap import db
from sigap.app import Contenedor
from sigap.errors import ErrorDominio, NoEncontrado, StockInsuficiente


@pytest.fixture()
def c():
    conn = db.connect(":memory:")
    db.init_db(conn)
    yield Contenedor(conn)
    conn.close()


@pytest.fixture()
def base(c):
    prod = c.productos.crear({"nombre": "Papa", "precio_base": 3.0,
                              "stock_minimo": 100})
    p = c.productores.crear({"codigo": "P-0001", "nombre": "X",
                             "comunidad": "Y"})
    par = c.productores.agregar_parcela(p["id"], {
        "nombre": "Z", "area_ha": 1, "altitud_msnm": 3300})
    cli = c.clientes.crear({"razon_social": "Demo", "tipo": "mayorista"})
    return c, prod, par, cli


def lote(c, prod, par, fecha, kg):
    return c.acopio.registrar_lote({
        "producto_id": prod["id"], "parcela_id": par["id"],
        "fecha_cosecha": fecha, "cantidad_kg": kg, "calidad": "A"})


def test_auth_registrar_y_autenticar(c):
    c.auth.registrar("u1", "Clave#1234", "vendedor")
    assert c.auth.autenticar("u1", "Clave#1234")["rol"] == "vendedor"
    with pytest.raises(ErrorDominio) as e:
        c.auth.autenticar("u1", "mala")
    assert e.value.status == 401


def test_auth_valida_rol_clave_y_duplicado(c):
    with pytest.raises(ErrorDominio):
        c.auth.registrar("u", "Clave#1234", "root")
    with pytest.raises(ErrorDominio):
        c.auth.registrar("u", "corta", "admin")
    c.auth.registrar("u", "Clave#1234", "admin")
    with pytest.raises(ErrorDominio) as e:
        c.auth.registrar("u", "Clave#1234", "admin")
    assert e.value.status == 409


def test_password_no_se_guarda_en_claro(c):
    c.auth.registrar("u", "Clave#1234", "admin")
    assert "Clave#1234" not in c.usuarios.por_username("u")["password_hash"]


def test_productor_codigo_duplicado(c):
    c.productores.crear({"codigo": "P-0001", "nombre": "a", "comunidad": "b"})
    with pytest.raises(ErrorDominio) as e:
        c.productores.crear({"codigo": "P-0001", "nombre": "a",
                             "comunidad": "b"})
    assert e.value.status == 409


def test_productor_actualizar_y_obtener(c):
    p = c.productores.crear({"codigo": "P-0002", "nombre": "a",
                             "comunidad": "b"})
    nuevo = c.productores.actualizar(p["id"], {"nombre": "n", "activo": False})
    assert nuevo["nombre"] == "n" and nuevo["activo"] == 0
    assert c.productores.obtener(p["id"])["parcelas"] == []
    with pytest.raises(NoEncontrado):
        c.productores.obtener(999)
    with pytest.raises(NoEncontrado):
        c.productores.actualizar(999, {})


def test_parcela_validaciones(c):
    p = c.productores.crear({"codigo": "P-0003", "nombre": "a",
                             "comunidad": "b"})
    with pytest.raises(NoEncontrado):
        c.productores.agregar_parcela(999, {})
    with pytest.raises(ErrorDominio):
        c.productores.agregar_parcela(p["id"], {
            "nombre": "z", "area_ha": -1, "altitud_msnm": 3000})
    with pytest.raises(ErrorDominio):
        c.productores.agregar_parcela(p["id"], {
            "nombre": "z", "area_ha": 1, "altitud_msnm": 7000})


def test_producto_validaciones(c):
    with pytest.raises(ErrorDominio):
        c.productos.crear({"nombre": "a", "precio_base": 0})
    with pytest.raises(ErrorDominio):
        c.productos.crear({"nombre": "a", "precio_base": 1,
                           "stock_minimo": -5})


def test_lote_validaciones(base):
    c, prod, par, _ = base
    with pytest.raises(NoEncontrado):
        c.acopio.registrar_lote({"producto_id": 99, "parcela_id": par["id"],
                                 "fecha_cosecha": "2026-01-01",
                                 "cantidad_kg": 1, "calidad": "A"})
    with pytest.raises(NoEncontrado):
        c.acopio.registrar_lote({"producto_id": prod["id"], "parcela_id": 99,
                                 "fecha_cosecha": "2026-01-01",
                                 "cantidad_kg": 1, "calidad": "A"})
    with pytest.raises(ErrorDominio):
        c.acopio.registrar_lote({"producto_id": prod["id"],
                                 "parcela_id": par["id"],
                                 "fecha_cosecha": "2026-01-01",
                                 "cantidad_kg": 1, "calidad": "Z"})


def test_fifo_consume_lote_mas_antiguo_primero(base):
    c, prod, par, cli = base
    viejo = lote(c, prod, par, "2026-01-01", 100)
    nuevo = lote(c, prod, par, "2026-02-01", 100)
    ped = c.pedidos.crear({"cliente_id": cli["id"], "items": [
        {"producto_id": prod["id"], "cantidad_kg": 150}]})
    c.pedidos.confirmar(ped["id"])
    asign = c.pedidos.pedidos.asignaciones(ped["id"])
    assert [(a["lote_id"], a["kg"]) for a in asign] == [
        (viejo["id"], 100), (nuevo["id"], 50)]
    assert c.pedidos.lotes.obtener(viejo["id"])["disponible_kg"] == 0
    assert c.pedidos.lotes.obtener(nuevo["id"])["disponible_kg"] == 50


def test_stock_insuficiente_no_altera_inventario(base):
    c, prod, par, cli = base
    lote(c, prod, par, "2026-01-01", 50)
    ped = c.pedidos.crear({"cliente_id": cli["id"], "items": [
        {"producto_id": prod["id"], "cantidad_kg": 80}]})
    with pytest.raises(StockInsuficiente):
        c.pedidos.confirmar(ped["id"])
    assert c.pedidos.productos.stock_disponible(prod["id"]) == 50
    assert c.pedidos.detalle(ped["id"])["estado"] == "pendiente"


def test_cancelar_confirmado_repone_stock(base):
    c, prod, par, cli = base
    lote(c, prod, par, "2026-01-01", 100)
    ped = c.pedidos.crear({"cliente_id": cli["id"], "items": [
        {"producto_id": prod["id"], "cantidad_kg": 60}]})
    c.pedidos.confirmar(ped["id"])
    assert c.pedidos.productos.stock_disponible(prod["id"]) == 40
    c.pedidos.cancelar(ped["id"])
    assert c.pedidos.productos.stock_disponible(prod["id"]) == 100


def test_transiciones_invalidas(base):
    c, prod, par, cli = base
    lote(c, prod, par, "2026-01-01", 100)
    ped = c.pedidos.crear({"cliente_id": cli["id"], "items": [
        {"producto_id": prod["id"], "cantidad_kg": 10}]})
    with pytest.raises(ErrorDominio) as e:
        c.pedidos.despachar(ped["id"])
    assert e.value.status == 409
    c.pedidos.confirmar(ped["id"])
    c.pedidos.despachar(ped["id"])
    with pytest.raises(ErrorDominio):
        c.pedidos.cancelar(ped["id"])


def test_pedido_validaciones(base):
    c, prod, par, cli = base
    with pytest.raises(NoEncontrado):
        c.pedidos.crear({"cliente_id": 99, "items": [1]})
    with pytest.raises(ErrorDominio):
        c.pedidos.crear({"cliente_id": cli["id"], "items": []})
    with pytest.raises(NoEncontrado):
        c.pedidos.crear({"cliente_id": cli["id"], "items": [
            {"producto_id": 99, "cantidad_kg": 1}]})
    with pytest.raises(NoEncontrado):
        c.pedidos.detalle(99)
    with pytest.raises(ErrorDominio):
        c.clientes.crear({"razon_social": "a", "tipo": "otro"})


def test_total_aplica_descuento_mayorista(base):
    c, prod, par, cli = base
    ped = c.pedidos.crear({"cliente_id": cli["id"], "items": [
        {"producto_id": prod["id"], "cantidad_kg": 200}]})
    assert ped["items"][0]["precio_unit"] == 2.85
    assert ped["total"] == 570.0


def test_alerta_stock_bajo_observer(base):
    c, prod, par, cli = base
    lote(c, prod, par, "2026-01-01", 120)
    ped = c.pedidos.crear({"cliente_id": cli["id"], "items": [
        {"producto_id": prod["id"], "cantidad_kg": 50}]})
    c.pedidos.confirmar(ped["id"])
    alertas = c.alertas.listar()
    assert len(alertas) == 1 and "Stock bajo" in alertas[0]["mensaje"]
    estado = c.acopio.stock()[0]
    assert estado["bajo"] is True and estado["disponible_kg"] == 70


def test_reportes(base):
    c, prod, par, cli = base
    lote(c, prod, par, "2026-01-01", 300)
    ped = c.pedidos.crear({"cliente_id": cli["id"], "items": [
        {"producto_id": prod["id"], "cantidad_kg": 100}]})
    assert c.reportes.ventas_por_producto() == []
    c.pedidos.confirmar(ped["id"])
    ventas = c.reportes.ventas_por_producto()
    assert ventas[0]["kg"] == 100 and ventas[0]["monto"] == 285.0
    traz = c.reportes.trazabilidad(ped["id"])
    assert traz["lotes"][0]["productor"] == "P-0001"
    with pytest.raises(NoEncontrado):
        c.reportes.trazabilidad(99)


def test_repositorio_rechaza_tabla_no_permitida():
    from sigap.repositories.base import RepositorioBase
    with pytest.raises(ValueError):
        class Malo(RepositorioBase):
            tabla = "usuario; DROP TABLE x"
