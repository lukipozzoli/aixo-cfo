# Contexto del Proyecto

## Qué es este agente

Agente CFO diseñado para gestionar las finanzas de una empresa de manera autónoma
e inteligente. La primera implementación es para AIXO, un estudio de
diseño/tecnología argentino.

Está diseñado para ser reutilizado en otras empresas con mínima configuración.
Todo lo específico de AIXO vive en archivos de configuración separados.
El core nunca hardcodea nada de ninguna empresa en particular.

---

## Arquitectura general

El sistema es multi-agente. Cada agente tiene una responsabilidad específica.

Pipeline implementado y funcionando:

```
Telegram → Preprocessor → Router → Orquestador → Sub-agentes → Supabase
```

- **Preprocessor**: convierte todo a texto (transcribe audios, describe imágenes con visión).
- **Router**: clasifica el mensaje en un intent (una palabra, LLM barato).
- **Orquestador**: recibe mensaje + intent y decide qué sub-agente resuelve el pedido.
  Puede encadenar varios agentes. El intent es una pista, no una orden.
- **Sub-agentes**: cada uno resuelve su dominio con operaciones validadas por código.

La interfaz actual del sistema es **Telegram** (modo polling). Es la interfaz de
testeo mientras se construye la estructura; el diseño permite sumar otras
(WhatsApp, iMessage, web) implementando `MessagingProvider`.

Entradas al sistema:
- Mensajes del usuario vía proveedor de mensajería (hoy: Telegram)
- Webhooks externos (Gmail, Linear, Bancos)
- Cron jobs programados
- Llamadas desde otros agentes (Admin, Ops)

La capa de conectores normaliza todos los eventos externos a un formato estándar
antes de que lleguen al agente financiero. Esto permite agregar nuevas fuentes
sin tocar la lógica central.

---

## Patrón de providers

Todo componente con dependencia externa (LLM, base de datos, mensajería) sigue el mismo patrón:

1. `core/<tipo>/base.py` — clase abstracta que define la interfaz. El core y los agentes solo importan de acá.
2. `providers/<tipo>/<nombre>.py` — implementación concreta para un proveedor específico.
3. `<tipo>/client.py` o `core/<tipo>/factory.py` — factory que instancia el provider correcto según config.
4. `config/aixo.py` — variable de entorno que selecciona el provider (ej: `DATABASE_PROVIDER=supabase`).

**Para agregar un nuevo provider:**
1. Crear `providers/<tipo>/<nuevo_nombre>.py`
2. Implementar la clase abstracta de `core/<tipo>/base.py`
3. Registrar el nuevo provider en el factory correspondiente con su nombre como clave

Este patrón garantiza que cambiar de proveedor (de Supabase a Postgres, de Claude a GPT-4, de Telegram a iMessage) no requiere tocar ningún agente ni lógica de negocio.

### Providers implementados

#### LLM (`core/llm/base.py` → `LLMProvider`)
Métodos: `async chat(messages)`, `async complete(prompt)`
Factory: `core/llm/factory.py` → `build_llm_provider(provider, model, api_key)`

| Provider | Archivo | Variable de selección |
|----------|---------|----------------------|
| Anthropic Claude | `providers/llm/claude.py` | `<AGENTE>_PROVIDER=claude` |
| OpenAI | `providers/llm/openai.py` | `<AGENTE>_PROVIDER=openai` |
| Google Gemini | `providers/llm/gemini.py` | `<AGENTE>_PROVIDER=gemini` |

Cada agente tiene su propio provider y modelo configurados de forma independiente:
`FINANCIAL_AGENT_PROVIDER`, `CONVERSATION_AGENT_PROVIDER`, `REPORT_AGENT_PROVIDER`, `ROUTER_PROVIDER`.

#### Base de datos (`core/db/base.py` → `DatabaseClient`)
Métodos: `select(table, filters)`, `insert(table, data)`, `update(table, data, filters)`, `delete(table, filters)`
Factory: `db/client.py` → `get_client()`

| Provider | Archivo | Variable de selección |
|----------|---------|----------------------|
| Supabase | `providers/db/supabase.py` | `DATABASE_PROVIDER=supabase` |

El schema de Postgres llega por constructor junto con la URL y la key, desde
`DATABASE_SCHEMA`. `SupabaseClient` lo ata una sola vez —`create_client(...).schema(x)`
devuelve un cliente ya apuntado a ese espacio de tablas— y los cuatro métodos no
vuelven a nombrarlo.

Va en el constructor y no en la interfaz `DatabaseClient` a propósito: "schema" es un
concepto de Postgres, y si mañana el provider fuera Mongo o SQLite ese parámetro no
significaría nada. La abstracción queda genérica; el detalle vive en el adaptador que
sí sabe con qué habla.

Una instancia representa **el acceso a un conjunto de tablas**: quien la recibe pide
una tabla por nombre y no sabe en qué schema vive. Para hablarle a otro schema se
construye otro cliente. Hoy `get_client()` devuelve uno solo, así que el sistema usa
un único schema por corrida; cuando ARCA necesite `facturacion` en paralelo, el
cambio es que el factory reciba el schema y guarde uno por cada uno — confinado a
`db/client.py`.

**El nombre lo fija la migración, no el `.env`.** `001_finanzas.sql` escribe `finanzas`
en el `create schema`, en cada tabla y en los `grant`. `DATABASE_SCHEMA` tiene que
coincidir; cambiar de nombre es editar los dos lados. No se parametrizó el SQL porque
el flujo de instalación es pegar el archivo en el editor de Supabase y un paso de
plantilla lo rompería.

#### Mensajería (`core/messaging/base.py` → `MessagingProvider`)
Métodos: `send(chat_id, text)`, `listen(handler)`
Factory: `messaging/client.py` → `get_client()`

