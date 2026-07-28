# Agente CFO

Agente de IA financiero multi-agente. Gestiona las finanzas de una empresa de manera autónoma: registra movimientos, concilia facturas con cobros, calcula resúmenes mensuales con división de ganancias entre socios, y conversa por Telegram.

La primera implementación es para **AIXO Studio**, pero el core es genérico: todo lo específico de la empresa vive en configuración (`.env` + `config/`), nunca en la lógica. El proyecto está pensado para reimplementarse en otras empresas sin tocar el código.

## Arquitectura en una línea

```
Telegram → Preprocessor → Router → Orquestador → Financial Agent → Supabase
  (sin      (Whisper +     (LLM:     (LLM:         (LLM: elige      (sin
   LLM)      visión)       etiqueta)  decide)       tool)            LLM)
```

- **Preprocessor**: convierte todo a texto (transcribe audios con Whisper, describe imágenes con visión).
- **Router**: clasifica cada mensaje en un intent (LLM barato).
- **Orquestador**: decide qué sub-agente resuelve el pedido y puede encadenar varios.
- **Financial Agent**: consulta la base de datos (cuentas, ingresos y egresos, previstos y efectuados). Por ahora solo lectura.

El detalle completo está en [`docs/context.md`](docs/context.md).

## Requisitos

- Python 3.12 o superior
- Una cuenta de [Supabase](https://supabase.com) (plan Free alcanza)
- Un bot de Telegram (se crea gratis con [@BotFather](https://t.me/BotFather))
- API keys de los proveedores de LLM que uses (OpenAI y/o Anthropic y/o Google)

## Instalación

### 1. Clonar e instalar dependencias

```bash
git clone git@github.com:lukipozzoli/aixo-cfo.git
cd aixo-cfo
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configurar el `.env`

```bash
cp .env.example .env
```

Completar las variables:

| Variable | Qué es |
|---|---|
| `DATABASE_PROVIDER` | `supabase` |
| `DATABASE_URL` | URL del proyecto Supabase (Settings → Data API) |
| `DATABASE_KEY` | **Secret key** del proyecto (Settings → API Keys → Secret keys). Nunca la publishable. |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` | Solo las de los providers que uses |
| `ROUTER_PROVIDER` / `ROUTER_MODEL` | Clasificador de intents (ej: `openai` / `gpt-4o-mini`) |
| `ORCHESTRATOR_PROVIDER` / `ORCHESTRATOR_MODEL` | Orquestador (ej: `openai` / `gpt-4o-mini`) |
| `FINANCIAL_AGENT_PROVIDER` / `FINANCIAL_AGENT_MODEL` | Agente financiero (ej: `openai` / `gpt-4o-mini`) |
| `CONVERSATION_AGENT_*` / `REPORT_AGENT_*` | Vacías por ahora (agentes aún no implementados) |
| `MESSAGING_PROVIDER` / `MESSAGING_MODE` | `telegram` / `polling` |
| `MESSAGING_PORT` | Puerto para modo webhook (con polling no se usa, pero debe tener valor) |
| `TELEGRAM_BOT_TOKEN` | Token que entrega @BotFather |
| `TELEGRAM_CHAT_ID` | ID del chat autorizado |
| `TELEGRAM_WEBHOOK_PATH` / `TELEGRAM_WEBHOOK_URL` | Solo para modo webhook |
| `TRANSCRIPTION_PROVIDER` / `TRANSCRIPTION_MODEL` | Transcripción de audios (ej: `whisper` / `whisper-1`) |
| `VISION_PROVIDER` / `VISION_MODEL` | Lectura de imágenes (ej: `claude` / `claude-haiku-4-5-20251001`) |

### 3. Crear la base de datos en Supabase

1. Crear un proyecto en Supabase.
2. Abrir el **SQL Editor**, pegar el contenido completo de `db/migrations/001_finanzas.sql` y ejecutar con **Run and enable RLS** (botón verde). Esto crea el schema `finanzas` con sus tablas, y las protege con Row Level Security.
3. Exponer el schema a la API: **Settings → Data API → Exposed schemas** → agregar `finanzas` → Save.

> Los permisos del schema para el rol de backend (`service_role`) están incluidos al final de la migración. Sin ellos la API devuelve `permission denied for schema finanzas`.

### 4. Crear el bot de Telegram

1. Hablarle a [@BotFather](https://t.me/BotFather) → `/newbot` → seguir los pasos → copiar el token a `TELEGRAM_BOT_TOKEN`.
2. Escribirle cualquier cosa al bot recién creado (para abrir el chat).
3. Obtener el chat ID (por ejemplo visitando `https://api.telegram.org/bot<TOKEN>/getUpdates` después de escribirle) y ponerlo en `TELEGRAM_CHAT_ID`.

## Correr el agente

```bash
source venv/bin/activate
python3 main.py
```

Debería aparecer:

```
Agente CFO iniciado. Escuchando mensajes...
```

Se detiene con `Ctrl+C`.

## Probar que funciona

Por Telegram, en orden:

1. `creá una cuenta que se llame Banco Test, bancaria, en pesos` → confirma la creación
2. `cargá un gasto de 1000 pesos de prueba en Banco Test` → registra el gasto y descuenta el saldo
3. `qué cuentas tengo?` → lista la cuenta con saldo -1000
4. `cómo venimos este mes?` → resumen con ingresos, egresos, ganancia neta y mitad por socio

También acepta **audios** (los transcribe) e **imágenes de facturas** (las lee con visión y las carga como ingresos previstos). Los PDF todavía no se procesan — mandar captura de pantalla.

Los registros quedan en Supabase → Table Editor → schema `finanzas` (verificable también desde el SQL Editor).

## Estructura del proyecto

```
├── main.py               # Punto de entrada: arma el pipeline completo
├── config/aixo.py        # Configuración de la empresa (lee el .env)
├── core/                 # Abstracciones (interfaces): llm, db, messaging,
│   │                     #   vision, transcription, scheduler, agents
│   └── agents/base.py    # Contrato Agent + AgentResult que cumple todo sub-agente
├── providers/            # Implementaciones concretas (Claude, OpenAI, Gemini,
│                         #   Supabase, Telegram, Whisper)
├── agents/
│   ├── router.py         # Clasificador de intents
│   ├── orchestrator.py   # Orquestador: decide y encadena sub-agentes
│   └── financial/        # Financial Agent (agent.py + prompt.py) — solo lectura
├── db/migrations/        # DDL versionado de la base de datos
└── docs/context.md       # Documentación viva: arquitectura, tablas, decisiones
```

**Regla de oro del proyecto:** el core nunca importa SDKs ni conoce empresas concretas. Cambiar de proveedor (LLM, base, mensajería) es cambiar una variable del `.env`.
