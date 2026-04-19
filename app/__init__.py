"""
Fabrica principal de la aplicacion Flask Tempest.

Este archivo inicializa:
- Configuracion
- Conexion DB
- Contexto por request (g.db / g.user)
- Blueprints de rutas
"""

from __future__ import annotations

from pathlib import Path

from flask import Flask, g, session

from app.config import Config
from app.models import CartItem, User, db
from app.routes import ALL_BLUEPRINTS
from app.services.logic import (
    ensure_schema,
    format_price,
    normalize_database_url,
    normalize_role,
    seed_initial_data,
    session_user_payload,
)


def create_app() -> Flask:
    """Crea y configura la aplicacion Flask."""
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)

    # Normalizamos la URL por si Render la entrega como postgres://...
    normalized_db_url = normalize_database_url(app.config.get("DATABASE_URL"))
    app.config["DATABASE_URL"] = normalized_db_url
    app.config["SQLALCHEMY_DATABASE_URI"] = normalized_db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    engine_options = dict(app.config.get("SQLALCHEMY_ENGINE_OPTIONS") or {})
    if normalized_db_url.startswith("sqlite"):
        engine_options["connect_args"] = {"check_same_thread": False}
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options

    db.init_app(app)

    with app.app_context():
        db.create_all()
        ensure_schema(db.engine)
        seed_initial_data(
            db.session,
            app.config["ADMIN_EMAIL"],
            app.config["ADMIN_PASSWORD"],
            seed_path=(Path(app.root_path) / "data" / "products_seed.json"),
        )

    @app.before_request
    def load_request_context():
        """Abre sesion DB y carga usuario autenticado para cada request."""
        g.db = db.session
        g.user = None
        user_id = session.get("user_id")
        if user_id:
            g.user = g.db.get(User, user_id)
            if g.user:
                normalized_role = normalize_role(g.user.role)
                if normalized_role != g.user.role:
                    g.user.role = normalized_role
                    g.db.commit()
                session["user"] = session_user_payload(g.user)
                session["user_email"] = g.user.email
            else:
                session.pop("user_id", None)
                session.pop("user", None)
                session.pop("user_email", None)

    @app.template_filter("fmt_price")
    @app.template_filter("currency")
    def price_filter(value):
        """Formato monetario consistente para toda la tienda."""
        return format_price(value)

    @app.context_processor
    def inject_template_helpers():
        """Datos globales seguros para navbar y templates."""
        current_user = session.get("user") or session_user_payload(getattr(g, "user", None))
        cart_count = 0
        if getattr(g, "db", None) is not None and getattr(g, "user", None) is not None:
            cart_count = g.db.query(CartItem).filter_by(user_id=g.user.id).count()
        return {
            "current_user": lambda: current_user,
            "get_cart_count": lambda: cart_count,
            "session_user": current_user,
        }

    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)

    return app
