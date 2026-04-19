from app import create_app
from app.models.models import db, Product, OrderItem, CartItem

app = create_app()

with app.app_context():
    product_id = 16  # 👈 ESTE ES EL QUE QUIERES ELIMINAR

    product = db.session.get(Product, product_id)

    if not product:
        print("❌ Producto no encontrado")
    else:
        # eliminar relaciones primero
        OrderItem.query.filter_by(product_id=product_id).delete()
        CartItem.query.filter_by(product_id=product_id).delete()

        # eliminar producto
        db.session.delete(product)
        db.session.commit()

        print("✅ Producto eliminado correctamente")