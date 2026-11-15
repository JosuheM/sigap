"""Patrón Strategy: políticas de descuento intercambiables."""
from abc import ABC, abstractmethod


class PoliticaDescuento(ABC):
    """Interfaz de una política de descuento."""

    @abstractmethod
    def porcentaje(self, cantidad_kg):
        """Devuelve el porcentaje de descuento (0-100)."""


class SinDescuento(PoliticaDescuento):
    def porcentaje(self, cantidad_kg):
        return 0.0


class DescuentoPorVolumen(PoliticaDescuento):
    """Aplica 5 % desde 100 kg y 10 % desde 500 kg."""

    def porcentaje(self, cantidad_kg):
        if cantidad_kg >= 500:
            return 10.0
        if cantidad_kg >= 100:
            return 5.0
        return 0.0


def politica_para(tipo_cliente):
    """Fábrica simple: elige la política según el tipo de cliente."""
    if tipo_cliente == "mayorista":
        return DescuentoPorVolumen()
    return SinDescuento()


def precio_con_descuento(precio_base, cantidad_kg, tipo_cliente):
    """Calcula el precio unitario tras aplicar la política."""
    pct = politica_para(tipo_cliente).porcentaje(cantidad_kg)
    return round(precio_base * (1 - pct / 100), 2)
