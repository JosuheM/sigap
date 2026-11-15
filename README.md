# SIGAP – Sistema de Información para la Gestión de Acopio y Pedidos

Repositorio: https://github.com/JosuheM/sigap


Proyecto de Ingeniería de Software (SIS021, 2026-II, UAC). Caso verosímil: APAVS
(Asociación de Productores Agroecológicos del Valle Sagrado). Todos los datos de
demostración son ficticios y anonimizados (Ley N.° 29733).

## Requisitos
Python 3.11 o superior. Sin servicios externos (SGBD: SQLite incluido).

## Instalación y ejecución
    python -m venv .venv
    source .venv/bin/activate          # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    python run.py                      # http://127.0.0.1:5000

Usuarios de demostración (cámbielos antes de usar datos reales):
admin / Admin#2026, acopio1 / Acopio#2026, ventas1 / Ventas#2026.
Variables de entorno: SIGAP_DB (ruta de la base), SIGAP_SECRET (clave de sesión,
obligatoria en producción), SIGAP_HTTPS=1 (cookie Secure).

## Pruebas y calidad
    pytest                                   # 74 pruebas
    pytest -m aceptacion                     # por tipo: integracion, regresion, seguridad, rendimiento
    pytest --cov=sigap --cov-branch          # cobertura
    flake8 sigap tests --max-line-length=79
    radon cc sigap -s -a ; radon mi sigap -s
    bandit -r sigap

## Estructura
sigap/ (app, db, errors, domain, repositories, services, static) · tests/ · docs/ · .github/workflows/ci.yml

## API (resumen)
POST /api/auth/login | /api/auth/logout · POST /api/usuarios (admin)
GET/POST /api/productores · GET/PUT /api/productores/<id> · POST /api/productores/<id>/parcelas
GET/POST /api/productos · POST /api/lotes · GET /api/stock · GET /api/alertas
GET/POST /api/clientes · GET/POST /api/pedidos · GET /api/pedidos/<id>
POST /api/pedidos/<id>/confirmar | despachar | cancelar
GET /api/reportes/ventas · GET /api/reportes/trazabilidad/<pedido_id>
