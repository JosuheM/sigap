"""Módulo 3: pedidos y ventas con asignación FIFO de lotes."""
from datetime import date

from ..domain.pricing import precio_con_descuento
from ..domain import validation as v
from ..errors import ErrorDominio, NoEncontrado, StockInsuficiente


class ServicioClientes:
    def __init__(self, clientes):
        self.clientes = clientes

    def crear(self, datos):
        v.requerido(datos, ("razon_social", "tipo"))
        if datos["tipo"] not in ("minorista", "mayorista"):
            raise ErrorDominio("Tipo de cliente inválido")
        id_ = self.clientes.crear(datos["razon_social"], datos["tipo"])
        return self.clientes.obtener(id_)


class ServicioPedidos:
    TRANSICIONES = {
        "pendiente": ("confirmado", "cancelado"),
        "confirmado": ("despachado", "cancelado"),
        "despachado": (),
        "cancelado": (),
    }

    def __init__(self, pedidos, clientes, productos, lotes, bus):
        self.pedidos = pedidos
        self.clientes = clientes
        self.productos = productos
        self.lotes = lotes
        self.bus = bus

    def crear(self, datos):
        v.requerido(datos, ("cliente_id", "items"))
        cliente = self.clientes.obtener(datos["cliente_id"])
        if not cliente:
            raise NoEncontrado("Cliente no encontrado")
        if not datos["items"]:
            raise ErrorDominio("El pedido debe tener al menos un ítem")
        pedido_id = self.pedidos.crear(cliente["id"], date.today().isoformat())
        total = 0.0
        for item in datos["items"]:
            v.requerido(item, ("producto_id", "cantidad_kg"))
            producto = self.productos.obtener(item["producto_id"])
            if not producto:
                raise NoEncontrado("Producto no encontrado")
            kg = v.numero_positivo(item["cantidad_kg"], "cantidad_kg")
            precio = precio_con_descuento(producto["precio_base"], kg,
                                          cliente["tipo"])
            self.pedidos.agregar_item(pedido_id, producto["id"], kg, precio)
            total += precio * kg
        self.pedidos.fijar_total(pedido_id, total)
        return self.detalle(pedido_id)

    def detalle(self, pedido_id):
        pedido = self.pedidos.obtener(pedido_id)
        if not pedido:
            raise NoEncontrado("Pedido no encontrado")
        pedido["items"] = self.pedidos.items(pedido_id)
        return pedido

    def _validar_transicion(self, pedido, nuevo):
        if nuevo not in self.TRANSICIONES[pedido["estado"]]:
            raise ErrorDominio(
                f"Transición inválida: {pedido['estado']} -> {nuevo}", 409)

    def _planificar_item(self, item):
        """Calcula las tomas FIFO (lote, kg) que cubren un ítem."""
        pendiente = item["cantidad_kg"]
        tomas = []
        for lote in self.lotes.fifo(item["producto_id"]):
            if pendiente <= 1e-9:
                break
            tomar = min(pendiente, lote["disponible_kg"])
            tomas.append((item, lote["id"], tomar))
            pendiente -= tomar
        if pendiente > 1e-9:
            raise StockInsuficiente(
                f"Stock insuficiente para el producto {item['producto_id']}"
                f" (faltan {pendiente:.1f} kg)")
        return tomas

    def confirmar(self, pedido_id):
        """Reserva stock por FIFO; si falta stock, no se altera nada."""
        pedido = self.detalle(pedido_id)
        self._validar_transicion(pedido, "confirmado")
        plan = []
        for item in pedido["items"]:
            plan.extend(self._planificar_item(item))
        for item, lote_id, kg in plan:
            self.lotes.descontar(lote_id, kg)
            self.pedidos.registrar_asignacion(item["id"], lote_id, kg)
        self.pedidos.cambiar_estado(pedido_id, "confirmado")
        for producto_id in {i["producto_id"] for i in pedido["items"]}:
            self.bus.publicar("stock_actualizado", producto_id=producto_id)
        return self.detalle(pedido_id)

    def despachar(self, pedido_id):
        pedido = self.detalle(pedido_id)
        self._validar_transicion(pedido, "despachado")
        self.pedidos.cambiar_estado(pedido_id, "despachado")
        return self.detalle(pedido_id)

    def cancelar(self, pedido_id):
        """Cancela y repone el stock si el pedido estaba confirmado."""
        pedido = self.detalle(pedido_id)
        self._validar_transicion(pedido, "cancelado")
        if pedido["estado"] == "confirmado":
            for a in self.pedidos.asignaciones(pedido_id):
                self.lotes.reponer(a["lote_id"], a["kg"])
            self.pedidos.borrar_asignaciones(pedido_id)
        self.pedidos.cambiar_estado(pedido_id, "cancelado")
        return self.detalle(pedido_id)
