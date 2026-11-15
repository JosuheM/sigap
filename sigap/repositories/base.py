"""Patrón Repository: acceso a datos con consultas parametrizadas."""


TABLAS = frozenset({
    "usuario", "productor", "parcela", "producto", "lote", "cliente",
    "pedido", "alerta"})


class RepositorioBase:
    """El nombre de tabla proviene de una lista cerrada (nunca del usuario);
    los valores siempre viajan como parámetros enlazados."""

    tabla = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.tabla is not None and cls.tabla not in TABLAS:
            raise ValueError(f"Tabla no permitida: {cls.tabla}")

    def __init__(self, conn):
        self.conn = conn

    def obtener(self, id_):
        fila = self.conn.execute(
            f"SELECT * FROM {self.tabla} WHERE id = ?", (id_,)  # nosec B608
        ).fetchone()
        return dict(fila) if fila else None

    def listar(self):
        filas = self.conn.execute(
            f"SELECT * FROM {self.tabla} ORDER BY id"  # nosec B608
        ).fetchall()
        return [dict(f) for f in filas]

    def _insertar(self, campos, valores):
        marcas = ", ".join("?" for _ in campos)
        cur = self.conn.execute(
            f"INSERT INTO {self.tabla} ({', '.join(campos)}) "  # nosec B608
            f"VALUES ({marcas})",
            valores,
        )
        return cur.lastrowid
