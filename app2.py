from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/")
def inicio():
    return render_template("formulario.html")

@app.route("/enviar", methods=["POST"])
def enviar():
    nombre = request.form["nombre"]
    mensaje = request.form["mensaje"]
    return f"Gracias {nombre}, recibimos tu mensaje: {mensaje}"

if __name__ == "__main__":
    app.run(debug=True)