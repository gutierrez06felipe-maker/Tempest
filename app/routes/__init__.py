"""Registro central de blueprints para la aplicacion Flask."""

from app.routes.auth import bp as auth_bp
from app.routes.cart import bp as cart_bp
from app.routes.main import bp as main_bp
from app.routes.products import bp as products_bp


ALL_BLUEPRINTS = (
    main_bp,
    auth_bp,
    products_bp,
    cart_bp,
)

__all__ = ["ALL_BLUEPRINTS", "main_bp", "auth_bp", "products_bp", "cart_bp"]
