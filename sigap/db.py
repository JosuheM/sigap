"""Acceso a SQLite y esquema de la base de datos de SIGAP."""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS usuario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    rol TEXT NOT NULL CHECK (rol IN ('admin','acopiador','vendedor'))
);
CREATE TABLE IF NOT EXISTS productor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    comunidad TEXT NOT NULL,
    telefono TEXT,
    activo INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS parcela (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    productor_id INTEGER NOT NULL REFERENCES productor(id),
    nombre TEXT NOT NULL,
    area_ha REAL NOT NULL CHECK (area_ha > 0),
    altitud_msnm INTEGER NOT NULL CHECK (altitud_msnm BETWEEN 0 AND 6500)
);
CREATE TABLE IF NOT EXISTS producto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    precio_base REAL NOT NULL CHECK (precio_base > 0),
    stock_minimo REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS lote (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL REFERENCES producto(id),
    parcela_id INTEGER NOT NULL REFERENCES parcela(id),
    fecha_cosecha TEXT NOT NULL,
    cantidad_kg REAL NOT NULL CHECK (cantidad_kg > 0),
    disponible_kg REAL NOT NULL CHECK (disponible_kg >= 0),
    calidad TEXT NOT NULL CHECK (calidad IN ('A','B','C'))
);
CREATE TABLE IF NOT EXISTS cliente (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    razon_social TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('minorista','mayorista'))
);
CREATE TABLE IF NOT EXISTS pedido (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL REFERENCES cliente(id),
    fecha TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente','confirmado','despachado','cancelado')),
    total REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS pedido_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER NOT NULL REFERENCES pedido(id),
    producto_id INTEGER NOT NULL REFERENCES producto(id),
    cantidad_kg REAL NOT NULL CHECK (cantidad_kg > 0),
    precio_unit REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS asignacion_lote (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_item_id INTEGER NOT NULL REFERENCES pedido_item(id),
    lote_id INTEGER NOT NULL REFERENCES lote(id),
    kg REAL NOT NULL CHECK (kg > 0)
);
CREATE TABLE IF NOT EXISTS alerta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL REFERENCES producto(id),
    mensaje TEXT NOT NULL,
    fecha TEXT NOT NULL
);
"""


def connect(path):
    """Abre una conexión SQLite con claves foráneas activadas."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn):
    """Crea las tablas si no existen."""
    conn.executescript(SCHEMA)
    conn.commit()
