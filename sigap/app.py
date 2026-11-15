"""Fábrica de la aplicación Flask de SIGAP (capa de presentación/API)."""
import os
from functools import wraps

from flask import Flask, g, jsonify, request, session

from . import db
from .domain.events import BusEventos
from .errors import ErrorDominio
from .repositories import repos
from .services.acopio import ServicioAcopio
from .services.auth import ServicioAuth
from .services.catalogo import ServicioProductores, ServicioProductos
from .services.reportes import ServicioReportes
from .services.ventas import ServicioClientes, ServicioPedidos

MAX_INTENTOS = 5


class Contenedor:
    """Inyección de dependencias: repositorios y servicios por petición."""

    def __init__(self, conn):
        bus = BusEventos()
        self.usuarios = repos.UsuarioRepo(conn)
        productores = repos.ProductorRepo(conn)
        parcelas = repos.ParcelaRepo(conn)
        productos = repos.ProductoRepo(conn)
        lotes = repos.LoteRepo(conn)
        clientes = repos.ClienteRepo(conn)
        pedidos = repos.PedidoRepo(conn)
        self.alertas = repos.AlertaRepo(conn)
        self.auth = ServicioAuth(self.usuarios)
        self.productores = ServicioProductores(productores, parcelas)
        self.productos = ServicioProductos(productos)
        self.acopio = ServicioAcopio(lotes, productos, parcelas,
                                     self.alertas, bus)
        self.clientes = ServicioClientes(clientes)
        self.pedidos = ServicioPedidos(pedidos, clientes, productos,
                                       lotes, bus)
        self.reportes = ServicioReportes(conn, pedidos)
        self.repo_productores = productores
        self.repo_productos = productos
        self.repo_clientes = clientes
        self.repo_pedidos = pedidos


def requiere_rol(*roles):
    """Decorador RBAC: exige sesión y que el rol esté permitido."""
    def decorador(fn):
        @wraps(fn)
        def interno(*args, **kwargs):
            if "uid" not in session:
                raise ErrorDominio("Autenticación requerida", 401)
            if roles and session.get("rol") not in roles:
                raise ErrorDominio("No autorizado para esta operación", 403)
            return fn(*args, **kwargs)
        return interno
    return decorador


