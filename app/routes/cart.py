"""Rutas de carrito, checkout y pedidos."""

from __future__ import annotations

from decimal import Decimal

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from sqlalchemy.exc import SQLAlchemyError

from app.models.models import CartItem, Order, OrderItem
from app.services.logic import (
    cart_items_for_user,
    cart_total,
    find_product_by_public_id,
    json_response,
    login_required,
    order_payload,
    user_payload,
)


bp = Blueprint("cart", __name__)

PAYMENT_METHODS = {"tarjeta", "nequi", "pse", "contraentrega"}


def _safe_int(raw_value, default: int = 1) -> int:
    """Convierte enteros de formularios sin lanzar excepciones."""
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return default


def _login_page_redirect(target_endpoint: str):
    """Redirecciona a login conservando el destino original."""
    flash("Debes iniciar sesión para continuar.", "warning")
    return redirect(url_for("auth.login_page", next=url_for(target_endpoint)))


def _add_to_cart(data) -> tuple[bool, str]:
    """Agrega o acumula items en el carrito."""
    try:
        product_id = str(data.get("productId") or data.get("product_id") or "").strip()
        selected_size = (data.get("selectedSize") or data.get("size") or "M").strip()
        selected_color = (data.get("selectedColor") or data.get("color") or "").strip()
        quantity = max(1, _safe_int(data.get("quantity") or data.get("qty") or 1, default=1))

        product = find_product_by_public_id(g.db, product_id)
        if not product:
            return False, "Producto no encontrado."

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
            g.db.add(
                CartItem(
                    user_id=g.user.id,
                    product_id=product.id,
                    quantity=quantity,
                    selected_size=selected_size,
                    selected_color=selected_color,
                )
            )
        g.db.commit()
        return True, "Producto agregado al carrito."
    except SQLAlchemyError:
        g.db.rollback()
        return False, "No fue posible actualizar el carrito."
    except Exception:
        g.db.rollback()
        return False, "Ocurrio un error inesperado al agregar el producto."


def _remove_from_cart(data) -> tuple[bool, str]:
    """Elimina un item puntual del carrito."""
    try:
        product_id = str(data.get("productId") or data.get("product_id") or "").strip()
        selected_size = (data.get("selectedSize") or data.get("size") or "M").strip()
        selected_color = (data.get("selectedColor") or data.get("color") or "").strip()

        product = find_product_by_public_id(g.db, product_id)
        if not product:
            return False, "Producto no encontrado en el carrito."

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
            return False, "Producto no encontrado en el carrito."

        g.db.delete(item)
        g.db.commit()
        return True, "Producto eliminado del carrito."
    except SQLAlchemyError:
        g.db.rollback()
        return False, "No fue posible actualizar el carrito."
    except Exception:
        g.db.rollback()
        return False, "Ocurrio un error inesperado al eliminar el item."


def _update_cart_item(data) -> tuple[bool, str]:
    """Actualiza la cantidad o elimina el item si queda en cero."""
    try:
        product_id = str(data.get("productId") or data.get("product_id") or "").strip()
        selected_size = (data.get("selectedSize") or data.get("size") or "M").strip()
        selected_color = (data.get("selectedColor") or data.get("color") or "").strip()
        quantity = max(0, _safe_int(data.get("quantity") or data.get("qty") or 1, default=1))

        product = find_product_by_public_id(g.db, product_id)
        if not product:
            return False, "Producto no encontrado."

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
            return False, "Item no encontrado en el carrito."

        if quantity == 0:
            g.db.delete(item)
            g.db.commit()
            return True, "Producto eliminado del carrito."

        item.quantity = quantity
        g.db.commit()
        return True, "Cantidad actualizada."
    except SQLAlchemyError:
        g.db.rollback()
        return False, "No fue posible actualizar la cantidad."
    except Exception:
        g.db.rollback()
        return False, "Ocurrio un error inesperado al actualizar el carrito."


def _validate_checkout_form(data, cart_items: list[dict]) -> list[str]:
    """Valida datos del checkout HTML/API."""
    payment_method = (data.get("payment") or data.get("paymentMethod") or "tarjeta").strip().lower()
    errors = []

    if not (data.get("name") or "").strip():
        errors.append("El nombre es obligatorio.")
    if not (data.get("phone") or "").strip():
        errors.append("El teléfono es obligatorio.")
    if not (data.get("address") or "").strip():
        errors.append("La dirección es obligatoria.")
    if not (data.get("city") or "").strip():
        errors.append("La ciudad es obligatoria.")
    if payment_method not in PAYMENT_METHODS:
        errors.append("Selecciona un método de pago válido.")
    if not cart_items:
        errors.append("Tu carrito está vacío.")

    if payment_method == "tarjeta":
        for field, label in (
            ("card_number", "número de tarjeta"),
            ("card_name", "nombre del titular"),
            ("card_expiry", "fecha de expiración"),
            ("card_cvv", "CVV"),
        ):
            if not (data.get(field) or "").strip():
                errors.append(f"Completa el campo {label}.")
    elif payment_method == "nequi" and not (data.get("nequi_phone") or "").strip():
        errors.append("Ingresa el número asociado a Nequi.")
    elif payment_method == "pse":
        if not (data.get("pse_bank") or "").strip():
            errors.append("Selecciona el banco para PSE.")
        if not (data.get("pse_account") or "").strip():
            errors.append("Selecciona el tipo de cuenta PSE.")

    return errors


