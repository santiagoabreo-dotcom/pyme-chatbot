"""
chat.py
───────
Endpoints principales de la API.
"""

import logging

import anthropic
from fastapi import APIRouter, HTTPException, Request

from ..config.registry import registry
from ..models.schemas import ChatRequest, ChatResponse
from ..utils.rate_limit import rate_limiter
from ..utils.security import verify_origin

logger = logging.getLogger("pymechatbot.chat")

router = APIRouter()


@router.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    """Recibe un mensaje del widget y devuelve la respuesta del asistente
    configurado para ese `client_id`."""

    client = registry.get(payload.client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Dominio autorizado para este cliente puntual (además del CORS global).
    verify_origin(request, client.allowed_domain)

    ip = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(f"{client.id}:{ip}", client.rate_limit_per_minute):
        raise HTTPException(
            status_code=429,
            detail="Demasiadas solicitudes. Esperá un momento e intentá de nuevo.",
        )

    api_key = client.get_api_key()
    if not api_key:
        # No exponemos al cliente que falta configurar una env var: es un problema
        # nuestro, no del visitante del widget.
        logger.error(
            "API key no configurada para client_id=%s (variable %s vacía)",
            client.id,
            client.api_key_env,
        )
        raise HTTPException(status_code=503, detail="Servicio no disponible en este momento")

    try:
        anthropic_client = anthropic.Anthropic(api_key=api_key)
        message = anthropic_client.messages.create(
            model=client.model,
            max_tokens=client.max_tokens,
            system=client.build_system_prompt(),
            messages=[{"role": "user", "content": payload.message}],
        )
        response_text = message.content[0].text.strip()
        return ChatResponse(client_id=client.id, response=response_text)

    except anthropic.AuthenticationError:
        logger.error("API key inválida para client_id=%s", client.id)
        raise HTTPException(status_code=503, detail="Servicio no disponible en este momento")
    except anthropic.RateLimitError:
        logger.warning("Rate limit de Anthropic alcanzado para client_id=%s", client.id)
        raise HTTPException(
            status_code=429,
            detail="El asistente está ocupado, intentá de nuevo en unos segundos",
        )
    except Exception:
        # Nunca devolvemos str(e) al cliente: puede filtrar detalles internos
        # (paths, stack, nombres de variables de entorno, etc). El detalle
        # completo queda en el log del servidor.
        logger.exception("Error inesperado procesando chat para client_id=%s", client.id)
        raise HTTPException(status_code=500, detail="Ocurrió un error. Intentá de nuevo más tarde.")


@router.get("/api/health")
def health() -> dict:
    """Health check. No expone dominios ni nombres reales de negocio,
    solo cuántos clientes hay cargados."""
    ids = registry.all_ids()
    return {
        "status": "healthy" if ids else "no_clients_configured",
        "clients_configured": len(ids),
    }