| Provider | Archivo | Variable de selección |
|----------|---------|----------------------|
| Telegram (webhook) | `providers/messaging/telegram.py` | `MESSAGING_PROVIDER=telegram` |

*El modo de Telegram (webhook/polling) se configura con `MESSAGING_MODE`.*

#### Scheduler (`core/scheduler/base.py` → `Scheduler`)
Métodos: `register_job(job_id, func, cron_expr)`, `run()`
*Implementación concreta: a definir.*

---

## Concurrencia

Todo el sistema corre sobre un único event loop de asyncio. `async` no reparte el
trabajo en varios hilos: la concurrencia sale de que cada espera de red ceda el
control con `await`. Una llamada sincrónica que tarda segundos no cede nada y
congela el proceso entero mientras dura.

Por eso las interfaces de las esperas largas son `async`: `LLMProvider`,
`VisionProvider` y `TranscriptionProvider`. `DatabaseClient` todavía es sincrónico
(ver Pendientes técnicos).

**Dónde vive la decisión de procesar en paralelo.** En `main.py`, no en los
providers. `main.py` no le pasa su `handle` directamente a `listen()`: le pasa un
`dispatch` que lanza el pipeline como tarea y vuelve enseguida. El provider hace su
`await handler(...)` de siempre, ese await vuelve al instante, y el loop sigue
recibiendo.

El motivo es de arquitectura: procesar en paralelo es una política de la
aplicación, no un detalle del transporte. Si la decidiera cada provider, cambiar de
mensajería cambiaría el comportamiento además del canal — y la regla del proyecto
es que cambiar de proveedor sea cambiar una variable del `.env`. Además, así
cualquier mensajería futura (WhatsApp, iMessage, web) hereda el comportamiento sin
escribir una línea.

**Manejo de errores y de tareas.** Dos defensas, las dos en `main.py`:
- `handle` tiene un `try/except` que le responde al usuario si algo falla, en vez
  de dejarlo esperando. Antes una excepción se llevaba puesto el loop de mensajería
  y el bot dejaba de atender a todos; ahora solo se cae el mensaje que falló.
- Cada tarea se guarda en un set (`_tareas_en_vuelo`) y reporta sus errores por
  callback. asyncio guarda solo una referencia débil a las tareas, así que sin el
  set el recolector de basura puede matar una a mitad de camino.

---

## Logging

Nada escribe a `stdout` directamente. Cada módulo pide su logger con
`logging.getLogger(__name__)` y solo emite; **a dónde va esa salida y con cuánto
detalle lo decide `main.py`**, una sola vez, con el nivel leído de `LOG_LEVEL`.

Es la misma separación que la concurrencia: el módulo sabe *qué* informar, la
aplicación decide *qué se hace* con eso. Un agente no tiene por qué saber si su
diagnóstico va a una terminal, a un archivo o a un agregador de logs.

**Qué va en cada nivel** — esta es la regla que hace que el esquema sirva:

| Nivel | Qué lleva |
|---|---|
| `DEBUG` | El detalle completo: decisiones del LLM, filas devueltas por las tools, montos. |
| `INFO` | Que algo pasó, sin el contenido. Ej: el arranque del bot. |
| `ERROR` | Fallas, con su traceback (`logger.exception` lo agrega solo). |

**Ningún dato financiero puede aparecer en `INFO` o por encima.** Con
`LOG_LEVEL=INFO` un deploy no filtra montos ni respuestas del LLM a sus logs; con
`DEBUG` sale todo, y por eso `DEBUG` es solo para desarrollo local.

Dos detalles de implementación:

- Los mensajes se arman con `logger.debug("... %s", valor)` y no con f-strings. Con
  f-string el texto se construye siempre, aunque el nivel esté apagado y el mensaje
  se descarte.
- **`LOG_LEVEL` se aplica solo a los módulos del proyecto**, con una lista blanca en
  `main.py`; el resto del mundo queda en `WARNING`. Se hizo así después de fallar
  con el enfoque inverso: se listaron las librerías ruidosas conocidas (`httpx`,
  `httpcore`, `asyncio`, los SDK) y se escapó `hpack`, que en `DEBUG` imprime cada
  header HTTP/2 — **incluida la apikey de Supabase en texto plano**. Una lista de
  librerías a silenciar nunca está completa; una lista de módulos propios sí.

---

## Agentes

### Contrato común (`core/agents/base.py`) — IMPLEMENTADO

Todo sub-agente implementa la interfaz `Agent`: atributos `name` y `description`
(el orquestador arma su prompt con las descripciones — actualizar la descripción
cada vez que un agente gana una capacidad), y un método
`handle(message, intent, instruction) -> AgentResult`.
`AgentResult` lleva `text` (respuesta), `data` (datos estructurados para encadenar)
y `success`.

Convención de organización: **agente simple = archivo, agente complejo = carpeta**
con `agent.py` (la clase), `prompt.py` (su system prompt) y `operations.py`
(operaciones validadas). Cada carpeta es autocontenida y extraíble como skill.

### Loop agéntico (`core/agents/loop.py`) — IMPLEMENTADO

El Orquestador y el Financial Agent comparten la misma mecánica: preguntarle al LLM
qué hacer, ejecutarlo, mostrarle el resultado, y repetir hasta que responda o se
agoten las vueltas. Esa mecánica vive en `AgentLoop`, una sola vez.

Encapsula: el loop acotado por `max_iterations`, el parseo de la decisión (incluida la
limpieza del envoltorio markdown que a veces mete el LLM), la alimentación del
historial, y el corte por iteraciones.

