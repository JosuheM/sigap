"""Pruebas unitarias: dominio (Strategy, validaciones, eventos)."""
from datetime import date, timedelta

import pytest

from sigap.domain import validation as v
from sigap.domain.events import BusEventos
from sigap.domain.pricing import (DescuentoPorVolumen, SinDescuento,
                                  politica_para, precio_con_descuento)
from sigap.errors import ErrorDominio


@pytest.mark.parametrize("kg,pct", [(1, 0), (99.9, 0), (100, 5), (499, 5),
                                    (500, 10), (2000, 10)])
def test_descuento_por_volumen(kg, pct):
    assert DescuentoPorVolumen().porcentaje(kg) == pct


def test_minorista_no_recibe_descuento():
    assert isinstance(politica_para("minorista"), SinDescuento)
    assert precio_con_descuento(10, 1000, "minorista") == 10


def test_mayorista_recibe_descuento():
    assert precio_con_descuento(10, 500, "mayorista") == 9.0
    assert precio_con_descuento(10, 100, "mayorista") == 9.5


def test_requerido_detecta_faltantes():
    with pytest.raises(ErrorDominio, match="nombre"):
        v.requerido({"codigo": "x"}, ("codigo", "nombre"))
    v.requerido({"a": 1}, ("a",))


@pytest.mark.parametrize("valor", ["abc", None, 0, -3, "-1"])
def test_numero_positivo_rechaza(valor):
    with pytest.raises(ErrorDominio):
        v.numero_positivo(valor, "x")


def test_numero_positivo_acepta():
    assert v.numero_positivo("2.5", "x") == 2.5


def test_telefono_y_codigo():
    assert v.telefono_valido("987654321") == "987654321"
    assert v.telefono_valido(None) is None
    with pytest.raises(ErrorDominio):
        v.telefono_valido("12345")
    assert v.codigo_valido("P-0001") == "P-0001"
    with pytest.raises(ErrorDominio):
        v.codigo_valido("0001")


def test_fecha_iso():
    assert v.fecha_iso("2026-01-15") == "2026-01-15"
    with pytest.raises(ErrorDominio):
        v.fecha_iso("15/01/2026")
    futura = (date.today() + timedelta(days=2)).isoformat()
    with pytest.raises(ErrorDominio, match="futura"):
        v.fecha_iso(futura)


def test_bus_eventos_notifica_suscriptores():
    recibidos = []
    bus = BusEventos()
    bus.suscribir("e", lambda **d: recibidos.append(d))
    bus.publicar("e", x=1)
    bus.publicar("otro", x=2)
    assert recibidos == [{"x": 1}]
