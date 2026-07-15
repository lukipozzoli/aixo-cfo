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
Los detalles de cada agente y sus flujos se irán definiendo iterativamente.

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
Métodos: `chat(messages)`, `complete(prompt)`
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

## Agentes

### Financial Agent
Maneja toda la lógica de negocio financiera: registra movimientos, concilia, proyecta.
*Detalle: a definir.*

### Router
Recibe mensajes normalizados desde el proveedor de mensajería y los clasifica para derivarlos al agente correcto.
*Detalle: a definir.*

### Conversation Agent
Presenta información al usuario en lenguaje natural. Maneja el ida y vuelta conversacional.
*Detalle: a definir.*

### Report Agent
Genera reportes, proyecciones y resúmenes financieros.
*Detalle: a definir.*

---

## Base de datos

Supabase. Proyecto: `finanzas`.

El schema `finanzas` contiene toda la lógica financiera del agente.
El schema `facturacion` contiene las tablas del subagente de facturación ARCA.
El schema `public` contiene la estructura de la empresa (fuera del scope de este agente).

### Schema `finanzas`

Contiene toda la lógica financiera del agente: movimientos de dinero, liquidaciones
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

#### `liquidacion_mensual`
Liquidación mensual de ganancias entre socios.
Se calcula a fin de mes sobre los ingresos y egresos efectuados del período.

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | `uuid` | PK |
| `periodo` | `date` | Primer día del mes (ej: 2025-07-01) |
| `moneda` | `text` | `ARS`, `USD` |
| `tipo_cambio_referencia` | `float8` | Tipo de cambio usado para el período, Nullable |
| `ingresos_total` | `float8` | Suma de todos los `ingreso_efectuado` del mes |
| `egresos_total` | `float8` | Suma de todos los `egreso_efectuado` del mes |
| `ganancia_neta` | `float8` | `ingresos_total - egresos_total` |
| `monto_retenido_caja` | `float8` | Lo que queda en caja sin dividir, default 0 |
| `porcentaje_socio_1` | `float8` | Default 50 |
| `porcentaje_socio_2` | `float8` | Default 50 |
| `monto_socio_1` | `float8` | |
| `monto_socio_2` | `float8` | |
| `estado` | `text` | `pendiente`, `transferido` |
| `fecha_transferencia` | `date` | Nullable |
| `notas` | `text` | Nullable |
| `created_at` | `timestamp` | |
| `edited_at` | `timestamp` | |

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

*A definir.*

---

## Flujo de un evento externo

*A definir.*
