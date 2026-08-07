# Agente CFO

Agente de IA financiero multi-agente para gestionar las finanzas de una empresa. Hoy consulta cuentas y movimientos, calcula el resultado mensual por moneda, y conversa por Telegram. La escritura (registrar movimientos, conciliar facturas con cobros) está en el roadmap.

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
| `MESSAGING_PROVIDER` | `telegram` |

Las siguientes **solo hacen falta si `MESSAGING_PROVIDER=telegram`**. Con otro proveedor se pueden omitir por completo:

| Variable | Qué es |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token que entrega @BotFather |
| `MESSAGING_MODE` | `polling` o `webhook` |
| `MESSAGING_PORT` | Puerto del servidor; solo se usa en modo webhook |
| `TELEGRAM_WEBHOOK_PATH` / `TELEGRAM_WEBHOOK_URL` | Solo para modo webhook |
| `TELEGRAM_CHAT_ID` | Opcional. Destino de los mensajes que el agente manda solo (reportes, alertas). Todavía no lo usa nada |
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
3. *(Opcional)* Obtener el chat ID visitando `https://api.telegram.org/bot<TOKEN>/getUpdates` después de escribirle, y ponerlo en `TELEGRAM_CHAT_ID`. Todavía no lo usa nada: va a ser el destino de los reportes y alertas que el agente mande por su cuenta.

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

1. `qué cuentas tengo?` → lista tus cuentas con saldo, tipo y moneda
2. `qué cobros tengo pendientes?` → los ingresos previstos en estado `pendiente`
3. `cómo venimos este mes?` → resultado del mes separado por moneda
4. `cuál fue el resultado de julio 2026?` → lo mismo, con el mes explícito

También acepta **audios** (los transcribe) e **imágenes** (las lee con visión). Los PDF todavía no se procesan — mandar captura de pantalla.

Los datos que consulta viven en Supabase → Table Editor → schema `finanzas` (verificable también desde el SQL Editor).

## Estructura del proyecto

```
├── main.py               # Punto de entrada: arma el pipeline completo
├── config/               # Qué variables se leen del .env, separadas por tema
│   ├── agents.py         #   API keys + proveedor y modelo de cada agente
│   ├── database.py       #   Base de datos
│   ├── media.py          #   Transcripción y visión
│   └── messaging.py      #   Canal de mensajería
├── core/                 # Abstracciones (interfaces) y factories: llm, db,
│   │                     #   messaging, vision, transcription, scheduler, agents
│   └── agents/base.py    # Contrato Agent + AgentResult que cumple todo sub-agente
├── providers/            # Implementaciones concretas (Claude, OpenAI, Gemini,
│                         #   Supabase, Telegram, Whisper)
├── agents/
│   ├── router.py         # Clasificador de intents
│   ├── orchestrator.py   # Orquestador: decide y encadena sub-agentes
│   └── financial/        # Financial Agent (agent.py + prompt.py) — solo lectura
├── tools/reads/          # Tools de lectura, reutilizables e inyectadas
├── reports/              # Reportes: cálculo determinista sobre los datos
├── db/migrations/        # DDL versionado de la base de datos
└── docs/context.md       # Documentación viva: arquitectura, tablas, decisiones
```

Los archivos de `config/` no contienen ningún dato de la empresa: solo declaran qué variables se leen del entorno. Los valores reales viven en el `.env`, que no está versionado. Por eso el mismo `config/` sirve para cualquier empresa.

**Regla de oro del proyecto:** el core nunca importa SDKs ni conoce empresas concretas. Cambiar de proveedor (LLM, base, mensajería) es cambiar una variable del `.env`.
