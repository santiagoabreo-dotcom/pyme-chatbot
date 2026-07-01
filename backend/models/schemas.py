"""
schemas.py
──────────
Modelos Pydantic de entrada/salida de la API.
"""

from pydantic import BaseModel, Field, field_validator

MAX_MESSAGE_LENGTH = 2000


class ChatRequest(BaseModel):
    """Solicitud de chat entrante desde el widget."""

    client_id: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        # Descarta caracteres de control (excepto salto de línea) y espacios sobrantes.
        cleaned = "".join(ch for ch in value if ch == "\n" or ch.isprintable())
        cleaned = cleaned.strip()
        if not cleaned:
            raise ValueError("El mensaje no puede estar vacío")
        return cleaned


class ChatResponse(BaseModel):
    """Respuesta del chatbot."""

    client_id: str
    response: str
