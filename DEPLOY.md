# Despliegue de Tempest Commerce

## Desarrollo local

1. Crea o activa tu entorno virtual.
2. Instala dependencias:

```powershell
pip install -r requirements.txt
```

3. Ejecuta la app:

```powershell
python run.py
```

La aplicacion arrancara en `http://127.0.0.1:5000` o `http://0.0.0.0:5000`.

## Base de datos

- Sin `DATABASE_URL`, la app usa `SQLite` en `database.db`.
- En produccion, Render inyecta `DATABASE_URL` y la app la normaliza para `Flask-SQLAlchemy`.
- La app crea tablas automaticamente al arrancar y hace seed inicial del catalogo.
- El catalogo canonico vive en `app/data/products_seed.json` y se sincroniza a la tabla `products`.

## Usuario administrador inicial

La primera vez que inicia, se crea un admin usando:

- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`

Si no defines variables, se usan estos valores por defecto:

- Email: `admin@tempest.com`
- Contrasena: `tempest123`

Cambialos antes de produccion.

## Render

1. Sube el proyecto a GitHub.
2. En Render crea un nuevo `Blueprint` o `Web Service`.
3. Usa el archivo `render.yaml` del repositorio.
4. Verifica que el `startCommand` sea:

```bash
gunicorn run:app
```

5. Verifica estas variables:

- `SECRET_KEY`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`
- `ADMIN_INVITE_SECRET`
- `DATABASE_URL`

6. Render te entregara una URL publica como `https://tu-app.onrender.com`.

## Railway

1. Crea un proyecto nuevo desde tu repositorio.
2. Anade un servicio PostgreSQL.
3. Configura estas variables en Railway:

- `SECRET_KEY`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`
- `ADMIN_INVITE_SECRET`
- `DATABASE_URL`

4. Railway detectara `Procfile` y podra iniciar con:

```bash
gunicorn run:app
```

5. Publica el servicio y usa la URL publica generada.

## Paso de localhost a produccion

- `localhost` solo escucha tu maquina.
- En produccion, `gunicorn` expone la app en `0.0.0.0` y el hosting publica la URL.
- La persistencia queda en base de datos compartida con `Flask-SQLAlchemy`.
- Multiples usuarios pueden registrarse, iniciar sesion, comprar y ver pedidos en tiempo real.