**No conoce agentes ni tools.** Recibe un catálogo `dict[str, Accion]` desde afuera
(principio D de SOLID). Lo único que sabe del protocolo es que `respond` termina — que
no es una acción de dominio sino su forma de cortar. La diferencia entre los dos que lo
usan queda reducida a qué acciones entienden: el orquestador registra `call_agent`, el
financial registra `read`.

Devuelve un `LoopOutcome` (`text` + `success`) y no un `AgentResult` ni un `str`: el
loop no sabe quién lo llama, así que entrega lo mínimo y cada uno lo envuelve como le
corresponde (principio I). Los tres mensajes de salida —parseo fallido, iteraciones
agotadas, y el aviso de formato inválido que va al LLM— se inyectan con `LoopMessages`,
porque el orquestador le habla al usuario final y un sub-agente le habla al orquestador.

Se arma **por llamada**, no en el constructor del agente: el catálogo del orquestador
necesita el mensaje y el intent de esa corrida, y `main.py` procesa mensajes en
paralelo. Guardarlos en `self` mezclaría dos conversaciones.

Al unificar se arreglaron dos cosas que estaban desparejas entre los dos loops: el
orquestador no le avisaba al LLM cuando elegía una acción inexistente (le mandaba el
mismo prompt las 5 vueltas, sin forma de corregirse), y un JSON válido que no fuera un
objeto —`["read"]`, `42`— pasaba el parseo y reventaba después con `AttributeError`.
Los dos quedaron cubiertos en `tests/test_agent_loop.py`.

### Router (`agents/router.py`) — IMPLEMENTADO
Clasifica cada mensaje en un intent (enum `core/intents.py`) usando un LLM.
Valida la respuesta contra el enum; si no matchea, cae en `desconocido`.
No tiene lógica de negocio.

### Orquestador (`agents/orchestrator.py`) — IMPLEMENTADO
El "agente principal". Recibe el mensaje ya clasificado y decide cómo resolverlo:
a qué sub-agente llamar, con qué instrucción, y si encadenar varios. Reemplazó al
`match intent:` provisorio de `main.py`.

Funcionamiento: usa el `AgentLoop` de `core/agents/loop.py` (ver arriba), registrando
una sola acción: `call_agent`. Su LLM responde JSON:
`{"action": "call_agent", "agent": ..., "instruction": ...}` o
`{"action": "respond", "text": ...}`. Las defensas —JSON validado, límite de
iteraciones (default 5) contra loops infinitos, y el aviso al LLM cuando el formato es
inválido— viven en el loop. Lo propio del orquestador es informarle al LLM cuando el
agente que pidió no existe.

Recibe los sub-agentes inyectados por constructor (lista en `main.py`). Agregar
un agente nuevo no requiere tocar el orquestador (principio O de SOLID).

### Financial Agent (`agents/financial/`) — IMPLEMENTADO (solo lectura)
Sub-agente financiero, por ahora de **solo lectura**. Cumple el contrato `Agent`,
así que el orquestador lo llama igual que a cualquier otro sub-agente. Su LLM elige
una tool de una **lista blanca**, el código la ejecuta (solo `db.select`) y el LLM
narra el resultado. Usa el mismo `AgentLoop` que el orquestador (ver arriba),
registrando la acción `read`. Protocolo JSON con `{"action": "read", ...}` /
`{"action": "respond", ...}`. No tiene ninguna tool que escriba, así que no puede
mutar la base.

No conoce ninguna implementación concreta: recibe una `list[Tool]` armada en
`main.py` con los catálogos de `tools/reads/financial.py` y `reports/financial.py`
(ver sección Tools). Todas sus dependencias son contratos —`Agent`, `AgentLoop`,
`LLMProvider`, `Tool`—: no importa ni `FinancialReadTools` ni `FinancialReports`.

Las tools que hoy tiene registradas:

| Tool | Qué lee |
|---|---|
| `buscar_cuentas(nombre?)` | `finanzas.cuenta` — cuentas con saldo, tipo y moneda. |
| `listar_ingresos_previstos(estado?)` | `finanzas.ingreso_previsto` — por default los `pendiente` (cobros a recibir). |
| `listar_egresos_previstos(estado?)` | `finanzas.egreso_previsto` — por default los `pendiente` (pagos a hacer). |
| `listar_ingresos_efectuados(mes?)` | `finanzas.ingreso_efectuado` — cobros concretados. `mes` en formato `AAAA-MM`; sin él devuelve todos. |
| `listar_egresos_efectuados(mes?)` | `finanzas.egreso_efectuado` — pagos concretados. `mes` en formato `AAAA-MM`; sin él devuelve todos. |

Las dos de efectuados cambian el `id_cuenta` por el nombre de la cuenta antes de
devolver: un UUID crudo no le dice nada al usuario, y resolver el cruce en la tool
evita que el agente tenga que juntar dos listas a ojo —trabajo que no conviene
delegarle a un LLM— y le ahorra una vuelta de loop. Si un id no matchea con ninguna
cuenta se deja como estaba, para que un dato inconsistente se vea en vez de
desaparecer.

Y los reportes de `reports/financial.py` (ver sección Reportes):

| Reporte | Qué calcula |
|---|---|
| `resultado_mensual_por_moneda(mes?)` | Resultado de un mes: ingresos menos egresos efectuados, agrupado por moneda. |

Probado end-to-end por Telegram: consultas de cuentas (multi-moneda ARS/USD/EUR),
cobros y pagos previstos (filtrando por estado) y efectuados, y el resultado
mensual por moneda (con mes explícito y sin él).

**La fecha de hoy se le pasa en el contexto** (`agents/financial/agent.py`, en el
primer mensaje del historial). Un LLM no tiene forma de saber en qué día está: sin
esto, ante un "este mes" o un "julio" adivinaría el período y devolvería datos de
otro mes sin que nada avise. Con la fecha adelante resuelve "julio" → `2026-07`
solo.

