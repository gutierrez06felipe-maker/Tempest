from flask import Flask, render_template, request, redirect, url_for
from PIL import Image
import os

app = Flask(__name__)

@app.route("/")
def index():
    productos = [
        {"nombre": "Camiseta Deportiva Negra", "precio": 45000, "imagen": "camiseta.jpg"},
        {"nombre": "Camiseta Deportiva Blanca", "precio": 42000, "imagen": "camiseta.jpg"},
    ]
    return render_template("index.html", productos=productos)

@app.route("/comprar", methods=["POST"])
def comprar():
    nombre = request.form.get("nombre")
    correo = request.form.get("correo")
    producto = request.form.get("producto")

    print("Pedido recibido:", nombre, correo, producto)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)