"""Logica de negocio reutilizable para rutas Flask y Jinja."""

from __future__ import annotations

import ast
import json
import re
from decimal import Decimal
from functools import wraps
from pathlib import Path
from urllib.parse import urlparse

from flask import g, jsonify
from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash

from app.models.models import CartItem, Order, OrderItem, Product, User


def normalize_database_url(raw_url: str | None) -> str:
    """Normaliza URLs de PostgreSQL para SQLAlchemy."""
    if not raw_url:
        return ""
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+psycopg2://", 1)
    if raw_url.startswith("postgresql://"):
        return raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return raw_url


def normalize_role(raw_role: str | None) -> str:
    """Normaliza roles antiguos y nuevos a admin/client."""
    value = (raw_role or "client").strip().lower()
    if value in {"admin", "administrator"}:
        return "admin"
    if value in {"cliente", "client", "cliente "}:
        return "client"
    return "client"


def session_user_payload(user: User | None) -> dict | None:
    """Version minima del usuario para guardar en sesion."""
    if not user:
        return None
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": normalize_role(user.role),
    }


def json_response(ok: bool, **payload):
    """Respuesta JSON estandar para APIs."""
    status = 200 if ok else 400
    return jsonify({"ok": ok, **payload}), status


def login_required(func):
    """Protege rutas para usuarios autenticados."""

    @wraps(func)
    def wrapped(*args, **kwargs):
        if not g.user:
            return json_response(False, message="Debes iniciar sesion.")
        return func(*args, **kwargs)

    return wrapped


def admin_required(func):
    """Protege rutas para rol administrador."""

    @wraps(func)
    @login_required
    def wrapped(*args, **kwargs):
        if g.user.role != "admin":
            return json_response(False, message="Acceso restringido.")
        return func(*args, **kwargs)

    return wrapped


def ensure_schema(engine) -> None:
    """
    Aplica compatibilidad de columnas para bases existentes.
    """
    inspector = inspect(engine)
    expected_columns = {
        "users": {
            "name": "ALTER TABLE users ADD COLUMN name VARCHAR(120) DEFAULT 'Cliente Tempest' NOT NULL",
            "phone": "ALTER TABLE users ADD COLUMN phone VARCHAR(40) DEFAULT '' NOT NULL",
            "address": "ALTER TABLE users ADD COLUMN address TEXT DEFAULT '' NOT NULL",
        },
        "products": {
            "source_id": "ALTER TABLE products ADD COLUMN source_id VARCHAR(80) DEFAULT '' NOT NULL",
            "category": "ALTER TABLE products ADD COLUMN category VARCHAR(80) DEFAULT 'Tops' NOT NULL",
            "gender": "ALTER TABLE products ADD COLUMN gender VARCHAR(20) DEFAULT 'Unisex' NOT NULL",
            "sizes_csv": "ALTER TABLE products ADD COLUMN sizes_csv VARCHAR(120) DEFAULT 'S,M,L,XL' NOT NULL",
            "gallery_csv": "ALTER TABLE products ADD COLUMN gallery_csv TEXT DEFAULT '' NOT NULL",
            "colors_csv": "ALTER TABLE products ADD COLUMN colors_csv VARCHAR(255) DEFAULT '' NOT NULL",
        },
        "cart_items": {
            "selected_size": "ALTER TABLE cart_items ADD COLUMN selected_size VARCHAR(20) DEFAULT 'M' NOT NULL",
            "selected_color": "ALTER TABLE cart_items ADD COLUMN selected_color VARCHAR(40) DEFAULT '' NOT NULL",
        },
        "orders": {
            "payment_method": "ALTER TABLE orders ADD COLUMN payment_method VARCHAR(40) DEFAULT 'tarjeta' NOT NULL",
            "delivery_name": "ALTER TABLE orders ADD COLUMN delivery_name VARCHAR(120) DEFAULT '' NOT NULL",
            "delivery_city": "ALTER TABLE orders ADD COLUMN delivery_city VARCHAR(120) DEFAULT '' NOT NULL",
            "delivery_address": "ALTER TABLE orders ADD COLUMN delivery_address TEXT DEFAULT '' NOT NULL",
        },
        "order_items": {
            "selected_size": "ALTER TABLE order_items ADD COLUMN selected_size VARCHAR(20) DEFAULT 'M' NOT NULL",
            "selected_color": "ALTER TABLE order_items ADD COLUMN selected_color VARCHAR(40) DEFAULT '' NOT NULL",
        },
    }
    with engine.begin() as conn:
        for table_name, additions in expected_columns.items():
            if not inspector.has_table(table_name):
                continue
            current_cols = {col["name"] for col in inspect(engine).get_columns(table_name)}
            for col_name, ddl in additions.items():
                if col_name not in current_cols:
                    conn.execute(text(ddl))
        if inspector.has_table("products"):
            conn.execute(
                text("UPDATE products SET source_id = CAST(id AS TEXT) WHERE source_id IS NULL OR source_id = ''")
            )
        if inspector.has_table("users"):
            conn.execute(
                text("UPDATE users SET role = 'client' WHERE role IS NULL OR role = '' OR lower(role) = 'cliente'")
            )