**Su prompt lleva tres reglas que no son de formato sino de honestidad**, agregadas
después de que el agente presentara movimientos sin filtrar como si fueran "de
Luciano" y "de este mes":
- No afirmar condiciones que no aplicó.
- Si un filtro del pedido no lo cubre ninguna tool, decirlo y entregar igual lo que
  sí puede, en la misma respuesta.
- Si hay un reporte que ya responde el pedido, usarlo en vez de combinar tools a
  mano (ver Pendientes: son garantías probabilísticas, no del código).

> Historia: existió una v1 de este agente con operaciones de **escritura**
> (`crear_cuenta`, `registrar_egreso`, `registrar_ingreso_efectuado`,
> `resumen_mensual`, etc.) validadas en un `operations.py`. Se descartó para
> consolidar en un único agente de lectura; esa lógica y sus validaciones (montos
> positivos, moneda del movimiento = moneda de la cuenta, conciliación de previstos)
> quedan en el historial de git para recuperar cuando se reimplemente la escritura.

Config propia: `FINANCIAL_AGENT_PROVIDER` / `FINANCIAL_AGENT_MODEL` (`.env` + `config/aixo.py`).

### Conversation Agent — A IMPLEMENTAR
Presenta información al usuario en lenguaje natural. Maneja el ida y vuelta conversacional.

### Report Agent — A IMPLEMENTAR
Genera reportes, proyecciones y resúmenes financieros.

### Sub-agente ARCA (`agents/arca/`) — PRÓXIMO PASO
Primer sub-agente de facturación. Reutiliza el motor de facturación ya existente
(emite Factura C vía WSFEv1) para facturar sin entrar al portal de ARCA ni hacer
el proceso manual. El orquestador interpreta el pedido del usuario y delega en
este sub-agente, que ejecuta el proceso completo: emisión, registro en el schema
`facturacion`, y creación automática del `finanzas.ingreso_previsto` vinculado.

---

## Tools

Las herramientas que usan los agentes viven en su **propia carpeta** (`tools/`),
separadas de cualquier agente, para poder ser reutilizadas por varios. Se
**inyectan por constructor** (el armado pasa en `main.py`); el agente no las crea
ni las tiene adentro, solo las recibe.

Organización **por acceso**: `tools/reads/` contiene únicamente tools de lectura
(solo llaman `db.select`, nunca escriben). La carpeta es la frontera que garantiza
que un agente de solo lectura no pueda mutar la base, por construcción. Cuando haga
falta, se sumará `tools/writes/` para las de escritura.

### El contrato (`core/tools/base.py`) → `Tool`

Una tool es un objeto con cuatro campos: `nombre` (lo que el LLM escribe en
`{"tool": ...}`), `argumentos` (la firma en texto, ej `mes?`), `descripcion` (qué hace
y qué significa cada argumento) y `ejecutar` (el método, ya atado a su instancia). Es
un dataclass congelado: una tool no cambia después de armada.

El contrato es **genérico** —no menciona finanzas, igual que `Agent` o `LLMProvider`—
así que cualquier sub-agente futuro lo usa sin copiar nada.

Cada clase de tools **se describe a sí misma** con un método `catalogo() -> list[Tool]`.
La descripción vive al lado del método que describe y no en el composition root: si el
texto queda lejos del código se desincroniza sin que nada falle (ya pasó con
`buscar_cuentas` — ver Pendientes).

`main.py` concatena los catálogos y se los pasa al agente:

```python
tools=_lecturas.catalogo() + _reportes.catalogo()
```

El agente arma su lista blanca con `{tool.nombre: tool}` y no conoce ninguna
implementación concreta (principio D de SOLID). Qué puede tocar cada agente queda
visible en el composition root, que es donde viven las decisiones de política.

Implementado: `tools/reads/financial.py` → `FinancialReadTools`
(`buscar_cuentas`, `listar_ingresos_previstos`, `listar_egresos_previstos`,
`listar_ingresos_efectuados`, `listar_egresos_efectuados`).

## Reportes

Un **reporte** devuelve números ya calculados; una **tool** devuelve datos crudos.
Viven separados (`reports/`, hermana de `tools/`) porque son cosas distintas, pero
conviven en la misma lista blanca del agente: para el LLM los dos son "algo que
puedo pedir", y los dos son de solo lectura.

Regla que justifica que existan: **la aritmética con dinero la hace siempre el
código, nunca el LLM.** Un LLM predice texto, no calcula. El LLM elige qué reporte
pedir; los números los pone el código.

Los reportes dependen de la abstracción `DatabaseClient` y se inyectan por
constructor desde `main.py`, igual que las tools. No consumen las tools: son sus
pares, no sus clientes.

Y se describen igual: `FinancialReports.catalogo()` devuelve sus `Tool`, que se
concatenan con las de lectura antes de llegar al agente. Para el agente los dos son lo
mismo; la diferencia entre datos crudos y números calculados importa del lado de quien
los produce.

Implementado: `reports/financial.py` → `FinancialReports`

| Reporte | Qué calcula |
|---|---|
| `resultado_mensual_por_moneda(mes?)` | Ingresos efectuados menos egresos efectuados de un mes, agrupado por moneda. `mes` en formato `AAAA-MM`; sin argumento, el mes actual. Devuelve `Decimal` con 2 decimales. |

Detalles de implementación: agrupa por las monedas presentes en los datos (no por
una lista fija), nunca suma monedas distintas entre sí, y el filtro por mes se hace
en Python porque `DatabaseClient` solo filtra por igualdad exacta.

## Base de datos

Supabase. Proyecto: `aixo.bdd`.

