"""Rutas de autenticacion (login, registro, logout)."""

from __future__ import annotations

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app.models.models import User
from app.services.logic import json_response, normalize_role, session_user_payload, user_payload


bp = Blueprint("auth", __name__)


def _safe_redirect_target(target: str | None) -> str | None:
    """Solo permite redirects internos simples."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return None


def _login_user(user: User) -> None:
    """Guarda sesion consistente para frontend y backend."""
    normalized_role = normalize_role(user.role)
    if normalized_role != user.role:
        user.role = normalized_role
        g.db.commit()

    session.clear()
    session["user_id"] = user.id
    session["user"] = session_user_payload(user)
    session["user_email"] = user.email


@bp.route("/login", methods=["GET", "POST"])
def login_page():
    """Vista y submit de inicio de sesion."""
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        next_url = _safe_redirect_target(request.form.get("next") or request.args.get("next"))

        user = g.db.query(User).filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash("Credenciales inválidas. Verifica email y contraseña.", "danger")
            return render_template("login.html", next_url=next_url or "")

        _login_user(user)
        flash("Sesión iniciada correctamente.", "success")
        return redirect(next_url or url_for("main.home"))

    if g.user:
        return redirect(url_for("main.home"))

    return render_template("login.html", next_url=_safe_redirect_target(request.args.get("next")) or "")


@bp.route("/register", methods=["GET", "POST"])
def register_page():
    """Vista y submit de registro."""
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""
        role = normalize_role(request.form.get("role") or "client")
        phone = (request.form.get("phone") or "").strip()
        address = (request.form.get("address") or "").strip()
        admin_pass = request.form.get("adminPass") or ""

        if not name or not email or not password:
            flash("Completa los campos obligatorios.", "warning")
            return render_template("register.html")
        if password != confirm:
            flash("La confirmación de contraseña no coincide.", "warning")
            return render_template("register.html")
        if len(password) < 6:
            flash("La contraseña debe tener mínimo 6 caracteres.", "warning")
            return render_template("register.html")
        if g.db.query(User).filter_by(email=email).first():
            flash("Ese correo ya está registrado.", "warning")
            return render_template("register.html")
        if role == "admin" and admin_pass != current_app.config["ADMIN_INVITE_SECRET"]:
            flash("La clave de administrador no es válida.", "danger")
            return render_template("register.html")

        user = User(
            name=name,
            email=email,
            role=role,
            phone=phone,
            address=address,
            password_hash=generate_password_hash(password),
        )
        g.db.add(user)
        g.db.commit()

        _login_user(user)
        flash("Cuenta creada con éxito.", "success")
        return redirect(url_for("main.home"))

    if g.user:
        return redirect(url_for("main.home"))

    return render_template("register.html")


@bp.route("/logout", methods=["GET", "POST"])
def logout_page():
    """Cierra sesion y vuelve al inicio."""
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("main.home"))


@bp.post("/api/login")
def api_login():
    """Autentica usuario y responde JSON."""
    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = g.db.query(User).filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return json_response(False, message="Credenciales inválidas.")

    _login_user(user)
    return json_response(True, message="Sesión iniciada.", user=user_payload(user))


@bp.post("/api/register")
def api_register():
    """Registro JSON conservando compatibilidad con el frontend anterior."""
    data = request.get_json(silent=True) or request.form
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = normalize_role(data.get("role") or "client")
    phone = (data.get("phone") or "").strip()
    address = (data.get("address") or "").strip()
    admin_pass = data.get("adminPass") or ""

    if not name or not email or not password:
        return json_response(False, message="Completa los campos obligatorios.")
    if g.db.query(User).filter_by(email=email).first():
        return json_response(False, message="Ese email ya está registrado.")
    if role == "admin" and admin_pass != current_app.config["ADMIN_INVITE_SECRET"]:
        return json_response(False, message="Contraseña de administrador incorrecta.")

    user = User(
        name=name,
        email=email,
        role=role,
        phone=phone,
        address=address,
        password_hash=generate_password_hash(password),
    )
    g.db.add(user)
    g.db.commit()

    _login_user(user)
    return json_response(True, message="Cuenta creada.", user=user_payload(user))


@bp.post("/api/logout")
def api_logout():
    """Cierre de sesion para clientes API."""
    session.clear()
    return json_response(True, message="Sesión cerrada.")
