import os
import re
import ast
from datetime import datetime
from decimal import Decimal
from functools import wraps
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, g, jsonify, render_template, request, session
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)


def normalize_database_url(raw_url: str | None) -> str:
    if not raw_url:
        return f"sqlite:///{(INSTANCE_DIR / 'tempest.db').as_posix()}"
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+psycopg2://", 1)
    if raw_url.startswith("postgresql://"):
        return raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return raw_url


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), default="Cliente Tempest", nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="cliente", nullable=False)
    phone: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    address: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    cart_items: Mapped[list["CartItem"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(80), default="", nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    image: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str] = mapped_column(String(80), default="Tops", nullable=False)
    gender: Mapped[str] = mapped_column(String(20), default="Unisex", nullable=False)
    sizes_csv: Mapped[str] = mapped_column(String(120), default="S,M,L,XL", nullable=False)
    gallery_csv: Mapped[str] = mapped_column(Text, default="", nullable=False)
    colors_csv: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    cart_items: Mapped[list["CartItem"]] = relationship(back_populates="product")
    order_items: Mapped[list["OrderItem"]] = relationship(back_populates="product")


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    selected_size: Mapped[str] = mapped_column(String(20), default="M", nullable=False)
    selected_color: Mapped[str] = mapped_column(String(40), default="", nullable=False)

    user: Mapped[User] = relationship(back_populates="cart_items")
    product: Mapped[Product] = relationship(back_populates="cart_items")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="pendiente", nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(40), default="tarjeta", nullable=False)
    delivery_name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    delivery_city: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    delivery_address: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    selected_size: Mapped[str] = mapped_column(String(20), default="M", nullable=False)
    selected_color: Mapped[str] = mapped_column(String(40), default="", nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product] = relationship(back_populates="order_items")


