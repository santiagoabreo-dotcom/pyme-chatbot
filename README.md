# Pyme Chatbot

**Asistente de Atención al Cliente para Pymes**

Chatbot personalizable por negocio sin tocar código: cada cliente define identidad, tono y conocimiento en un archivo de configuración, y el backend arma el comportamiento del asistente a partir de esos datos. Se embebe en cualquier sitio con una línea de `<script>`, sin exponer credenciales al navegador.

## Características

- **Multi-tenant sin código**: agregar un cliente nuevo es agregar un archivo JSON, no tocar el backend.
- **Identidad y conocimiento por config**: nombre, rol, tono, info del negocio, FAQ y políticas se inyectan en el system prompt automáticamente.
- **Widget JS embebible**: una línea de `<script>`, sin API keys en el navegador.
- **CORS por dominio**: solo los dominios registrados por algún cliente pueden llamar a la API desde el navegador, más una validación server-side por cliente.
- **Rate limiting básico** por cliente + IP.

## Stack

Python · FastAPI · Anthropic API · CORS dinámico por dominio.

## Arquitectura

```
pyme-chatbot/
├── backend/
│   ├── main.py              # App FastAPI, CORS, monta el widget estático
│   ├── config/
│   │   └── registry.py      # Carga config/clientes/*.json → ClientConfig
│   ├── models/
│   │   └── schemas.py       # ChatRequest / ChatResponse (Pydantic)
│   ├── routes/
│   │   └── chat.py          # POST /api/chat, GET /api/health
│   └── utils/
│       ├── security.py      # Validación de Origin + regex de CORS
│       └── rate_limit.py    # Rate limiter en memoria
├── config/
│   ├── cliente-ejemplo.json # Plantilla (versionada en git)
│   └── clientes/            # Configs reales por negocio (gitignored)
├── widget/
│   └── widget.js            # Widget embebible
└── requirements.txt
```

## Instalación

```bash
git clone https://github.com/<tu-usuario>/pyme-chatbot.git
cd pyme-chatbot
pip install -r requirements.txt

# 1. Copiar la plantilla de cliente y editarla
cp config/cliente-ejemplo.json config/clientes/demo.json
# editar id, display_name, allowed_domain (usar "localhost" para probar local),
# identity, knowledge y api_key_env

# 2. Setear la variable de entorno que el config apunta (api_key_env)
export CLIENTE1_ANTHROPIC_API_KEY=sk-ant-...

# 3. Levantar el servidor
uvicorn backend.main:app --reload
```

`GET /api/health` te dice cuántos clientes quedaron cargados. Si agregás o editás un archivo en `config/clientes/`, hay que reiniciar el proceso para que tome el cambio (ver Roadmap).

## Agregar un cliente nuevo (sin tocar código)

Crear `config/clientes/<algo>.json`:

```json
{
  "id": "cliente-1",
  "display_name": "Tienda Online XYZ",
  "allowed_domain": "tienda.com",
  "identity": {
    "name": "Maya",
    "role": "Asistente de Ventas",
    "tone": "amigable y profesional"
  },
  "knowledge": {
    "business_info": "Vendemos indumentaria deportiva. Envíos a todo el país en 48-72hs.",
    "faq": "¿Hacen cambios? Sí, dentro de los 30 días con etiqueta original.",
    "policies": "Devoluciones sin cargo dentro de los 30 días."
  },
  "api_key_env": "CLIENTE1_ANTHROPIC_API_KEY",
  "model": "claude-haiku-4-5-20251001",
  "max_tokens": 300,
  "rate_limit_per_minute": 20
}
```

Notar que `api_key_env` es el **nombre** de una variable de entorno, no la key en sí — la key real nunca se escribe en el archivo de configuración ni se commitea.

## Integración en un sitio (una línea)

```html
<script src="https://tu-backend.com/widget/widget.js"
        data-client-id="cliente-1"
        data-title="¿En qué te ayudamos?"
        defer></script>
```

El widget solo conoce el `client_id` (público). La API key de Anthropic vive únicamente en el servidor y nunca viaja al navegador.

## API

```
POST /api/chat
Content-Type: application/json

{ "client_id": "cliente-1", "message": "¿Tienen stock de X?" }

→ { "client_id": "cliente-1", "response": "Sí, tenemos stock disponible..." }
```

```
GET /api/health
→ { "status": "healthy", "clients_configured": 1 }
```

## Seguridad — qué cubre esto y qué no

- **CORS por dominio**: el backend arma la lista de orígenes permitidos a partir de los `allowed_domain` de todos los clientes configurados. Un sitio no registrado no puede leer la respuesta de un `fetch()` al endpoint.
- **Validación de Origin por cliente**: además del CORS global, cada request valida que el `Origin`/`Referer` coincida con el dominio del `client_id` que dice ser — evita que un dominio autorizado para el Cliente A use el `client_id` del Cliente B.
- **Límite honesto**: `Origin`/`Referer` los controla quien hace el request; un script fuera de un navegador (curl, un backend de otro lado) puede falsificarlos. Esta capa frena el uso accidental o no autorizado desde otro sitio web, **no reemplaza autenticación fuerte**. Para eso, el siguiente paso sería un secreto por cliente (ver Roadmap).
- **Sin credenciales en el cliente**: la API key de Anthropic solo existe como variable de entorno del servidor; nunca se envía al navegador ni se commitea en `config/clientes/*.json`.
- **Rate limiting**: en memoria, por `client_id` + IP. Suficiente para un solo proceso; con múltiples workers cada uno cuenta por separado (el límite efectivo se multiplica).
- **Errores sin fugas**: las excepciones no se devuelven al cliente (`str(e)`); se loguean server-side y se responde un mensaje genérico.

## Qué prioricé para el MVP vs. qué queda para después

**En el MVP:** endpoint funcional, config multi-tenant sin código, CORS + validación de origen por cliente, rate limiting básico, manejo de errores que no filtra detalles internos, widget embebible sin exponer credenciales.

**Roadmap (fuera del MVP):**
- [ ] Recarga de configuración en caliente (hoy requiere reiniciar el proceso)
- [ ] Rate limiting compartido (Redis) para correr con más de un worker
- [ ] Secreto/token por cliente además de la validación de Origin
- [ ] Caché de respuestas para preguntas frecuentes repetidas
- [ ] Panel de administración multi-cliente
- [ ] Analytics por cliente
- [ ] Entrenamiento con documentos propios (RAG) en vez de FAQ en texto plano
- [ ] Soporte multi-idioma

## Licencia

MIT

---

**Proyecto Personal · Santiago Abreo**