def crear_app(config=None):
    app = Flask(__name__, static_folder="static", static_url_path="")
    app.config.update(
        DATABASE=os.environ.get("SIGAP_DB", "sigap.db"),
        SECRET_KEY=os.environ.get("SIGAP_SECRET", os.urandom(24)),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_SECURE=os.environ.get("SIGAP_HTTPS") == "1",
    )
    if config:
        app.config.update(config)
    app.intentos = {}
    conn_ini = db.connect(app.config["DATABASE"])
    try:
        db.init_db(conn_ini)
    finally:
        conn_ini.close()

    @app.before_request
    def abrir():
        g.conn = db.connect(app.config["DATABASE"])
        g.c = Contenedor(g.conn)
        escribe = request.method in ("POST", "PUT", "DELETE")
        if escribe and request.path.startswith("/api") and \
                request.content_length and not request.is_json:
            raise ErrorDominio("Se requiere Content-Type application/json",
                               415)

    @app.after_request
    def cerrar(resp):
        conn = g.pop("conn", None)
        if conn is not None:
            (conn.commit if resp.status_code < 400 else conn.rollback)()
            conn.close()
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Content-Security-Policy"] = \
            "default-src 'self'; style-src 'self' 'unsafe-inline'"
        return resp

    @app.errorhandler(ErrorDominio)
    def error_dominio(e):
        return jsonify(error=e.mensaje), e.status

    @app.errorhandler(404)
    def no_ruta(_):
        return jsonify(error="Recurso no encontrado"), 404

    @app.errorhandler(Exception)
    def error_inesperado(_):
        app.logger.exception("Error no controlado")
        return jsonify(error="Error interno del servidor"), 500

    @app.get("/")
    def inicio():
        return app.send_static_file("index.html")

    # ---------------------------------------------------------- autenticación
    @app.post("/api/auth/login")
    def login():
        datos = request.get_json(silent=True) or {}
        usuario = datos.get("username", "")
        if app.intentos.get(usuario, 0) >= MAX_INTENTOS:
            raise ErrorDominio("Cuenta bloqueada por intentos fallidos", 429)
        try:
            u = g.c.auth.autenticar(usuario, datos.get("password"))
        except ErrorDominio:
            app.intentos[usuario] = app.intentos.get(usuario, 0) + 1
            raise
        app.intentos.pop(usuario, None)
        session.clear()
        session.update(uid=u["id"], rol=u["rol"])
        return jsonify(username=u["username"], rol=u["rol"])

    @app.post("/api/auth/logout")
    def logout():
        session.clear()
        return jsonify(ok=True)

    @app.post("/api/usuarios")
    @requiere_rol("admin")
    def crear_usuario():
        d = request.get_json(silent=True) or {}
        id_ = g.c.auth.registrar(d.get("username", ""), d.get("password", ""),
                                 d.get("rol"))
        return jsonify(id=id_), 201

    # -------------------------------------------------- módulo 1: catálogo
    @app.get("/api/productores")
    @requiere_rol()
    def listar_productores():
        return jsonify(g.c.repo_productores.listar())

    @app.post("/api/productores")
    @requiere_rol("admin", "acopiador")
    def crear_productor():
        return jsonify(g.c.productores.crear(
            request.get_json(silent=True) or {})), 201

    @app.get("/api/productores/<int:id_>")
    @requiere_rol()
    def ver_productor(id_):
        return jsonify(g.c.productores.obtener(id_))

    @app.put("/api/productores/<int:id_>")
    @requiere_rol("admin", "acopiador")
    def editar_productor(id_):
        return jsonify(g.c.productores.actualizar(
            id_, request.get_json(silent=True) or {}))

    @app.post("/api/productores/<int:id_>/parcelas")
    @requiere_rol("admin", "acopiador")
    def crear_parcela(id_):
        return jsonify(g.c.productores.agregar_parcela(
            id_, request.get_json(silent=True) or {})), 201

    @app.get("/api/productos")
    @requiere_rol()
    def listar_productos():
        return jsonify(g.c.repo_productos.listar())

    @app.post("/api/productos")
    @requiere_rol("admin")
    def crear_producto():
        return jsonify(g.c.productos.crear(
            request.get_json(silent=True) or {})), 201

    # ------------------------------------ módulo 2: acopio e inventario
    @app.post("/api/lotes")
    @requiere_rol("admin", "acopiador")
    def crear_lote():
        return jsonify(g.c.acopio.registrar_lote(
            request.get_json(silent=True) or {})), 201

    @app.get("/api/stock")
    @requiere_rol()
    def ver_stock():
        return jsonify(g.c.acopio.stock())

    @app.get("/api/alertas")
    @requiere_rol()
    def ver_alertas():
        return jsonify(g.c.alertas.listar())

    # --------------------------------------------------- módulo 3: ventas
    @app.get("/api/clientes")
    @requiere_rol()
    def listar_clientes():
        return jsonify(g.c.repo_clientes.listar())

    @app.post("/api/clientes")
    @requiere_rol("admin", "vendedor")
    def crear_cliente():
        return jsonify(g.c.clientes.crear(
            request.get_json(silent=True) or {})), 201

    @app.get("/api/pedidos")
    @requiere_rol()
    def listar_pedidos():
        return jsonify(g.c.repo_pedidos.listar())

    @app.post("/api/pedidos")
    @requiere_rol("admin", "vendedor")
    def crear_pedido():
        return jsonify(g.c.pedidos.crear(
            request.get_json(silent=True) or {})), 201

    @app.get("/api/pedidos/<int:id_>")
    @requiere_rol()
    def ver_pedido(id_):
        return jsonify(g.c.pedidos.detalle(id_))

    @app.post("/api/pedidos/<int:id_>/confirmar")
    @requiere_rol("admin", "vendedor")
    def confirmar_pedido(id_):
        return jsonify(g.c.pedidos.confirmar(id_))

    @app.post("/api/pedidos/<int:id_>/despachar")
    @requiere_rol("admin", "vendedor")
    def despachar_pedido(id_):
        return jsonify(g.c.pedidos.despachar(id_))

    @app.post("/api/pedidos/<int:id_>/cancelar")
    @requiere_rol("admin", "vendedor")
    def cancelar_pedido(id_):
        return jsonify(g.c.pedidos.cancelar(id_))

    # ------------------------------------------------ módulo 4: reportes
    @app.get("/api/reportes/ventas")
    @requiere_rol("admin", "vendedor")
    def reporte_ventas():
        return jsonify(g.c.reportes.ventas_por_producto())

    @app.get("/api/reportes/trazabilidad/<int:id_>")
    @requiere_rol("admin", "vendedor")
    def reporte_trazabilidad(id_):
        return jsonify(g.c.reportes.trazabilidad(id_))

    return app
