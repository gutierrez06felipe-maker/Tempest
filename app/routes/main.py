"""Rutas generales de navegacion y estado."""

from __future__ import annotations

from flask import Blueprint, current_app, flash, g, jsonify, redirect, render_template, request, session, url_for

from app.models import Order
from app.services.logic import bootstrap_payload, featured_products, health_payload, order_payload


bp = Blueprint("main", __name__)


FAQ_ITEMS = [
    {
        "question": "¿Cuáles son los tiempos de entrega?",
        "answer": "Bogotá: 1 a 2 días hábiles. Resto de Colombia: 3 a 5 días hábiles.",
    },
    {
        "question": "¿Puedo cambiar la talla?",
        "answer": "Sí. Puedes solicitar cambio dentro de los 30 días posteriores a la compra.",
    },
    {
        "question": "¿Qué métodos de pago aceptan?",
        "answer": "Tarjeta, PSE, Nequi y contraentrega.",
    },
    {
        "question": "¿Cómo rastreo mi pedido?",
        "answer": "Desde tu historial de pedidos podrás identificar cada compra y su estado actual.",
    },
]

SUPPORT_TOPICS = [
    "Consulta sobre pedido",
    "Cambio de talla",
    "Problema con pago",
    "Información de producto",
    "Otro",
]

CONTACT_CHANNELS = [
    {"label": "Instagram", "value": "@sport.tempest"},
    {"label": "Email", "value": "soporte@tempest.com"},
]


@bp.get("/")
def home():
    """Pagina principal del ecommerce."""
    return render_template("index.html", featured=featured_products(g.db, limit=4))


@bp.get("/about")
def about_page():
    """Vista informativa de marca."""
    return render_template("about.html")


@bp.route("/support", methods=["GET", "POST"])
def support_page():
    """Soporte basico con formulario y FAQs."""
    form_data = {
        "name": request.form.get("name", session.get("user", {}).get("name", "")),
        "email": request.form.get("email", session.get("user", {}).get("email", "")),
        "subject": request.form.get("subject", SUPPORT_TOPICS[0]),
        "message": request.form.get("message", ""),
    }

    if request.method == "POST":
        missing = [field for field in ("name", "email", "subject", "message") if not request.form.get(field, "").strip()]
        if missing:
            flash("Completa todos los campos del formulario de soporte.", "warning")
        else:
            flash("Recibimos tu mensaje. Te responderemos pronto.", "success")
            return redirect(url_for("main.support_page"))

    return render_template(
        "support.html",
        faq_items=FAQ_ITEMS,
        support_topics=SUPPORT_TOPICS,
        contact_channels=CONTACT_CHANNELS,
        support_form=form_data,
    )


@bp.get("/pedido-exitoso")
def order_success_page():
    """Resumen final del ultimo pedido confirmado."""
    last_order_id = session.get("last_order_id")
    order = None

    if last_order_id:
        try:
            order = g.db.get(Order, int(last_order_id))
        except (TypeError, ValueError):
            session.pop("last_order_id", None)
            order = None
        if order and g.user and order.user_id != g.user.id and getattr(g.user, "role", "client") != "admin":
            order = None

    if not order and g.user:
        order = (
            g.db.query(Order)
            .filter_by(user_id=g.user.id)
            .order_by(Order.created_at.desc(), Order.id.desc())
            .first()
        )

    if not order:
        flash("Aún no tienes un pedido confirmado para mostrar.", "info")
        return redirect(url_for("products.products_page"))

    return render_template("order_success.html", order=order_payload(order))


@bp.get("/health")
def health():
    """Endpoint de salud para despliegue."""
    return health_payload(current_app.config["DATABASE_URL"])


@bp.get("/api/bootstrap")
def api_bootstrap():
    """Estado inicial reutilizable para integraciones frontend."""
    return jsonify(bootstrap_payload(g.db, g.user))
