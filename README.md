# Tempest - Flask E-commerce (Arquitectura Modular)

Proyecto reorganizado para una presentacion academica, con estructura limpia y facil de navegar.

## Estructura principal

```text
tempest/
|-- app/
|   |-- __init__.py          # Fabrica Flask (create_app)
|   |-- config.py            # Configuracion (SECRET_KEY, DATABASE_URL, etc.)
|   |-- routes/              # Endpoints separados por dominio
|   |   |-- main.py
|   |   |-- auth.py
|   |   |-- products.py
|   |   `-- cart.py
|   |-- models/
|   |   `-- models.py        # Tablas SQLAlchemy
|   |-- services/
|   |   `-- logic.py         # Logica de negocio reutilizable
|   |-- templates/           # HTML (incluye tempest.html original)
|   `-- static/
|       |-- css/
|       |-- js/
|       `-- img/
|-- run.py                   # Entrada principal (gunicorn run:app)
|-- requirements.txt
|-- Procfile
`-- render.yaml
```

## Como ejecutar en local

```powershell
pip install -r requirements.txt
python run.py
```

## Donde cambiar cosas rapido (para exposicion)

- Rutas backend: `app/routes/*.py`
- Logica del carrito y checkout: `app/routes/cart.py`
- Autenticacion y sesiones: `app/routes/auth.py`
- Modelos/tablas DB: `app/models/models.py`
- Conexion a base de datos: `app/config.py` (`DATABASE_URL`)
- Seed inicial de productos desde HTML: `app/services/logic.py` (`seed_initial_data`)
- Colores y look visual: `app/templates/tempest.html` (variables CSS y estilos existentes)
- JS puente frontend-backend: `app/static/js/backend-bridge.js`

## Produccion (Render/Railway)

- Comando de inicio: `gunicorn run:app`
- Variables recomendadas:
  - `SECRET_KEY`
  - `DATABASE_URL` (PostgreSQL en produccion)
  - `ADMIN_EMAIL`
  - `ADMIN_PASSWORD`

Con eso la app deja de ser solo localhost y queda publica con URL global.
