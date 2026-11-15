"""Módulo 4: reportes de ventas y trazabilidad del lote al pedido."""
from ..errors import NoEncontrado


class ServicioReportes:
    def __init__(self, conn, pedidos):
        self.conn = conn
        self.pedidos = pedidos

    def ventas_por_producto(self):
        filas = self.conn.execute(
            "SELECT pr.nombre AS producto, "
            "ROUND(SUM(i.cantidad_kg), 2) AS kg, "
            "ROUND(SUM(i.cantidad_kg * i.precio_unit), 2) AS monto "
            "FROM pedido_item i JOIN pedido p ON p.id = i.pedido_id "
            "JOIN producto pr ON pr.id = i.producto_id "
            "WHERE p.estado IN ('confirmado','despachado') "
            "GROUP BY pr.id ORDER BY monto DESC").fetchall()
        return [dict(f) for f in filas]

    def trazabilidad(self, pedido_id):
        pedido = self.pedidos.obtener(pedido_id)
        if not pedido:
            raise NoEncontrado("Pedido no encontrado")
        return {"pedido_id": pedido_id, "estado": pedido["estado"],
                "lotes": self.pedidos.asignaciones(pedido_id)}