def load_products_from_html_seed(html_path: Path) -> list[dict]:
    """
    Lee la constante PRODUCTS del HTML original para usarla como seed canonico.
    """
    if not html_path.exists():
        return []
    html = html_path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"const PRODUCTS\s*=\s*(\[.*?\]);", html, re.S)
    if not match:
        return []
    array_source = match.group(1)
    python_literal = re.sub(r"([\{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r"\1'\2':", array_source)
    try:
        parsed = ast.literal_eval(python_literal)
    except (ValueError, SyntaxError):
        return []
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]


def load_products_from_seed(seed_path: Path) -> list[dict]:
    """Carga el catalogo canonico desde JSON persistente."""
    if not seed_path.exists():
        return []
    try:
        data = json.loads(seed_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def seed_initial_data(db, admin_email: str, admin_password: str, seed_path: Path) -> None:
    """
    Crea usuarios base y sincroniza productos canonicos.
    """
    admin = db.query(User).filter_by(email=admin_email).first()
    if not admin:
        admin = User(name="Admin Tempest", email=admin_email, role="admin", phone="", address="")
        admin.password_hash = generate_password_hash(admin_password)
        db.add(admin)
    else:
        admin.role = "admin"

    demo_client = db.query(User).filter_by(email="cliente@tempest.com").first()
    if not demo_client:
        demo_client = User(name="Cliente Demo", email="cliente@tempest.com", role="client", phone="", address="")
        demo_client.password_hash = generate_password_hash("tempest123")
        db.add(demo_client)
    else:
        demo_client.role = "client"

    original_products = load_products_from_seed(seed_path)
    for item in original_products:
        source_id = str(item.get("id", "")).strip()
        if not source_id:
            continue
        exists = db.query(Product).filter_by(source_id=source_id).first()
        gallery = item.get("gallery") or [item.get("image", "")]
        sizes = item.get("sizes") or ["M"]
        canonical = {
            "source_id": source_id,
            "name": str(item.get("name", "")).strip(),
            "price": Decimal(str(item.get("price", "0"))),
            "image": str(item.get("image", "")).strip(),
            "description": str(item.get("description", "")).strip(),
            "category": str(item.get("category", "Tops")).strip(),
            "gender": str(item.get("gender", "Unisex")).strip(),
            "sizes_csv": ",".join(str(size).strip() for size in sizes if str(size).strip()),
            "gallery_csv": ",".join(str(url).strip() for url in gallery if str(url).strip()),
            "colors_csv": "",
        }
        if exists:
            exists.name = canonical["name"]
            exists.price = canonical["price"]
            exists.image = canonical["image"]
            exists.description = canonical["description"]
            exists.category = canonical["category"]
            exists.gender = canonical["gender"]
            exists.sizes_csv = canonical["sizes_csv"]
            exists.gallery_csv = canonical["gallery_csv"]
            exists.colors_csv = canonical["colors_csv"]
        else:
            db.add(Product(**canonical))

    db.commit()


def product_public_id(product: Product) -> str:
    """ID publico estable para URLs y formularios."""
    return product.source_id or str(product.id)


def format_price(value) -> str:
    """Formato monetario compacto en COP."""
    amount = Decimal(str(value or 0))
    amount = amount.quantize(Decimal("1")) if amount == amount.to_integral() else amount.quantize(Decimal("0.01"))
    if amount == amount.to_integral():
        return f"${int(amount):,}".replace(",", ".")
    formatted = f"{amount:,.2f}"
    return f"${formatted}".replace(",", "X").replace(".", ",").replace("X", ".")


def product_badge(product: Product) -> str:
    """Badge visual derivado del producto."""
    if product.category in {"Outerwear", "Compression"}:
        return "NUEVO"
    if product.category == "Accessories":
        return "LIMITED"
    return "ESENCIAL"


def product_features(product: Product) -> list[str]:
    """Bullets de apoyo para la vista detalle."""
    by_category = {
        "Tops": ["Tela transpirable de secado rapido", "Costuras comodas para entrenamiento intenso", "Ajuste atletico con libertad de movimiento"],
        "Bottoms": ["Elasticidad de 4 vias", "Ajuste seguro para sesiones de alto impacto", "Diseno resistente para uso diario"],
        "Compression": ["Compresion ligera para soporte muscular", "Reduce friccion durante el movimiento", "Tejido tecnico de alto rendimiento"],
        "Outerwear": ["Proteccion frente a viento y clima variable", "Capa ligera y funcional", "Construccion lista para entrenamiento exterior"],
        "Accessories": ["Diseno utilitario para uso deportivo", "Materiales durables y faciles de limpiar", "Acabado premium marca Tempest"],
    }
    return by_category.get(product.category, by_category["Tops"])


def product_payload(product: Product) -> dict:
    sizes = [s.strip() for s in (product.sizes_csv or "S,M,L,XL").split(",") if s.strip()]
    gallery = [g.strip() for g in (product.gallery_csv or product.image).split(",") if g.strip()]
    colors = []
    for raw in [c.strip() for c in (product.colors_csv or "").split(",") if c.strip()]:
        if "|" in raw:
            name, hex_color = raw.split("|", 1)
            colors.append({"name": name, "hex": hex_color})
    return {
        "id": product_public_id(product),
        "db_id": product.id,
        "name": product.name,
        "price": float(product.price),
        "image": product.image,
        "description": product.description,
        "category": product.category,
        "gender": product.gender,
        "sizes": sizes or ["S", "M", "L"],
        "gallery": gallery or [product.image],
        "colors": colors,
        "badge": product_badge(product),
        "features": product_features(product),
        "color": colors[0]["name"] if colors else "Negro",
        "is_seed": product_public_id(product).isdigit(),
    }


def cart_item_payload(item: CartItem) -> dict:
    payload = product_payload(item.product)
    payload.update(
        {
            "itemId": item.id,
            "product_id": product_public_id(item.product),
            "quantity": item.quantity,
            "qty": item.quantity,
            "size": item.selected_size,
            "selectedSize": item.selected_size,
            "selectedColor": item.selected_color or None,
        }
    )
    return payload


def order_payload(order: Order) -> dict:
    return {
        "id": order.id,
        "userId": str(order.user_id),
        "user": order.user.email if order.user else "",
        "name": order.delivery_name,
        "email": order.user.email if order.user else "",
        "status": order.status,
        "total": float(order.total),
        "paymentMethod": order.payment_method,
        "payment_method": order.payment_method,
        "city": order.delivery_city,
        "address": order.delivery_address,
        "date": order.created_at.strftime("%Y-%m-%d %H:%M"),
        "createdAt": order.created_at.isoformat(),
        "deliveryInfo": {
            "name": order.delivery_name,
            "city": order.delivery_city,
            "address": order.delivery_address,
        },
        "items": [
            {
                "id": item.product.source_id or str(item.product_id),
                "name": item.product.name,
                "price": float(item.unit_price),
                "quantity": item.quantity,
                "qty": item.quantity,
                "size": item.selected_size,
                "selectedSize": item.selected_size,
                "selectedColor": item.selected_color or None,
            }
            for item in order.items
        ],
    }


def user_payload(user: User | None) -> dict | None:
    if not user:
        return None
    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": normalize_role(user.role),
        "phone": user.phone,
        "address": user.address,
        "createdAt": user.created_at.isoformat(),
    }


