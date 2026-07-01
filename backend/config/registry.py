"""
registry.py
───────────
Carga de configuración de clientes (multi-tenant) sin tocar código.

Cada cliente se define en un archivo JSON dentro de `config/clientes/`
(fuera del repo por defecto, ver .gitignore). El registro los lee al
arrancar y expone la configuración por `client_id`.

Agregar un cliente nuevo = agregar un archivo JSON. No requiere
modificar el backend.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("pymechatbot.config")

# Raíz del proyecto: backend/config/registry.py -> backend/config -> backend -> raíz
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CONFIG_DIR = PROJECT_ROOT / "config" / "clientes"

# Permite apuntar a otro directorio de configs (útil para tests o despliegues).
CONFIG_DIR = Path(os.getenv("PYMECHATBOT_CONFIG_DIR", str(DEFAULT_CONFIG_DIR)))


class ClientIdentity(BaseModel):
    """Identidad del asistente para un cliente puntual."""

    name: str = "Asistente"
    role: str = "Asistente de Atención al Cliente"
    tone: str = "profesional y amigable"


class ClientKnowledge(BaseModel):
    """Conocimiento de negocio que el asistente puede usar para responder.

    Todo texto libre: catálogo, políticas, FAQ. Se inyecta en el system
    prompt tal cual, así que conviene mantenerlo breve y curado.
    """

    business_info: str = ""
    faq: str = ""
    policies: str = ""


class ClientConfig(BaseModel):
    """Configuración completa de un cliente (una Pyme)."""

    id: str = Field(..., min_length=1)
    display_name: str = Field(..., min_length=1)
    allowed_domain: str = Field(
        ...,
        description=(
            "Dominio autorizado a llamar a la API para este cliente "
            "(ej: 'tienda.com'). Usar '*' solo en desarrollo local."
        ),
    )
    identity: ClientIdentity = Field(default_factory=ClientIdentity)
    knowledge: ClientKnowledge = Field(default_factory=ClientKnowledge)
    api_key_env: str = Field(
        ...,
        description="Nombre de la variable de entorno que contiene la API key de Anthropic. Nunca la key en sí.",
    )
    model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = Field(default=300, ge=1, le=4096)
    rate_limit_per_minute: int = Field(default=20, ge=1)

    def get_api_key(self) -> Optional[str]:
        """Resuelve la API key real desde la variable de entorno configurada."""
        return os.getenv(self.api_key_env)

    def build_system_prompt(self) -> str:
        """Arma el system prompt a partir de la config, sin tocar código."""
        parts = [
            f"Eres {self.identity.name}, {self.identity.role} de {self.display_name}.",
            f"Tu tono es {self.identity.tone}.",
        ]
        if self.knowledge.business_info:
            parts.append(f"Información del negocio:\n{self.knowledge.business_info}")
        if self.knowledge.faq:
            parts.append(f"Preguntas frecuentes:\n{self.knowledge.faq}")
        if self.knowledge.policies:
            parts.append(f"Políticas relevantes:\n{self.knowledge.policies}")
        parts.append(
            "Respondé de forma breve y clara, basándote solo en la información de "
            "arriba. Si no sabés algo con certeza, decilo honestamente y sugerí "
            "contactar directamente al negocio en vez de inventar datos."
        )
        return "\n\n".join(parts)


class ClientRegistry:
    """Carga y cachea las configuraciones de todos los clientes."""

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self._clients: dict[str, ClientConfig] = {}
        self.reload()

    def reload(self) -> None:
        """Vuelve a leer todos los archivos JSON del directorio de config.

        Un archivo inválido se ignora (con log de error) en vez de tumbar
        el servicio entero: un typo en el config de un cliente no debería
        afectar a los demás.
        """
        self._clients = {}
        if not self.config_dir.exists():
            logger.warning("Directorio de configuración no existe: %s", self.config_dir)
            return

        for file in sorted(self.config_dir.glob("*.json")):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                cfg = ClientConfig(**data)
            except Exception as exc:  # noqa: BLE001 - queremos loguear cualquier error de config
                logger.error("No se pudo cargar %s: %s", file.name, exc)
                continue

            if cfg.id in self._clients:
                logger.warning("client_id duplicado '%s' en %s (se sobrescribe)", cfg.id, file.name)
            self._clients[cfg.id] = cfg

        logger.info("Clientes cargados: %s", list(self._clients.keys()) or "ninguno")

    def get(self, client_id: str) -> Optional[ClientConfig]:
        return self._clients.get(client_id)

    def all_ids(self) -> list[str]:
        return list(self._clients.keys())

    def all_domains(self) -> list[str]:
        return sorted({c.allowed_domain for c in self._clients.values() if c.allowed_domain})


# Instancia compartida por toda la app, cargada al importar el módulo.
registry = ClientRegistry(CONFIG_DIR)
