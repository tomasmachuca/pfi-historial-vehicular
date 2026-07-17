-- =============================================================
--  Historial 0km - Esquema de base de datos
--  Compatible con Postgres / Supabase
-- =============================================================

create extension if not exists "uuid-ossp";

create table if not exists concesionarias (
    id              uuid primary key default uuid_generate_v4(),
    nombre          text not null,
    cuit            text unique,
    email           text unique not null,
    password_hash   text not null,
    wallet_address  text unique not null,
    wallet_pk_enc   text not null,
    activa          boolean not null default true,
    creado_en       timestamptz not null default now()
);

create table if not exists vehiculos (
    id                       uuid primary key default uuid_generate_v4(),
    vin                      text unique not null,
    patente                  text,
    marca                    text not null,
    modelo                   text not null,
    anio                     int  not null,
    color                    text,
    concesionaria_alta_id    uuid not null references concesionarias(id),
    km_inicial               int  not null default 0,
    tx_hash_alta             text,
    creado_en                timestamptz not null default now()
);

create index if not exists idx_vehiculos_vin     on vehiculos(vin);
create index if not exists idx_vehiculos_patente on vehiculos(patente);

create table if not exists tipos_servicio (
    codigo  smallint primary key,
    nombre  text not null,
    descripcion text
);

insert into tipos_servicio (codigo, nombre, descripcion) values
    (0,  'Alta 0km',          'Registro inicial del vehiculo en concesionaria'),
    (1,  'Service 10.000 km', 'Mantenimiento programado a los 10.000 km'),
    (2,  'Service 20.000 km', 'Mantenimiento programado a los 20.000 km'),
    (3,  'Service 30.000 km', 'Mantenimiento programado a los 30.000 km'),
    (4,  'Service 40.000 km', 'Mantenimiento programado a los 40.000 km'),
    (5,  'Service mayor',     'Service de gran magnitud (correa, embrague, etc.)'),
    (6,  'Reparacion garantia','Reparacion bajo cobertura de garantia oficial'),
    (7,  'Cambio de aceite',  'Cambio de aceite y filtros'),
    (8,  'Cambio de cubiertas','Reemplazo de neumaticos'),
    (9,  'Inspeccion tecnica','Revision general en concesionaria oficial')
on conflict (codigo) do nothing;

create table if not exists servicios (
    id                  uuid primary key default uuid_generate_v4(),
    vehiculo_id         uuid not null references vehiculos(id) on delete cascade,
    concesionaria_id    uuid not null references concesionarias(id),
    tipo_servicio       smallint not null references tipos_servicio(codigo),
    kilometraje         int  not null,
    descripcion         text,
    archivo_url         text,
    archivo_nombre      text,
    hash_evidencia      text not null,
    tx_hash             text,
    block_number        bigint,
    chain_timestamp     timestamptz,
    creado_en           timestamptz not null default now()
);

create index if not exists idx_servicios_vehiculo on servicios(vehiculo_id);

create table if not exists eventos_auditoria (
    id          uuid primary key default uuid_generate_v4(),
    actor_id    uuid references concesionarias(id),
    accion      text not null,
    detalle     jsonb,
    creado_en   timestamptz not null default now()
);
