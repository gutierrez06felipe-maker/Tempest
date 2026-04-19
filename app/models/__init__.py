"""Atajos de import para modelos."""

from app.models.models import Base, CartItem, Order, OrderItem, Product, User, db

__all__ = ["Base", "db", "User", "Product", "CartItem", "Order", "OrderItem"]
