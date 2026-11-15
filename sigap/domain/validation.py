"""Validaciones de entrada (OWASP A03: Injection / validación)."""
import re
from datetime import date

from ..errors import ErrorDominio

_TEL = re.compile(r"^\d{9}$")
_CODIGO = re.compile(r"^P-\d{4}$")


def requerido(datos, campos):
    faltan = [c for c in campos if datos.get(c) in (None, "")]
    if faltan:
        raise ErrorDominio("Faltan campos: " + ", ".join(faltan))


def numero_positivo(valor, nombre):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ErrorDominio(f"{nombre} debe ser numérico") from None
    if numero <= 0:
        raise ErrorDominio(f"{nombre} debe ser mayor que cero")
    return numero


def telefono_valido(valor):
    if valor and not _TEL.match(str(valor)):
        raise ErrorDominio("El teléfono debe tener 9 dígitos")
    return valor


def codigo_valido(valor):
    if not _CODIGO.match(str(valor)):
        raise ErrorDominio("El código debe tener el formato P-0000")
    return valor


def fecha_iso(valor):
    try:
        f = date.fromisoformat(str(valor))
    except ValueError:
        raise ErrorDominio("Fecha inválida (use AAAA-MM-DD)") from None
    if f > date.today():
        raise ErrorDominio("La fecha no puede ser futura")
    return f.isoformat()
