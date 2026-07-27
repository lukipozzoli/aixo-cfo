-- 001_finanzas.sql — Schema finanzas: tablas base del agente CFO.
-- Pendiente: FKs hacia public (proyecto, costo_fijo, costo_variable)
-- se agregarán cuando esas tablas existan. Las columnas ya quedan creadas.

create schema if not exists finanzas;

-- Cuentas bancarias, billeteras virtuales o efectivo donde se mueve el dinero.
create table finanzas.cuenta (
  id            uuid primary key default gen_random_uuid(),
  nombre        text not null,
  tipo          text not null check (tipo in ('bancaria', 'billetera_virtual', 'efectivo')),
  moneda        text not null check (moneda in ('ARS', 'USD', 'EUR')),
  saldo_actual  numeric(15,2) not null default 0,
  created_at    timestamptz not null default now(),
  edited_at     timestamptz not null default now()
);

-- Ingresos esperados asociados a un proyecto. Se generan al confirmar un deal.
create table finanzas.ingreso_previsto (
  id              uuid primary key default gen_random_uuid(),
  id_proyecto     uuid,  -- FK a public.proyecto pendiente (tabla aún no existe)
  descripcion     text,
  monto           numeric(15,2) not null,
  moneda          text not null check (moneda in ('ARS', 'USD', 'EUR')),
  fecha_esperada  date not null,
  estado          text not null default 'pendiente' check (estado in ('pendiente', 'confirmado', 'cancelado')),
  created_at      timestamptz not null default now(),
  edited_at       timestamptz not null default now()
);

-- Egresos esperados asociados a un costo fijo. Se generan periódicamente por cron.
create table finanzas.egreso_previsto (
  id              uuid primary key default gen_random_uuid(),
  id_costo_fijo   uuid,  -- FK a public.costo_fijo pendiente (tabla aún no existe)
  descripcion     text,
  monto           numeric(15,2) not null,
  moneda          text not null check (moneda in ('ARS', 'USD', 'EUR')),
  fecha_esperada  date not null,
  estado          text not null default 'pendiente' check (estado in ('pendiente', 'confirmado', 'cancelado')),
  created_at      timestamptz not null default now(),
  edited_at       timestamptz not null default now()
);

-- Ingresos que realmente ocurrieron. Pueden o no venir de un ingreso previsto.
create table finanzas.ingreso_efectuado (
  id                   uuid primary key default gen_random_uuid(),
  id_ingreso_previsto  uuid references finanzas.ingreso_previsto (id),
  id_proyecto          uuid,  -- FK a public.proyecto pendiente
  descripcion          text,
  monto                numeric(15,2) not null,
  moneda               text not null check (moneda in ('ARS', 'USD', 'EUR')),
  fecha_efectiva       date not null,
  id_cuenta            uuid not null references finanzas.cuenta (id),
  comprobante          text,  -- URL al archivo
  created_at           timestamptz not null default now(),
  edited_at            timestamptz not null default now()
);

-- Egresos que realmente ocurrieron. Pueden venir de un previsto o de un costo variable.
create table finanzas.egreso_efectuado (
  id                  uuid primary key default gen_random_uuid(),
  id_egreso_previsto  uuid references finanzas.egreso_previsto (id),
  id_costo_variable   uuid,  -- FK a public.costo_variable pendiente
  descripcion         text,
  monto               numeric(15,2) not null,
  moneda              text not null check (moneda in ('ARS', 'USD', 'EUR')),
  fecha_efectiva      date not null,
  id_cuenta           uuid not null references finanzas.cuenta (id),
  comprobante         text,  -- URL al archivo
  created_at          timestamptz not null default now(),
  edited_at           timestamptz not null default now()
);

-- Liquidación mensual de ganancias entre socios. Una por período y moneda.
create table finanzas.liquidacion_mensual (
  id                      uuid primary key default gen_random_uuid(),
  periodo                 date not null,  -- primer día del mes (ej: 2026-07-01)
  moneda                  text not null check (moneda in ('ARS', 'USD')),
  tipo_cambio_referencia  numeric(12,6),
  ingresos_total          numeric(15,2) not null,
  egresos_total           numeric(15,2) not null,
  ganancia_neta           numeric(15,2) not null,
  monto_retenido_caja     numeric(15,2) not null default 0,
  porcentaje_socio_1      numeric(5,2) not null default 50,
  porcentaje_socio_2      numeric(5,2) not null default 50,
  monto_socio_1           numeric(15,2) not null,
  monto_socio_2           numeric(15,2) not null,
  estado                  text not null default 'pendiente' check (estado in ('pendiente', 'transferido')),
  fecha_transferencia     date,
  notas                   text,
  created_at              timestamptz not null default now(),
  edited_at               timestamptz not null default now(),
  unique (periodo, moneda)  -- evita liquidar dos veces el mismo mes en la misma moneda
);

-- Permisos del schema finanzas para el rol de backend (service_role).
-- Solo service_role: la anon key queda sin acceso, como corresponde.
grant usage on schema finanzas to service_role;
grant all on all tables in schema finanzas to service_role;
alter default privileges in schema finanzas grant all on tables to service_role;