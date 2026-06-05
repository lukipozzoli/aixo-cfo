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
- Mensajes de Telegram del usuario
- Webhooks externos (Gmail, Linear, Bancos)
- Cron jobs programados
- Llamadas desde otros agentes (Admin, Ops)

La capa de conectores normaliza todos los eventos externos a un formato estándar
antes de que lleguen al agente financiero. Esto permite agregar nuevas fuentes
sin tocar la lógica central.

---

## Base de datos

Supabase. Proyecto: `finanzas`.

El schema `finanzas` contiene toda la lógica financiera del agente.
El schema `public` contiene la estructura de la empresa (fuera del scope de este agente).

### Schema `finanzas`

#### `cuenta`
Cuentas bancarias, billeteras virtuales o efectivo donde se mueve el dinero.
Cada operación que mueve plata actualiza `saldo_actual` automáticamente.

| Columna | Tipo | Notas |
|---------|------|-------|
| `id` | `uuid` | PK |
| `nombre` | `text` | |
| `tipo` | `text` | `bancaria`, `billetera_virtual`, `efectivo` |
| `moneda` | `text` | `ARS`, `USD` |
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
| `moneda` | `text` | `ARS`, `USD` |
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
| `moneda` | `text` | `ARS`, `USD` |
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
| `moneda` | `text` | `ARS`, `USD` |
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
| `moneda` | `text` | `ARS`, `USD` |
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
| `moneda` | `text` | `ARS`, `USD` |
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
| `moneda` | `text` | `ARS`, `USD` |
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

## Flujo de un mensaje

*A definir.*

---

## Flujo de un evento externo

*A definir.*
