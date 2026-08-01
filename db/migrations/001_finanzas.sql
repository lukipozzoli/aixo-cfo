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

-- Permisos del schema finanzas para el rol de backend (service_role).
-- Solo service_role: la anon key queda sin acceso, como corresponde.
grant usage on schema finanzas to service_role;
grant all on all tables in schema finanzas to service_role;
alter default privileges in schema finanzas grant all on tables to service_role;