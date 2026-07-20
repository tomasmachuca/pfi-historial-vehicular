-- =============================================================
--  Migración 002 - Anomalías de kilometraje regresivo
--  Registra services con km menor al último como "manchas"
--  off-chain, con contador + detalle para el scoring del historial.
-- =============================================================

-- Detalle por service anómalo
alter table servicios     add column if not exists km_regresivo boolean not null default false;
alter table servicios     add column if not exists km_anterior  int;

-- Contadores agregados para el scoring (vehículo y concesionaria "manchados")
alter table vehiculos      add column if not exists anomalias_count int not null default 0;
alter table concesionarias add column if not exists anomalias_count int not null default 0;