El schema `finanzas` contiene toda la lógica financiera del agente.
El schema `facturacion` contiene las tablas del subagente de facturación ARCA.
El schema `public` contiene la estructura de la empresa (fuera del scope de este agente).

### Estado actual

**Creadas en Supabase** (DDL versionado en `db/migrations/001_finanzas.sql`, que es
la fuente de verdad de los tipos exactos): `cuenta`, `ingreso_previsto`,
`egreso_previsto`, `ingreso_efectuado`, `egreso_efectuado`.

**Pendientes de crear**: `inversion`, `prestamo`, `snapshot_cuenta`,
`snapshot_inversion`, `snapshot_prestamo` (schema `finanzas`) y las tres de
`facturacion` (se crean junto con el sub-agente ARCA).

Decisiones de tipos (aplican a todo lo que se cree de acá en adelante):
- Montos en `numeric(15,2)`, nunca `float8` — la coma flotante comete errores de redondeo y con dinero es inaceptable.
- Timestamps en `timestamptz` — con zona horaria, Supabase almacena en UTC.
- `CHECK` constraints en campos de moneda/tipo/estado — la base rechaza valores fuera de lista (última defensa contra alucinaciones del LLM).
- Las columnas FK hacia `public` (`id_proyecto`, `id_costo_fijo`, `id_costo_variable`) existen pero **sin constraint todavía**; se agregan en una migración futura. Nota: la tabla real es `public.cliente` (singular), no `clientes` como decía el diseño original.

Seguridad y acceso:
- **RLS activado en todas las tablas.** La anon/publishable key no accede a nada.
- El agente usa la **secret key** (`service_role`), que saltea RLS.
- Los schemas propios requieren dos pasos manuales en Supabase: exponerlos en
  Settings → Data API → Exposed schemas, y otorgar permisos al rol
  (`grant usage/all ... to service_role`, incluidos al final de la migración 001).

### Schema `finanzas`

Contiene toda la lógica financiera del agente: movimientos de dinero
y proyecciones. Es el núcleo del sistema — todos los demás schemas se conectan con
este a través de FKs.

#### `cuenta`
Cuentas bancarias, billeteras virtuales o efectivo donde se mueve el dinero.
Cada operación que mueve plata actualiza `saldo_actual` automáticamente.

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | `uuid` | PK |
| `nombre` | `text` | |
| `tipo` | `text` | `bancaria`, `billetera_virtual`, `efectivo` |
| `moneda` | `text` | `ARS`, `USD`, `EUR` |
| `saldo_actual` | `float8` | Se actualiza con cada movimiento |
| `created_at` | `timestamp` | |
| `edited_at` | `timestamp` | |

---

#### `ingreso_previsto`
Ingresos esperados asociados a un proyecto. Se generan al confirmar un deal.

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | `uuid` | PK |
| `id_proyecto` | `uuid` | FK → `public.proyecto` |
| `descripcion` | `text` | Nullable |
| `monto` | `float8` | |
| `moneda` | `text` | `ARS`, `USD`, `EUR` |
| `fecha_esperada` | `date` | |
| `estado` | `text` | `pendiente`, `confirmado`, `cancelado` |
| `created_at` | `timestamp` | |
| `edited_at` | `timestamp` | |

---

#### `egreso_previsto`
Egresos esperados asociados a un costo fijo. Se generan periódicamente por cron.

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | `uuid` | PK |
| `id_costo_fijo` | `uuid` | FK → `public.costo_fijo` |
| `descripcion` | `text` | Nullable |
| `monto` | `float8` | |
| `moneda` | `text` | `ARS`, `USD`, `EUR` |
| `fecha_esperada` | `date` | |
| `estado` | `text` | `pendiente`, `confirmado`, `cancelado` |
| `created_at` | `timestamp` | |
| `edited_at` | `timestamp` | |

---

#### `ingreso_efectuado`
Ingresos que realmente ocurrieron. Pueden o no estar asociados a un ingreso previsto.

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | `uuid` | PK |
| `id_ingreso_previsto` | `uuid` | FK → `ingreso_previsto`, Nullable |
| `id_proyecto` | `uuid` | FK → `public.proyecto` |
| `descripcion` | `text` | Nullable |
| `monto` | `float8` | |
| `moneda` | `text` | `ARS`, `USD`, `EUR` |
| `fecha_efectiva` | `date` | |
| `id_cuenta` | `uuid` | FK → `cuenta` |
| `comprobante` | `text` | URL al archivo, Nullable |
| `created_at` | `timestamp` | |
| `edited_at` | `timestamp` | |

---

#### `egreso_efectuado`
Egresos que realmente ocurrieron. Pueden venir de un egreso previsto o de un costo variable.

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | `uuid` | PK |
| `id_egreso_previsto` | `uuid` | FK → `egreso_previsto`, Nullable |
| `id_costo_variable` | `uuid` | FK → `public.costo_variable`, Nullable |
| `descripcion` | `text` | Nullable |
| `monto` | `float8` | |
| `moneda` | `text` | `ARS`, `USD`, `EUR` |
| `fecha_efectiva` | `date` | |
| `id_cuenta` | `uuid` | FK → `cuenta` |
| `comprobante` | `text` | URL al archivo, Nullable |
| `created_at` | `timestamp` | |
| `edited_at` | `timestamp` | |

---

