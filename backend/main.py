"""
main.py
───────
Pyme Chatbot - FastAPI Backend

Multi-tenant: cada Pyme se configura con un archivo JSON en
config/clientes/ (ver backend/config/registry.py), sin tocar este
código. El widget embebible (widget/widget.js) habla con /api/chat
usando solo un client_id público; la API key de Anthropic nunca sale
del servidor.
"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config.registry import CONFIG_DIR, registry
from .routes.chat import router as chat_router
from .utils.security import build_origin_regex

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("pymechatbot")

app = FastAPI(
    title="Pyme Chatbot",
    description="Asistente de Atención al Cliente para Pymes, configurable por negocio sin modificar código.",
    version="0.2.0",
)

# CORS dinámico: solo los dominios registrados por algún cliente pueden
# recibir respuesta del navegador. Se calcula al arrancar a partir de
# config/clientes/*.json — si agregás un cliente nuevo hay que reiniciar
# el proceso para que tome su dominio (ver README, Roadmap).
_origin_regex = build_origin_regex(registry.all_domains())

if _origin_regex:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=_origin_regex,
        allow_credentials=False,
        allow_methods=["POST", "GET", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
else:
    logger.warning(
        "No hay clientes configurados en %s: ningún origen podrá llamar a la API "
        "hasta que agregues al menos un archivo de configuración.",
        CONFIG_DIR,
    )

app.include_router(chat_router)

# Sirve el widget embebible (widget/widget.js) como archivo estático,
# para que un negocio pueda incluirlo con una sola línea de <script>.
_widget_dir = Path(__file__).resolve().parent.parent / "widget"
if _widget_dir.exists():
    app.mount("/widget", StaticFiles(directory=str(_widget_dir)), name="widget")


@app.get("/")
def root():
    """Health check básico."""
    return {
        "status": "ok",
        "service": "Pyme Chatbot",
        "version": app.version,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
