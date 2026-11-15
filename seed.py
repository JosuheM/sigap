"""Datos de demostración anonimizados (Ley N.° 29733).

No contienen personas reales.
"""
from datetime import date, timedelta

from sigap import db
from sigap.app import Contenedor


def sembrar(ruta):
    conn = db.connect(ruta)
    db.init_db(conn)
    c = Contenedor(conn)
    if c.usuarios.por_username("admin"):
        conn.close()
        return
    c.auth.registrar("admin", "Admin#2026", "admin")
    c.auth.registrar("acopio1", "Acopio#2026", "acopiador")
    c.auth.registrar("ventas1", "Ventas#2026", "vendedor")
    papa = c.productos.crear({"nombre": "Papa nativa", "precio_base": 3.2,
                              "stock_minimo": 300})
    quinua = c.productos.crear({"nombre": "Quinua", "precio_base": 7.5,
                                "stock_minimo": 150})
    for n, (nombre, comunidad) in enumerate(
            [("Productor Anónimo 1", "Comunidad A"),
             ("Productor Anónimo 2", "Comunidad B")], start=1):
        p = c.productores.crear({"codigo": f"P-{n:04d}", "nombre": nombre,
                                 "comunidad": comunidad,
                                 "telefono": f"98765432{n}"})
        parcela = c.productores.agregar_parcela(
            p["id"], {"nombre": f"Parcela {n}", "area_ha": 1.5 * n,
                      "altitud_msnm": 3200 + 100 * n})
        hoy = date.today()
        c.acopio.registrar_lote({
            "producto_id": papa["id"], "parcela_id": parcela["id"],
            "fecha_cosecha": (hoy - timedelta(days=10 - n)).isoformat(),
            "cantidad_kg": 400 * n, "calidad": "A"})
        c.acopio.registrar_lote({
            "producto_id": quinua["id"], "parcela_id": parcela["id"],
            "fecha_cosecha": (hoy - timedelta(days=8 - n)).isoformat(),
            "cantidad_kg": 120 * n, "calidad": "B"})
    c.clientes.crear({"razon_social": "Cliente Mayorista Demo",
                      "tipo": "mayorista"})
    c.clientes.crear({"razon_social": "Cliente Minorista Demo",
                      "tipo": "minorista"})
    conn.commit()
    conn.close()


if __name__ == "__main__":
    sembrar("sigap.db")
    print("Base de datos de demostración creada: sigap.db")
