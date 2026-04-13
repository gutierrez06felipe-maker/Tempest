# Despliegue de Tempest Commerce

## Desarrollo local

1. Crea o activa tu entorno virtual.
2. Instala dependencias:

```powershell
pip install -r requirements.txt
```

3. Ejecuta la app:

```powershell
python templates2/mientorno.py
```

La aplicacion arrancara en `http://127.0.0.1:8000` o en `http://0.0.0.0:8000` segun tu entorno.

## Base de datos

- Sin `DATABASE_URL`, la app usa `SQLite` en `templates2/instance/tempest.db`.
- En produccion, define `DATABASE_URL` con PostgreSQL.
- La app crea tablas automaticamente al arrancar.

## Usuario administrador inicial

La primera vez que inicia, se crea un admin usando:

- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`

Si no defines variables, se usan estos valores por defecto:

- Email: `admin@tempest.local`
- Contrasena: `Admin123!`

Cambialos antes de produccion.

## Render

1. Sube el proyecto a GitHub.
2. En Render crea un nuevo `Blueprint` o `Web Service`.
3. Usa el archivo `render.yaml` del repositorio.
4. Verifica estas variables:

- `SECRET_KEY`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`
- `DATABASE_URL`

5. Render te entregara una URL publica como `https://tu-app.onrender.com`.

## Railway

1. Crea un proyecto nuevo desde tu repositorio.
2. Anade un servicio PostgreSQL.
3. Configura estas variables en Railway:

- `SECRET_KEY`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`
- `DATABASE_URL`

4. Railway detectara `Procfile` y podra iniciar con `gunicorn`.
5. Publica el servicio y usa la URL publica generada.

## Paso de localhost a produccion

- Localhost solo escucha tu maquina.
- En produccion, `gunicorn` expone la app en `0.0.0.0` y el hosting la publica detras de una URL.
- La persistencia ya no queda en memoria ni en `localStorage`, sino en una base de datos compartida.
- Multiples usuarios pueden registrarse, iniciar sesion, comprar y consultar sus pedidos desde internet.
