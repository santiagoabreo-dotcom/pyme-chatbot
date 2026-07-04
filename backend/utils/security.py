"""
security.py
────────────
Capas de seguridad simples pero honestas para el MVP:

1. CORS a nivel navegador: solo los dominios registrados por algún
   cliente pueden recibir respuesta a un fetch() desde el browser.
2. Validación de Origin/Referer en el propio endpoint: el dominio que
   llama debe coincidir con el `allowed_domain` del `client_id` que dice
   ser.

Importante: Origin/Referer los define el cliente HTTP y pueden
falsificarse fuera de un navegador (con curl, por ejemplo). Esta capa
frena el uso accidental o no autorizado desde otros sitios web, pero
NO es autenticación fuerte. Para eso hace falta un secreto por cliente
(ver README, sección Seguridad).
"""

import re
from typing import Optional
from urllib.parse import urlparse

from fastapi import HTTPException, Request


def _hostname(url: str) -> str:
    if not url:
        return ""
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def verify_origin(request: Request, allowed_domain: str) -> None:
    """Verifica que el Origin (o Referer, como fallback) del request
    coincida con el dominio registrado para el cliente.

    `allowed_domain == "*"` desactiva el chequeo (solo para desarrollo
    local, nunca en producción).
    """
    if allowed_domain == "*":
        return

    origin = request.headers.get("origin") or request.headers.get("referer") or ""
    hostname = _hostname(origin)
    allowed = allowed_domain.lower()

    if not hostname or not (hostname == allowed or hostname.endswith("." + allowed)):
        raise HTTPException(
            status_code=403,
            detail="Este cliente no está autorizado a llamar desde este dominio.",
        )


def build_origin_regex(domains: list[str]) -> Optional[str]:
    """Construye un regex de orígenes permitidos para CORSMiddleware a
    partir de los dominios registrados por todos los clientes.

    Permite el dominio exacto y subdominios, en http y https (http solo
    importa para desarrollo local).
    """
    escaped = [re.escape(d) for d in domains if d and d != "*"]
    if not escaped:
        return None
    alternation = "|".join(escaped)
    return rf"^https?://([a-zA-Z0-9-]+\.)?({alternation})(:\d+)?$"
