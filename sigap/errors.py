"""Excepciones de dominio de SIGAP."""


class ErrorDominio(Exception):
    """Error de regla de negocio; se traduce a HTTP 4xx."""

    status = 400

    def __init__(self, mensaje, status=None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        if status:
            self.status = status


class NoEncontrado(ErrorDominio):
    status = 404


class StockInsuficiente(ErrorDominio):
    status = 409
