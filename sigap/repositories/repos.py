"""Repositorios concretos de SIGAP."""
from .base import RepositorioBase


class UsuarioRepo(RepositorioBase):
    tabla = "usuario"

    def crear(self, username, password_hash, rol):
        return self._insertar(("username", "password_hash", "rol"),
                              (username, password_hash, rol))

    def por_username(self, username):
        fila = self.conn.execute(
            "SELECT * FROM usuario WHERE username = ?", (username,)
        ).fetchone()
        return dict(fila) if fila else None


class ProductorRepo(RepositorioBase):
    tabla = "productor"

    def crear(self, codigo, nombre, comunidad, telefono):
        return self._insertar(("codigo", "nombre", "comunidad", "telefono"),
                              (codigo, nombre, comunidad, telefono))

    def actualizar(self, id_, nombre, comunidad, telefono, activo):
        self.conn.execute(
            "UPDATE productor SET nombre=?, comunidad=?, telefono=?, activo=? "
            "WHERE id=?", (nombre, comunidad, telefono, int(activo), id_))

    def por_codigo(self, codigo):
        fila = self.conn.execute(
            "SELECT * FROM productor WHERE codigo = ?", (codigo,)).fetchone()
        return dict(fila) if fila else None


class ParcelaRepo(RepositorioBase):
    tabla = "parcela"

    def crear(self, productor_id, nombre, area_ha, altitud_msnm):
        return self._insertar(
            ("productor_id", "nombre", "area_ha", "altitud_msnm"),
            (productor_id, nombre, area_ha, altitud_msnm))

    def de_productor(self, productor_id):
        filas = self.conn.execute(
            "SELECT * FROM parcela WHERE productor_id = ? ORDER BY id",
            (productor_id,)).fetchall()
        return [dict(f) for f in filas]


class ProductoRepo(RepositorioBase):
    tabla = "producto"

    def crear(self, nombre, precio_base, stock_minimo):
        return self._insertar(("nombre", "precio_base", "stock_minimo"),
                              (nombre, precio_base, stock_minimo))

    def stock_disponible(self, producto_id):
        fila = self.conn.execute(
            "SELECT COALESCE(SUM(disponible_kg), 0) AS kg FROM lote "
            "WHERE producto_id = ?", (producto_id,)).fetchone()
        return float(fila["kg"])


class LoteRepo(RepositorioBase):
    tabla = "lote"

    def crear(self, producto_id, parcela_id, fecha_cosecha, cantidad_kg,
              calidad):
        return self._insertar(
            ("producto_id", "parcela_id", "fecha_cosecha", "cantidad_kg",
             "disponible_kg", "calidad"),
            (producto_id, parcela_id, fecha_cosecha, cantidad_kg,
             cantidad_kg, calidad))

    def fifo(self, producto_id):
        """Lotes con stock, del más antiguo al más reciente (FIFO)."""
        filas = self.conn.execute(
            "SELECT * FROM lote WHERE producto_id = ? AND disponible_kg > 0 "
            "ORDER BY fecha_cosecha, id", (producto_id,)).fetchall()
        return [dict(f) for f in filas]

    def descontar(self, lote_id, kg):
        self.conn.execute(
            "UPDATE lote SET disponible_kg = disponible_kg - ? WHERE id = ?",
            (kg, lote_id))

    def reponer(self, lote_id, kg):
        self.conn.execute(
            "UPDATE lote SET disponible_kg = disponible_kg + ? WHERE id = ?",
            (kg, lote_id))


class ClienteRepo(RepositorioBase):
    tabla = "cliente"

    def crear(self, razon_social, tipo):
        return self._insertar(("razon_social", "tipo"), (razon_social, tipo))


class PedidoRepo(RepositorioBase):
    tabla = "pedido"

    def crear(self, cliente_id, fecha):
        return self._insertar(("cliente_id", "fecha"), (cliente_id, fecha))

    def agregar_item(self, pedido_id, producto_id, cantidad_kg, precio_unit):
        cur = self.conn.execute(
            "INSERT INTO pedido_item (pedido_id, producto_id, cantidad_kg, "
            "precio_unit) VALUES (?, ?, ?, ?)",
            (pedido_id, producto_id, cantidad_kg, precio_unit))
        return cur.lastrowid

    def items(self, pedido_id):
        filas = self.conn.execute(
            "SELECT * FROM pedido_item WHERE pedido_id = ? ORDER BY id",
            (pedido_id,)).fetchall()
        return [dict(f) for f in filas]

    def fijar_total(self, pedido_id, total):
        self.conn.execute("UPDATE pedido SET total = ? WHERE id = ?",
                          (round(total, 2), pedido_id))

    def cambiar_estado(self, pedido_id, estado):
        self.conn.execute("UPDATE pedido SET estado = ? WHERE id = ?",
                          (estado, pedido_id))

    def registrar_asignacion(self, item_id, lote_id, kg):
        self.conn.execute(
            "INSERT INTO asignacion_lote (pedido_item_id, lote_id, kg) "
            "VALUES (?, ?, ?)", (item_id, lote_id, kg))

    def asignaciones(self, pedido_id):
        filas = self.conn.execute(
            "SELECT a.lote_id, a.kg, i.producto_id, l.fecha_cosecha, "
            "l.calidad, pa.nombre AS parcela, pr.codigo AS productor "
            "FROM asignacion_lote a "
            "JOIN pedido_item i ON i.id = a.pedido_item_id "
            "JOIN lote l ON l.id = a.lote_id "
            "JOIN parcela pa ON pa.id = l.parcela_id "
            "JOIN productor pr ON pr.id = pa.productor_id "
            "WHERE i.pedido_id = ? ORDER BY a.id", (pedido_id,)).fetchall()
        return [dict(f) for f in filas]

    def borrar_asignaciones(self, pedido_id):
        self.conn.execute(
            "DELETE FROM asignacion_lote WHERE pedido_item_id IN "
            "(SELECT id FROM pedido_item WHERE pedido_id = ?)", (pedido_id,))


class AlertaRepo(RepositorioBase):
    tabla = "alerta"

    def crear(self, producto_id, mensaje, fecha):
        return self._insertar(("producto_id", "mensaje", "fecha"),
                              (producto_id, mensaje, fecha))