def _create_order(data) -> tuple[list[str], dict | None]:
    """Convierte carrito actual en pedido persistente."""
    try:
        cart_items = cart_items_for_user(g.db, g.user)
        errors = _validate_checkout_form(data, cart_items)
        if errors:
            return errors, None

        db_items = g.db.query(CartItem).filter_by(user_id=g.user.id).order_by(CartItem.id.asc()).all()
        missing_products = [item for item in db_items if item.product is None]
        if missing_products:
            for item in missing_products:
                g.db.delete(item)
            g.db.commit()
            return ["Algunos productos de tu carrito ya no estan disponibles. Revisa tu carrito e intenta nuevamente."], None

        total = sum((item.product.price * item.quantity for item in db_items), Decimal("0"))
        payment_method = (data.get("payment") or data.get("paymentMethod") or "tarjeta").strip().lower()

        order = Order(
            user_id=g.user.id,
            status="pendiente",
            total=total,
            payment_method=payment_method,
            delivery_name=(data.get("name") or "").strip(),
            delivery_city=(data.get("city") or "").strip(),
            delivery_address=(data.get("address") or "").strip(),
        )
        g.db.add(order)
        g.db.flush()

        for item in db_items:
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

        g.user.name = (data.get("name") or "").strip() or g.user.name
        g.user.phone = (data.get("phone") or "").strip() or g.user.phone
        g.user.address = (data.get("address") or "").strip() or g.user.address
        g.db.commit()

        session["last_order_id"] = order.id
        return [], order_payload(order)
    except SQLAlchemyError:
        g.db.rollback()
        return ["No fue posible procesar el pedido en este momento."], None
    except Exception:
        g.db.rollback()
        return ["Ocurrio un error inesperado al confirmar el pedido."], None


@bp.get("/cart")
def cart_page():
    """Vista HTML del carrito."""
    if not g.user:
        return _login_page_redirect("cart.cart_page")

    items = cart_items_for_user(g.db, g.user)
    return render_template("cart.html", cart_items=items, total=cart_total(items))


@bp.post("/cart/add")
def add_to_cart_page():
    """Submit HTML para agregar producto."""
    if not g.user:
        return _login_page_redirect("cart.cart_page")

    ok, message = _add_to_cart(request.form)
    flash(message, "success" if ok else "danger")
    return redirect(request.form.get("next") or request.referrer or url_for("cart.cart_page"))


@bp.post("/cart/update")
def update_cart_page():
    """Submit HTML para actualizar cantidades."""
    if not g.user:
        return _login_page_redirect("cart.cart_page")

    ok, message = _update_cart_item(request.form)
    flash(message, "success" if ok else "danger")
    return redirect(url_for("cart.cart_page"))


@bp.post("/cart/remove")
def remove_from_cart_page():
    """Submit HTML para eliminar un item del carrito."""
    if not g.user:
        return _login_page_redirect("cart.cart_page")

    ok, message = _remove_from_cart(request.form)
    flash(message, "success" if ok else "danger")
    return redirect(url_for("cart.cart_page"))


@bp.route("/checkout", methods=["GET", "POST"])
def checkout_page():
    """Vista y submit del checkout."""
    if not g.user:
        return _login_page_redirect("cart.checkout_page")

    cart_items = cart_items_for_user(g.db, g.user)
    form_data = {
        "name": request.form.get("name", g.user.name),
        "email": g.user.email,
        "phone": request.form.get("phone", g.user.phone),
        "address": request.form.get("address", g.user.address),
        "city": request.form.get("city", ""),
        "department": request.form.get("department", "Cundinamarca"),
        "payment": request.form.get("payment", "tarjeta"),
    }

    if request.method == "POST":
        errors, order = _create_order(request.form)
        if not errors:
            flash("Pedido creado correctamente.", "success")
            return redirect(url_for("main.order_success_page"))
        return render_template(
            "checkout.html",
            cart_items=cart_items,
            total=cart_total(cart_items),
            user=user_payload(g.user),
            errors=errors,
            checkout_form=form_data,
        )

    return render_template(
        "checkout.html",
        cart_items=cart_items,
        total=cart_total(cart_items),
        user=user_payload(g.user),
        errors=[],
        checkout_form=form_data,
    )


@bp.get("/orders")
def orders_page():
    """Historial de pedidos del usuario autenticado."""
    if not g.user:
        return _login_page_redirect("cart.orders_page")

    orders = [
        order_payload(order)
        for order in g.db.query(Order).filter_by(user_id=g.user.id).order_by(Order.created_at.desc(), Order.id.desc()).all()
    ]
    return render_template("orders.html", orders=orders)


@bp.post("/api/cart/add")
@login_required
def api_cart_add():
    """Agrega producto al carrito del usuario autenticado."""
    ok, message = _add_to_cart(request.get_json(silent=True) or request.form)
    return json_response(ok, message=message)


@bp.post("/api/cart/remove")
@login_required
def api_cart_remove():
    """Elimina un item especifico del carrito del usuario."""
    ok, message = _remove_from_cart(request.get_json(silent=True) or request.form)
    return json_response(ok, message=message)


@bp.post("/api/checkout")
@login_required
def api_checkout():
    """Convierte el carrito en pedido y limpia los items."""
    errors, order = _create_order(request.get_json(silent=True) or request.form)
    if errors:
        return json_response(False, message=" ".join(errors))
    return json_response(True, message="Pedido creado.", order=order)
