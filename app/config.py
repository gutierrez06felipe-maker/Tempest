"""
Configuracion central de la aplicacion Tempest.

BONUS exposicion:
- Conexion DB: cambia DATABASE_URL aqui (o via variable de entorno).
- Claves y credenciales iniciales: SECRET_KEY / ADMIN_EMAIL / ADMIN_PASSWORD.
"""

from __future__ import annotations

import os
from pathlib import Path


class Config:
    """Configuracion base para desarrollo y produccion."""

    BASE_DIR = Path(__file__).resolve().parent.parent
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

    # Base persistente por defecto compartida por toda la aplicacion.
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(BASE_DIR / 'database.db').as_posix()}")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@tempest.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "tempest123")
    ADMIN_INVITE_SECRET = os.getenv("ADMIN_INVITE_SECRET", "TempestAdmin2024!")