def list_products(db) -> list[dict]:
    """Catalogo completo para templates y APIs."""
    products = db.query(Product).order_by(Product.created_at.desc(), Product.id.desc()).all()
    return [product_payload(product) for product in products]


def featured_products(db, limit: int = 4) -> list[dict]:
    """Subset destacado para home."""
    return list_products(db)[:limit]


def filter_products(db, search: str = "", gender: str = "Todos", category: str = "Todas") -> list[dict]:
    """Filtro de catalogo para la vista de productos."""
    needle = (search or "").strip().lower()
    selected_gender = (gender or "Todos").strip()
    selected_category = (category or "Todas").strip()
    filtered = []
    for product in list_products(db):
        matches_search = (
            not needle
            or needle in product["name"].lower()
            or needle in product["category"].lower()
            or needle in product["gender"].lower()
            or needle in product["description"].lower()
        )
        matches_gender = selected_gender == "Todos" or product["gender"] == selected_gender
        matches_category = selected_category == "Todas" or product["category"] == selected_category
        if matches_search and matches_gender and matches_category:
            filtered.append(product)
    return filtered


def catalog_filters(db) -> tuple[list[str], list[str]]:
    """Valores disponibles para sidebar de catalogo."""
    products = list_products(db)
    genders = ["Todos"] + sorted({product["gender"] for product in products})
    categories = ["Todas"] + sorted({product["category"] for product in products})
    return genders, categories