#### `inversion`
Inversiones abiertas o cerradas. Soporta crypto, acciones, plazos fijos y fondos.
El campo `capital_recuperado` acumula los cierres parciales para calcular rentabilidad real.
Nada es ganancia hasta que se recuperó el capital original (`monto_inicio`).

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | `uuid` | PK |
| `id_cuenta` | `uuid` | FK → `cuenta` |
| `descripcion` | `text` | Nullable |
| `tipo` | `text` | `plazo_fijo`, `fondo_comun`, `accion`, `crypto`, `otro` |
| `ticker` | `text` | Símbolo para consulta de precio externo, Nullable |
| `cantidad` | `float8` | Unidades compradas, Nullable |
| `precio_compra` | `float8` | Precio unitario al momento de compra, Nullable |
| `tasa_anual` | `float8` | Para plazo fijo y fondos, Nullable |
| `monto_inicio` | `float8` | Capital invertido original |
| `monto_actual` | `float8` | Valor actual, se actualiza con `recalcular_inversion` |
| `monto_cierre` | `float8` | Valor al cerrar, Nullable |
| `capital_recuperado` | `float8` | Acumulado de cierres parciales, arranca en 0 |
| `moneda` | `text` | `ARS`, `USD`, `EUR` |
| `fecha_inicio` | `date` | |
| `fecha_vencimiento` | `date` | Para plazo fijo, Nullable |
| `estado` | `text` | `activa`, `finalizada` |
| `created_at` | `timestamp` | |
| `edited_at` | `timestamp` | |

---

#### `prestamo`
Préstamos otorgados o recibidos. `monto_pendiente` se actualiza con cada pago.
Si un pago cubre el total, el préstamo se cierra automáticamente (`estado = saldado`).

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | `uuid` | PK |
| `id_cuenta` | `uuid` | FK → `cuenta` |
| `descripcion` | `text` | Nullable |
| `tipo` | `text` | `otorgado`, `recibido` |
| `monto_original` | `float8` | |
| `monto_pendiente` | `float8` | Se actualiza con cada pago |
| `moneda` | `text` | `ARS`, `USD`, `EUR` |
| `fecha_inicio` | `date` | |
| `fecha_vencimiento` | `date` | Nullable |
| `estado` | `text` | `activo`, `saldado`, `cancelado` |
| `created_at` | `timestamp` | |
| `edited_at` | `timestamp` | |

---

#### `snapshot_cuenta`
Historial diario del saldo de cada cuenta.
Lo genera el cron `generar_snapshots_diarios` una vez por día.
Permite consultar evolución histórica del flujo de caja.

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | `uuid` | PK |
| `id_cuenta` | `uuid` | FK → `cuenta` |
| `saldo` | `float8` | |
| `fecha` | `date` | |
| `created_at` | `timestamp` | |

---

#### `snapshot_inversion`
Historial diario del valor de cada inversión.
Permite detectar cambios abruptos y generar evolución histórica.

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | `uuid` | PK |
| `id_inversion` | `uuid` | FK → `inversion` |
| `monto` | `float8` | |
| `fecha` | `date` | |
| `created_at` | `timestamp` | |

---

#### `snapshot_prestamo`
Historial diario del monto pendiente de cada préstamo.
Permite reconstruir la evolución de deudas a lo largo del tiempo.

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | `uuid` | PK |
| `id_prestamo` | `uuid` | FK → `prestamo` |
| `monto_pendiente` | `float8` | |
| `fecha` | `date` | |
| `created_at` | `timestamp` | |

---

## Cron Jobs

- `generar_snapshots_diarios` — registra el estado actual de cuentas, inversiones y préstamos.
- `preveer_egreso` — genera egresos previstos desde costos fijos.
- `preveer_ingreso` — genera ingresos previstos desde proyectos activos.
- `efectuar_egreso` — ejecuta egresos planificados en automático.
- Reportes periódicos — genera resúmenes financieros.
- Alertas — detecta riesgos, vencimientos y cambios relevantes.

*Frecuencias: a definir.*

---

## Schema `facturacion`

Tablas propias del subagente de facturación ARCA. Este schema es el dominio
exclusivo del subagente ARCA — ningún otro agente escribe acá directamente.
El resto del sistema consume esta información únicamente a través del vínculo
`ingreso_id` → `finanzas.ingreso_previsto`. Se conecta además con `public`
a través de `cliente_public_id`.

#### `clientes`
Ficha fiscal de cada receptor de facturas. Se carga manualmente una vez y el agente
la reutiliza en cada factura. Separada de `public.clientes` porque contiene datos
tributarios específicos de facturación.

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | `uuid` | PK |
| `cliente_public_id` | `uuid` | FK → `public.clientes`, Nullable. Vínculo con el cliente comercial. |
| `alias` | `text` | Nombre corto conversacional ("Sigma"). Clave de búsqueda del agente. UNIQUE. |
| `doc_tipo` | `smallint` | Tipo de documento ARCA: 80=CUIT, 96=DNI, 99=Consumidor Final. Default 80. |
| `doc_nro` | `text` | Número de documento (CUIT sin guiones). |
| `razon_social` | `text` | Razón social o apellido y nombre. |
| `domicilio` | `text` | Nullable. Se imprime en el PDF. |
| `condicion_iva` | `text` | Condición frente al IVA (ej: "IVA Responsable Inscripto"). |
| `condicion_venta_default` | `text` | Medio de pago habitual (ej: "Transferencia Bancaria"). Pisable por factura. |
| `plazo_pago_dias` | `integer` | Plazo habitual de pago. El agente calcula vencimiento como emisión + plazo. |
| `email` | `text` | Nullable. Para envío futuro del comprobante. |
| `activo` | `boolean` | Default true. Baja lógica. |
| `created_at` | `timestamptz` | |

---

