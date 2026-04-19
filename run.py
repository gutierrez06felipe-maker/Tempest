"""
Punto de entrada de produccion/desarrollo.

Render/Gunicorn:
    gunicorn run:app
"""

from __future__ import annotations

import os

from app import create_app


app = create_app()


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)
