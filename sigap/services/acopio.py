"""Módulo 2: acopio de lotes e inventario con alerta de stock bajo."""
from datetime import datetime

from ..errors import ErrorDominio, NoEncontrado
from ..domain import validation as v


class ServicioAcopio:
    def __init__(self, lotes, productos, parcelas, alertas, bus):
        self.lotes = lotes
        self.productos = productos
        self.parcelas = parcelas
        self.alertas = alertas
        bus.suscribir("stock_actualizado", self._verificar_stock_bajo)

    def registrar_lote(self, datos):
        v.requerido(datos, ("producto_id", "parcela_id", "fecha_cosecha",
                            "cantidad_kg", "calidad"))
        if not self.productos.obtener(datos["producto_id"]):
            raise NoEncontrado("Producto no encontrado")
        if not self.parcelas.obtener(datos["parcela_id"]):
            raise NoEncontrado("Parcela no encontrada")
        fecha = v.fecha_iso(datos["fecha_cosecha"])
        kg = v.numero_positivo(datos["cantidad_kg"], "cantidad_kg")
        if datos["calidad"] not in ("A", "B", "C"):
            raise ErrorDominio("Calidad debe ser A, B o C")
        id_ = self.lotes.crear(datos["producto_id"], datos["parcela_id"],
                               fecha, kg, datos["calidad"])
        return self.lotes.obtener(id_)

    def stock(self):
        """Stock disponible por producto, con indicador de stock bajo."""
        resultado = []
        for p in self.productos.listar():
            kg = self.productos.stock_disponible(p["id"])
            resultado.append({
                "producto_id": p["id"], "producto": p["nombre"],
                "disponible_kg": round(kg, 2),
                "stock_minimo": p["stock_minimo"],
                "bajo": kg < p["stock_minimo"]})
        return resultado

    def _verificar_stock_bajo(self, producto_id):
        producto = self.productos.obtener(producto_id)
        kg = self.productos.stock_disponible(producto_id)
        if producto and kg < producto["stock_minimo"]:
            self.alertas.crear(
                producto_id,
                f"Stock bajo de {producto['nombre']}: {kg:.1f} kg "
                f"(mínimo {producto['stock_minimo']:.1f} kg)",
                datetime.now().isoformat(timespec="seconds"))