#### `factura_arca`
Un registro por comprobante emitido. Los comprobantes con CAE son inmutables —
nunca se borran ni editan; se anulan emitiendo una nota de crédito vinculada.

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | `uuid` | PK |
| `entorno` | `text` | `testing`, `produccion`. Las de testing no generan ingresos. |
| `pto_vta` | `integer` | Punto de venta ARCA. |
| `cbte_tipo` | `smallint` | Código ARCA: 11=Factura C, 6=B, 1=A, 13=NC C, 8=NC B, 3=NC A. |
| `cbte_nro` | `integer` | Número correlativo. Lo asigna ARCA, nunca un contador propio. |
| `fecha_emision` | `date` | |
| `cliente_id` | `uuid` | FK → `facturacion.clientes` |
| `doc_tipo` | `smallint` | Foto del documento al momento de emitir. |
| `doc_nro` | `text` | Foto del CUIT al momento de emitir. |
| `condicion_iva_receptor` | `text` | Obligatoria desde RG 5616 (01/09/2026). |
| `condicion_venta` | `text` | Medio de pago de esta factura. |
| `concepto` | `smallint` | 1=Productos, 2=Servicios, 3=Ambos. |
| `descripcion` | `text` | Texto libre de la operación. Nullable. |
| `importe_total` | `numeric(15,2)` | Total del comprobante. |
| `imp_neto` | `numeric(15,2)` | Importe neto gravado. Default 0. |
| `imp_iva` | `numeric(15,2)` | IVA total. 0 en Factura C. Default 0. |
| `imp_trib` | `numeric(15,2)` | Otros tributos. Default 0. |
| `imp_op_ex` | `numeric(15,2)` | Operaciones exentas. Default 0. |
| `imp_tot_conc` | `numeric(15,2)` | Conceptos no gravados. Default 0. |
| `moneda` | `text` | Código ARCA: `PES`, `DOL`, `EUR`. Default `PES`. |
| `cotizacion` | `numeric(12,6)` | Tipo de cambio usado. Default 1. |
| `fch_serv_desde` | `date` | Inicio del período de servicio. Nullable (solo concepto 2 o 3). |
| `fch_serv_hasta` | `date` | Fin del período de servicio. Nullable. |
| `fch_vto_pago` | `date` | Vencimiento del pago. Se usa como fecha esperada del `ingreso_previsto`. |
| `cae` | `text` | Código de Autorización Electrónico. Sin CAE el comprobante no existe legalmente. |
| `cae_vencimiento` | `date` | Validez administrativa del CAE (~10 días). NO es el vencimiento de pago. |
| `observaciones_arca` | `jsonb` | Nullable. Observaciones que devuelve ARCA al aprobar. |
| `estado` | `text` | `emitida`, `anulada`. Default `emitida`. |
| `comprobante_asociado_id` | `uuid` | FK → `factura_arca`. La NC apunta a la factura que anula. Nullable. |
| `origen` | `text` | `chat`, `cotizacion`, `manual`. Auditoría del origen del comprobante. |
| `idempotency_key` | `text` | UNIQUE. Previene duplicar una factura si el agente reintenta tras un corte. |
| `pdf_url` | `text` | Nullable. URL del PDF generado. |
| `ingreso_id` | `uuid` | FK → `finanzas.ingreso_previsto`. Puente con el sistema financiero. |
| `created_at` | `timestamptz` | Auditoría técnica. Distinto de `fecha_emision`. |

> UNIQUE (entorno, pto_vta, cbte_tipo, cbte_nro) — defensa contra duplicados fiscales.

---

#### `factura_items`
Un registro por renglón de la factura. ARCA nunca ve estos datos — existen para
regenerar el PDF y para reportes por categoría.

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | `uuid` | PK |
| `factura_id` | `uuid` | FK → `factura_arca`. |
| `orden` | `smallint` | Posición del renglón para regenerar el PDF en orden original. |
| `codigo` | `text` | Nullable. Código del producto/servicio. |
| `descripcion` | `text` | Producto o servicio (ej: "Consultoría"). |
| `cantidad` | `numeric(12,2)` | Default 1. |
| `unidad` | `text` | Nullable. Unidad de medida. |
| `precio_unit` | `numeric(15,2)` | Precio unitario en la moneda de la factura. |
| `pct_bonif` | `numeric(5,2)` | Bonificación en porcentaje. Default 0. |
| `imp_bonif` | `numeric(15,2)` | Bonificación en importe. Default 0. |
| `subtotal` | `numeric(15,2)` | Subtotal del renglón. |
| `categoria` | `text` | Nullable. Usar misma lista que `finanzas.ingreso_efectuado` para reportes. |

---

## Reglas de integración entre schemas

1. **Emitir ≠ cobrar.** Al emitirse una factura se crea un `finanzas.ingreso_previsto`
   con `fch_vto_pago` como fecha esperada. Cuando se detecte el cobro, pasa a
   `ingreso_efectuado`. `factura_arca.ingreso_id` mantiene el vínculo.
2. **Solo producción genera ingresos.** Los registros con `entorno = 'testing'` nunca
   crean ingresos ni entran en reportes financieros.
3. **Anulación.** Una NC vinculada debe marcar la factura original como `anulada`
   y revertir el ingreso previsto asociado.
4. **Numeración.** La fuente de verdad del próximo número es ARCA, no la base.
   La tabla registra lo emitido; nunca se usa para calcular numeración.
5. **Inmutabilidad.** Filas de `factura_arca` con CAE no se actualizan (salvo
   `estado`, `pdf_url`, `ingreso_id`) ni se borran.

---

## Flujo de un mensaje

Ejemplo real (probado): *"¿qué cobros tengo pendientes?"*

1. `providers/messaging/telegram.py` recibe el mensaje y lo normaliza a `IncomingMessage`,
   y se lo entrega al `dispatch` de `main.py`, que lo lanza como tarea y vuelve
   enseguida (ver Concurrencia). Los pasos que siguen corren en esa tarea, en
   paralelo con los de cualquier otro mensaje que esté en curso.
