"""Servicio de autenticación y autorización por roles (RBAC)."""
from werkzeug.security import check_password_hash, generate_password_hash

from ..errors import ErrorDominio

ROLES = ("admin", "acopiador", "vendedor")


class ServicioAuth:
    def __init__(self, usuarios):
        self.usuarios = usuarios

    def registrar(self, username, password, rol):
        if rol not in ROLES:
            raise ErrorDominio("Rol inválido")
        if len(password) < 8:
            raise ErrorDominio("La contraseña debe tener 8 caracteres o más")
        if self.usuarios.por_username(username):
            raise ErrorDominio("El usuario ya existe", 409)
        return self.usuarios.crear(
            username, generate_password_hash(password), rol)

    def autenticar(self, username, password):
        usuario = self.usuarios.por_username(username or "")
        if not usuario or not check_password_hash(
                usuario["password_hash"], password or ""):
            raise ErrorDominio("Credenciales inválidas", 401)
        return usuario
