"""Módulo 1: productores, parcelas y productos."""
from ..errors import ErrorDominio, NoEncontrado
from ..domain import validation as v


class ServicioProductores:
    def __init__(self, productores, parcelas):
        self.productores = productores
        self.parcelas = parcelas

    def crear(self, datos):
        v.requerido(datos, ("codigo", "nombre", "comunidad"))
        v.codigo_valido(datos["codigo"])
        v.telefono_valido(datos.get("telefono"))
        if self.productores.por_codigo(datos["codigo"]):
            raise ErrorDominio("El código de productor ya existe", 409)
        id_ = self.productores.crear(datos["codigo"], datos["nombre"],
                                     datos["comunidad"], datos.get("telefono"))
        return self.productores.obtener(id_)

    def obtener(self, id_):
        productor = self.productores.obtener(id_)
        if not productor:
            raise NoEncontrado("Productor no encontrado")
        productor["parcelas"] = self.parcelas.de_productor(id_)
        return productor

    def actualizar(self, id_, datos):
        actual = self.productores.obtener(id_)
        if not actual:
            raise NoEncontrado("Productor no encontrado")
        v.telefono_valido(datos.get("telefono", actual["telefono"]))
        self.productores.actualizar(
            id_, datos.get("nombre", actual["nombre"]),
            datos.get("comunidad", actual["comunidad"]),
            datos.get("telefono", actual["telefono"]),
            datos.get("activo", actual["activo"]))
        return self.productores.obtener(id_)

    def agregar_parcela(self, productor_id, datos):
        if not self.productores.obtener(productor_id):
            raise NoEncontrado("Productor no encontrado")
        v.requerido(datos, ("nombre", "area_ha", "altitud_msnm"))
        area = v.numero_positivo(datos["area_ha"], "area_ha")
        altitud = int(v.numero_positivo(datos["altitud_msnm"], "altitud_msnm"))
        if altitud > 6500:
            raise ErrorDominio("Altitud fuera de rango")
        id_ = self.parcelas.crear(productor_id, datos["nombre"], area, altitud)
        return self.parcelas.obtener(id_)


class ServicioProductos:
    def __init__(self, productos):
        self.productos = productos

    def crear(self, datos):
        v.requerido(datos, ("nombre", "precio_base"))
        precio = v.numero_positivo(datos["precio_base"], "precio_base")
        minimo = float(datos.get("stock_minimo", 0))
        if minimo < 0:
            raise ErrorDominio("stock_minimo no puede ser negativo")
        id_ = self.productos.crear(datos["nombre"], precio, minimo)
        return self.productos.obtener(id_)
