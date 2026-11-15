"""Patrón Observer: bus de eventos de dominio muy simple."""
from collections import defaultdict


class BusEventos:
    def __init__(self):
        self._suscriptores = defaultdict(list)

    def suscribir(self, evento, manejador):
        self._suscriptores[evento].append(manejador)

    def publicar(self, evento, **datos):
        for manejador in self._suscriptores[evento]:
            manejador(**datos)