def cart_items_for_user(db, user: User | None) -> list[dict]:
    """Items del carrito listos para template."""
    if not user:
        return []
    items = db.query(CartItem).filter_by(user_id=user.id).order_by(CartItem.id.desc()).all()
    return [cart_item_payload(item) for item in items]


def cart_total(items: list[dict]) -> Decimal:
    """Total monetario del carrito."""
    return sum((Decimal(str(item.get("price", 0))) * int(item.get("qty", 0)) for item in items), Decimal("0"))


def bootstrap_payload(db, user: User | None) -> dict:
    products = list_products(db)
    cart_items = []
    orders = []
    if user:
        user = db.get(User, user.id)
        cart_items = cart_items_for_user(db, user)
        orders = [
            order_payload(order)
            for order in db.query(Order).filter_by(user_id=user.id).order_by(Order.created_at.desc()).all()
        ]
    all_users = [user_payload(item) for item in db.query(User).order_by(User.created_at.desc()).all()]
    admin_orders = [order_payload(order) for order in db.query(Order).order_by(Order.created_at.desc()).all()]
    return {
        "currentUser": user_payload(user),
        "products": products,
        "cart": cart_items,
        "orders": orders,
        "users": all_users,
        "adminOrders": admin_orders,
        "tickets": [],
    }


def find_product_by_public_id(db, raw_product_id: str) -> Product | None:
    public_id = str(raw_product_id).strip()
    if not public_id:
        return None
    product = db.query(Product).filter_by(source_id=public_id).first()
    if product:
        return product
    if public_id.isdigit():
        return db.get(Product, int(public_id))
    return None


def health_payload(database_url: str) -> dict:
    parsed = urlparse(database_url)
    return {"status": "ok", "database": parsed.scheme}