def create_app() -> Flask:
    app = Flask(__name__, template_folder=str(BASE_DIR))
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me-in-production")
    app.config["SQLALCHEMY_DATABASE_URI"] = normalize_database_url(os.getenv("DATABASE_URL"))
    app.config["ADMIN_EMAIL"] = os.getenv("ADMIN_EMAIL", "admin@tempest.com")
    app.config["ADMIN_PASSWORD"] = os.getenv("ADMIN_PASSWORD", "tempest123")
    app.config["ADMIN_INVITE_SECRET"] = os.getenv("ADMIN_INVITE_SECRET", "TempestAdmin2024!")

    connect_args = {}
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"], future=True, connect_args=connect_args)
    SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False))

    def json_response(ok: bool, **payload):
        status = 200 if ok else 400
        return jsonify({"ok": ok, **payload}), status

    def ensure_schema() -> None:
        Base.metadata.create_all(engine)
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
                conn.execute(text("UPDATE products SET source_id = CAST(id AS TEXT) WHERE source_id IS NULL OR source_id = ''"))

    def load_products_from_html_seed() -> list[dict]:
        html_path = BASE_DIR / "tempest.html"
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

    def find_product_by_public_id(raw_product_id: str) -> Product | None:
        public_id = str(raw_product_id).strip()
        if not public_id:
            return None
        product = g.db.query(Product).filter_by(source_id=public_id).first()
        if product:
            return product
        if public_id.isdigit():
            return g.db.get(Product, int(public_id))
        return None

    def product_payload(product: Product) -> dict:
        sizes = [s.strip() for s in (product.sizes_csv or "S,M,L,XL").split(",") if s.strip()]
        gallery = [g.strip() for g in (product.gallery_csv or product.image).split(",") if g.strip()]
        colors = []
        for raw in [c.strip() for c in (product.colors_csv or "").split(",") if c.strip()]:
            if "|" in raw:
                name, hex_color = raw.split("|", 1)
                colors.append({"name": name, "hex": hex_color})
        return {
            "id": product.source_id or str(product.id),
            "name": product.name,
            "price": float(product.price),
            "image": product.image,
            "description": product.description,
            "category": product.category,
            "gender": product.gender,
            "sizes": sizes or ["S", "M", "L"],
            "gallery": gallery or [product.image],
            "colors": colors,
        }

    def cart_item_payload(item: CartItem) -> dict:
        payload = product_payload(item.product)
        payload.update(
            {
                "quantity": item.quantity,
                "selectedSize": item.selected_size,
                "selectedColor": item.selected_color or None,
            }
        )
        return payload

    def order_payload(order: Order) -> dict:
        return {
            "id": str(order.id),
            "userId": str(order.user_id),
            "status": order.status,
            "total": float(order.total),
            "paymentMethod": order.payment_method,
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
            "role": user.role,
            "phone": user.phone,
            "address": user.address,
            "createdAt": user.created_at.isoformat(),
        }

    def bootstrap_payload(db_session, user: User | None) -> dict:
        products = [product_payload(product) for product in db_session.query(Product).order_by(Product.created_at.desc()).all()]
        cart_items = []
        orders = []
        if user:
            user = db_session.get(User, user.id)
            cart_items = [cart_item_payload(item) for item in user.cart_items]
            orders = [order_payload(order) for order in db_session.query(Order).filter_by(user_id=user.id).order_by(Order.created_at.desc()).all()]
        all_users = [user_payload(item) for item in db_session.query(User).order_by(User.created_at.desc()).all()]
        admin_orders = [order_payload(order) for order in db_session.query(Order).order_by(Order.created_at.desc()).all()]
        return {
            "currentUser": user_payload(user),
            "products": products,
            "cart": cart_items,
            "orders": orders,
            "users": all_users,
            "adminOrders": admin_orders,
            "tickets": [],
        }

    def login_required(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            if not g.user:
                return json_response(False, message="Debes iniciar sesion.")
            return func(*args, **kwargs)

        return wrapped

    def admin_required(func):
        @wraps(func)
        @login_required
        def wrapped(*args, **kwargs):
            if g.user.role != "admin":
                return json_response(False, message="Acceso restringido.")
            return func(*args, **kwargs)

        return wrapped

    @app.before_request
    def load_context():
        g.db = SessionLocal()
        g.user = None
        user_id = session.get("user_id")
        if user_id:
            g.user = g.db.get(User, user_id)

    @app.teardown_request
    def cleanup(exception=None):
        db = getattr(g, "db", None)
        if db is not None:
            if exception:
                db.rollback()
            db.close()
        SessionLocal.remove()

    def seed_initial_data() -> None:
        db = SessionLocal()
        try:
            admin = db.query(User).filter_by(email=app.config["ADMIN_EMAIL"]).first()
            if not admin:
                admin = User(name="Admin Tempest", email=app.config["ADMIN_EMAIL"], role="admin", phone="", address="")
                admin.set_password(app.config["ADMIN_PASSWORD"])
                db.add(admin)

            demo_client = db.query(User).filter_by(email="cliente@tempest.com").first()
            if not demo_client:
                demo_client = User(name="Cliente Demo", email="cliente@tempest.com", role="cliente", phone="", address="")
                demo_client.set_password("tempest123")
                db.add(demo_client)

            original_products = load_products_from_html_seed()
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
        finally:
            db.close()

    def render_store(page_name: str):
        html = render_template("tempest.html")
        script_tag = '<script src="/static/backend-bridge.js"></script>'
        if script_tag not in html and "</body>" in html:
            html = html.replace("</body>", f"{script_tag}\n</body>", 1)
        return html

    @app.get("/")
    def index():
        return render_store("home")

    @app.get("/products")
    def products():
        return render_store("catalog")

    @app.get("/login")
    def login_page():
        return render_store("login")

    @app.get("/register")
    def register_page():
        return render_store("register")

    @app.get("/cart")
    def cart_page():
        return render_store("cart")

    @app.get("/checkout")
    def checkout_page():
        return render_store("checkout")

    @app.get("/admin")
    def admin_page():
        return render_store("admin")

    @app.get("/orders")
    def orders_page():
        return render_store("orders")

    @app.post("/api/login")
    def api_login():
        data = request.get_json(silent=True) or request.form
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        user = g.db.query(User).filter_by(email=email).first()
        if not user or not user.check_password(password):
            return json_response(False, message="Credenciales invalidas.")
        session.clear()
        session["user_id"] = user.id
        return json_response(True, message="Sesion iniciada.", user=user_payload(user))

    @app.post("/api/register")
    def api_register():
        data = request.get_json(silent=True) or request.form
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        role = data.get("role") or "cliente"
        phone = (data.get("phone") or "").strip()
        address = (data.get("address") or "").strip()
        admin_pass = data.get("adminPass") or ""

        if not name or not email or not password:
            return json_response(False, message="Completa los campos obligatorios.")
        if g.db.query(User).filter_by(email=email).first():
            return json_response(False, message="Ese email ya esta registrado.")
        if role == "admin" and admin_pass != app.config["ADMIN_INVITE_SECRET"]:
            return json_response(False, message="Contrasena de administrador incorrecta.")

        user = User(name=name, email=email, role=role, phone=phone, address=address)
        user.set_password(password)
        g.db.add(user)
        g.db.commit()
        session.clear()
        session["user_id"] = user.id
        return json_response(True, message="Cuenta creada.", user=user_payload(user))

    @app.post("/api/logout")
    def api_logout():
        session.clear()
        return json_response(True, message="Sesion cerrada.")

    @app.get("/api/bootstrap")
    def api_bootstrap():
        return jsonify(bootstrap_payload(g.db, g.user))

    @app.post("/api/cart/add")
    @login_required
    def api_cart_add():
        data = request.get_json(silent=True) or request.form
        product_id = str(data.get("productId") or "").strip()
        selected_size = (data.get("selectedSize") or "M").strip()
        selected_color = (data.get("selectedColor") or "").strip()
        quantity = max(1, int(data.get("quantity") or 1))
        product = find_product_by_public_id(product_id)
        if not product:
            return json_response(False, message="Producto no encontrado.")
        item = (
            g.db.query(CartItem)
            .filter_by(
                user_id=g.user.id,
                product_id=product.id,
                selected_size=selected_size,
                selected_color=selected_color,
            )
            .first()
        )
        if item:
            item.quantity += quantity
        else:
            item = CartItem(
                user_id=g.user.id,
                product_id=product.id,
                quantity=quantity,
                selected_size=selected_size,
                selected_color=selected_color,
            )
            g.db.add(item)
        g.db.commit()
        return json_response(True, message="Producto agregado al carrito.")

    @app.post("/api/cart/remove")
    @login_required
    def api_cart_remove():
        data = request.get_json(silent=True) or request.form
        product_id = str(data.get("productId") or "").strip()
        selected_size = (data.get("selectedSize") or "M").strip()
        selected_color = (data.get("selectedColor") or "").strip()
        product = find_product_by_public_id(product_id)
        if not product:
            return json_response(False, message="Producto no encontrado en el carrito.")
        item = (
            g.db.query(CartItem)
            .filter_by(
                user_id=g.user.id,
                product_id=product.id,
                selected_size=selected_size,
                selected_color=selected_color,
            )
            .first()
        )
        if not item:
            return json_response(False, message="Producto no encontrado en el carrito.")
        g.db.delete(item)
        g.db.commit()
        return json_response(True, message="Producto eliminado.")

    @app.post("/api/checkout")
    @login_required
    def api_checkout():
        data = request.get_json(silent=True) or request.form
        name = (data.get("name") or "").strip()
        city = (data.get("city") or "").strip()
        address = (data.get("address") or "").strip()
        payment_method = (data.get("paymentMethod") or "tarjeta").strip()
        if not name or not city or not address:
            return json_response(False, message="Completa los datos de entrega.")

        items = g.db.query(CartItem).filter_by(user_id=g.user.id).all()
        if not items:
            return json_response(False, message="Tu carrito esta vacio.")

        extra = Decimal("5000") if payment_method == "contraentrega" else Decimal("0")
        total = sum((item.product.price * item.quantity for item in items), Decimal("0")) + extra
        order = Order(
            user_id=g.user.id,
            status="pendiente",
            total=total,
            payment_method=payment_method,
            delivery_name=name,
            delivery_city=city,
            delivery_address=address,
        )
        g.db.add(order)
        g.db.flush()
        for item in items:
            g.db.add(
                OrderItem(
                    order_id=order.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_price=item.product.price,
                    selected_size=item.selected_size,
                    selected_color=item.selected_color,
                )
            )
            g.db.delete(item)
        g.user.name = name or g.user.name
        g.user.address = address or g.user.address
        g.db.commit()
        return json_response(True, message="Pedido creado.", order=order_payload(order))

    @app.post("/api/admin/products")
    @admin_required
    def api_admin_create_product():
        data = request.get_json(silent=True) or request.form
        name = (data.get("name") or "").strip()
        price = data.get("price") or ""
        image = (data.get("image") or "").strip()
        description = (data.get("description") or "").strip()
        category = (data.get("category") or "Tops").strip()
        gender = (data.get("gender") or "Unisex").strip()
        sizes = (data.get("sizes") or "S,M,L,XL").strip()
        if not name or not price or not image or not description:
            return json_response(False, message="Completa los campos obligatorios.")
        product = Product(
            source_id="",
            name=name,
            price=Decimal(str(price)),
            image=image,
            description=description,
            category=category,
            gender=gender,
            sizes_csv=sizes,
            gallery_csv=image,
        )
        g.db.add(product)
        g.db.flush()
        product.source_id = f"admin-{product.id}"
        g.db.commit()
        return json_response(True, message="Producto agregado.", product=product_payload(product))

    @app.delete("/api/admin/products/<product_id>")
    @admin_required
    def api_admin_delete_product(product_id: str):
        product = find_product_by_public_id(product_id)
        if not product:
            return json_response(False, message="Producto no encontrado.")
        if product.source_id.isdigit():
            return json_response(False, message="No se pueden eliminar los productos base del catalogo.")
        g.db.delete(product)
        g.db.commit()
        return json_response(True, message="Producto eliminado.")

    @app.get("/health")
    def health():
        parsed = urlparse(app.config["SQLALCHEMY_DATABASE_URI"])
        return {"status": "ok", "database": parsed.scheme, "time": datetime.utcnow().isoformat()}

    ensure_schema()
    seed_initial_data()
    return app


app = create_app()


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)
    import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