2. `core/preprocessing/preprocessor.py` lo deja en texto (si era audio lo transcribe;
   si era imagen la describe con visión).
3. `agents/router.py` lo etiqueta con un intent (ej: `consulta_informacion`).
4. `agents/orchestrator.py` decide: `call_agent` → `financial`, con una instrucción específica.
5. `agents/financial/agent.py` resuelve con su mini-loop: elige la tool
   `listar_ingresos_previstos`, el código la ejecuta (solo `db.select`) y devuelve
   los cobros pendientes.
6. El resultado vuelve al orquestador, que redacta la respuesta final (`respond`).
7. `main.py` (`handle()`) se la pasa a `telegram.py`, que la envía al usuario.

Patrón general: dos niveles de LLM decidiendo en menús cada vez más chicos
(orquestador elige agente → agente elige tool), y al final siempre código
determinista tocando la base — hoy solo lectura.

---

## Flujo de un evento externo

*A definir.*

---

## Pendientes técnicos anotados

Detectados durante la construcción; ninguno es bloqueante hoy:

- **Memoria conversacional**: el sistema no recuerda mensajes anteriores. El intent
  `respuesta_agente` existe pero nada lo maneja — si un agente pregunta algo, la
  respuesta del usuario llega sin contexto. Los prompts mitigan esto haciendo que
  los agentes resuelvan solos (ej: buscar montos en la base) en vez de preguntar.
- **PDFs sin procesar**: el Preprocessor procesa imágenes con visión, pero los
  documentos PDF pasan de largo. Por ahora: mandar captura de pantalla.
- **Idempotencia de movimientos**: cuando se reimplemente la escritura, mensajes
  repetidos podrían generar registros duplicados (pasó en pruebas con un gasto
  cargado dos veces). ARCA ya lo prevé con `idempotency_key`; para el agente de
  escritura futuro falta detectar duplicados sospechosos y preguntar.
- **`edited_at` no se actualiza solo**: falta trigger en la base o seteo desde el código.
- **Un solo schema por corrida**: el schema ya no está hardcodeado —viaja desde
  `DATABASE_SCHEMA`— pero `get_client()` cachea un único cliente, así que el sistema
  habla con un solo schema a la vez. Nada puede leer `public` (los `cliente`,
  `proyecto` y `usuario` de Luciano) mientras usa `finanzas`. Cuando ARCA necesite
  `facturacion` en paralelo, hay que hacer que el factory reciba el schema y guarde
  uno por cada uno. El cambio queda contenido en `db/client.py`.
- **`LOG_LEVEL` en el servidor**: los `print` de debug ya son `logger.debug`, así que
  no hay nada que sacar del código — pero el deploy tiene que arrancar con
  `LOG_LEVEL=INFO`. Con `DEBUG` los montos y las respuestas del LLM van enteros a
  los logs.
- **Confirmación previa a escrituras**: evaluar que operaciones que escriben pidan
  confirmación por Telegram antes de ejecutar (requiere memoria conversacional).
- **El orden de los mensajes ya no está garantizado**: desde que `main.py` despacha
  cada mensaje como tarea, dos mensajes seguidos pueden terminar al revés — el
  segundo contesta antes si necesita menos pasos (verificado en pruebas). Hoy es
  inofensivo porque el agente es de solo lectura. **Bloqueante para reimplementar la
  escritura**: "cargá un gasto de 100" seguido de "no, eran 200" podría aplicarse
  invertido. Va junto con la race condition de abajo. Salida propuesta: procesar en
  paralelo entre chats distintos, pero secuencialmente dentro del mismo chat.
- **Race condition en el saldo**: la escritura vieja hacía `saldo = leer` →
  `saldo - monto` → `escribir`, sin transacción. Con procesamiento concurrente, dos
  movimientos sobre la misma cuenta pueden leer el mismo saldo y pisarse. Resolver
  antes de reactivar la escritura.
- **`DatabaseClient` sigue siendo sincrónico**: `providers/db/supabase.py` usa el
  cliente sync de supabase-py, así que cada `select` bloquea el event loop. Es el
  mismo problema que se arregló en `LLMProvider`, pero mucho menos grave: una query
  tarda decenas de milisegundos contra los segundos de un LLM. Migrar cuando moleste.
- **El orquestador reescribe respuestas que ya estaban bien**: cuando llama a un
  solo agente y ese agente contesta correctamente, el orquestador igual gasta una
  llamada al LLM para redactar de nuevo lo mismo (visto en pruebas: dos segundos y
  un texto idéntico al del agente). La salida es lo caro y lo lento — el modelo la
  genera token por token. **Que la decisión la tome el código, no el LLM**: si se
  llamó a un solo agente y devolvió `success=True`, pasar su texto tal cual sin
  consultar al modelo. Preguntarle al LLM "¿esta respuesta está bien?" cambiaría un
  ahorro chico por un riesgo de calidad. Contra: se pierden los casos donde el
  orquestador querría agregar contexto — hoy no aplica porque hay un solo agente.
- **La descripción de cada tool está escrita dos veces**: en el `catalogo()` de la
  tool y a mano en `agents/financial/prompt.py`. Es temporal y a propósito: el contrato
  `Tool` ya lleva la descripción justamente para que el prompt la genere solo, pero ese
  cambio es un ticket aparte. Hasta entonces, tocar una obliga a tocar la otra.
- **Las garantías del prompt son probabilísticas**: las reglas que evitan que el
  agente afirme filtros que no aplicó viven en su prompt, no en el código. Funcionan
  casi siempre, no siempre. Los montos sí están blindados (los calcula el código);
  las etiquetas que los acompañan, no. Tenerlo presente antes de exponer el agente a
  alguien que no sea del equipo.
