"""Rutas de catalogo, detalle y administracion."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from app.models.models import Order, Product, User
from app.services.logic import (
    admin_required,
    catalog_filters,
    filter_products,
    find_product_by_public_id,
    json_response,
    list_products,
    order_payload,
    product_payload,
    user_payload,
)


bp = Blueprint("products", __name__)

ORDER_STATUSES = {"pendiente", "procesando", "enviado", "entregado", "cancelado"}


def _admin_gate():
    """Proteccion server-side para panel HTML."""
    if not g.user:
        flash("Inicia sesión para acceder al panel administrador.", "warning")
        return redirect(url_for("auth.login_page", next=url_for("products.admin_page")))
    if getattr(g.user, "role", "client") != "admin":
        flash("Acceso restringido al panel administrador.", "danger")
        return redirect(url_for("main.home"))
    return None


def _parse_price(raw_price) -> Decimal | None:
    """Convierte precio a Decimal seguro."""
    try:
        return Decimal(str(raw_price)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _create_product(data) -> tuple[bool, str, dict | None]:
    """Crea producto admin y retorna payload listo."""
    name = (data.get("name") or "").strip()
    price = _parse_price(data.get("price"))
    image = (data.get("image") or "").strip()
    description = (data.get("description") or "").strip()
    category = (data.get("category") or "Tops").strip()
    gender = (data.get("gender") or "Unisex").strip()
    sizes = (data.get("sizes") or "S,M,L,XL").strip()

    if not name or price is None or not image or not description:
        return False, "Completa los campos obligatorios del producto.", None

    product = Product(
        source_id="",
        name=name,
        price=price,
        image=image,
        description=description,
        category=category,
        gender=gender,
        sizes_csv=sizes,
        gallery_csv=image,
        colors_csv="",
    )
    g.db.add(product)
    g.db.flush()
    product.source_id = f"admin-{product.id}"
    g.db.commit()
    return True, "Producto agregado correctamente.", product_payload(product)


def _delete_product(product_id: str) -> tuple[bool, str]:
    """Elimina solo productos creados desde admin."""
    product = find_product_by_public_id(g.db, product_id)
    if not product:
        return False, "Producto no encontrado."
    if (product.source_id or "").isdigit():
        return False, "No se pueden eliminar los productos base del catálogo."

    g.db.delete(product)
    g.db.commit()
    return True, "Producto eliminado correctamente."


@bp.get("/products")
@bp.get("/catalog")
def products_page():
    """Catalogo principal con filtros."""
    search = (request.args.get("q") or "").strip()
    sel_gender = (request.args.get("gender") or "Todos").strip()
    sel_category = (request.args.get("category") or "Todas").strip()
    genders, categories = catalog_filters(g.db)

    return render_template(
        "catalog.html",
        products=filter_products(g.db, search=search, gender=sel_gender, category=sel_category),
        search=search,
        sel_gender=sel_gender if sel_gender in genders else "Todos",
        sel_category=sel_category if sel_category in categories else "Todas",
        genders=genders,
        categories=categories,
    )


@bp.get("/products/<product_id>")
def product_detail(product_id: str):
    """Detalle dinamico de un producto."""
    product = find_product_by_public_id(g.db, product_id)
    if not product:
        flash("Producto no encontrado.", "warning")
        return redirect(url_for("products.products_page"))

    payload = product_payload(product)
    related = [
        candidate
        for candidate in list_products(g.db)
        if candidate["id"] != payload["id"] and candidate["category"] == payload["category"]
    ][:4]
    return render_template("product.html", product=payload, related=related)


@bp.route("/admin", methods=["GET", "POST"])
def admin_page():
    """Panel administrativo HTML."""
    gate = _admin_gate()
    if gate:
        return gate

    if request.method == "POST":
        ok, message, _ = _create_product(request.form)
        flash(message, "success" if ok else "danger")
        return redirect(url_for("products.admin_page"))

    products = list_products(g.db)
    orders = [
        order_payload(order)
        for order in g.db.query(Order).order_by(Order.created_at.desc(), Order.id.desc()).all()
    ]
    users = {user.email: (user_payload(user) or {}) for user in g.db.query(User).order_by(User.created_at.desc()).all()}
    total_revenue = sum((Decimal(str(order.get("total", 0))) for order in orders), Decimal("0"))

    return render_template(
        "admin.html",
        products=products,
        orders=orders,
        users=users,
        total_revenue=total_revenue,
    )


@bp.post("/admin/products/<product_id>/delete")
def admin_delete_product_page(product_id: str):
    """Delete HTML para productos admin."""
    gate = _admin_gate()
    if gate:
        return gate

    ok, message = _delete_product(product_id)
    flash(message, "success" if ok else "danger")
    return redirect(url_for("products.admin_page"))


@bp.post("/admin/orders/<int:order_id>/status")
def update_order_status(order_id: int):
    """Actualiza estado del pedido desde admin."""
    gate = _admin_gate()
    if gate:
        return gate

    order = g.db.get(Order, order_id)
    status = (request.form.get("status") or "").strip().lower()
    if not order or status not in ORDER_STATUSES:
        flash("No fue posible actualizar el pedido.", "danger")
        return redirect(url_for("products.admin_page"))

    order.status = status
    g.db.commit()
    flash("Estado del pedido actualizado.", "success")
    return redirect(url_for("products.admin_page"))


@bp.post("/api/admin/products")
@admin_required
def api_admin_create_product():
    """API para crear productos desde el panel admin."""
    ok, message, product = _create_product(request.get_json(silent=True) or request.form)
    if not ok:
        return json_response(False, message=message)
    return json_response(True, message=message, product=product)


@bp.delete("/api/admin/products/<product_id>")
@admin_required
def api_admin_delete_product(product_id: str):
    """API para eliminar productos creados desde admin."""
    ok, message = _delete_product(product_id)
    return json_response(ok, message=message)
