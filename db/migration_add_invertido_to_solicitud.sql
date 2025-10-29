-- Migración: Agregar campo 'invertido' a la tabla solicitud
-- Fecha: 2025-10-29
-- Descripción: Añade un flag booleano para controlar la lógica invertida en solicitudes con rechazos múltiples

ALTER TABLE solicitud 
ADD COLUMN invertido BOOLEAN DEFAULT FALSE;

-- Comentario: Este campo permite rastrear cuando una solicitud ha sido rechazada y la lógica de aceptación debe invertirse
