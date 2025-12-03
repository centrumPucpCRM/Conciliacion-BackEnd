-- Tabla: usuario_marketing
-- Descripción: Almacena información de usuarios del área de marketing con gestión de vacaciones

CREATE TABLE IF NOT EXISTS `usuario_marketing` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `nombre` VARCHAR(150) NOT NULL,
  `party_id` BIGINT NOT NULL,
  `party_number` VARCHAR(50) NOT NULL,
  `correo` VARCHAR(150) NOT NULL,
  `vacaciones` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '0 = no está de vacaciones, 1 = está de vacaciones',
  `id_usuario` INT NULL COMMENT 'ID del usuario relacionado (opcional)',
  `dias_pendientes` JSON NULL COMMENT 'Días pendientes por año. Ejemplo: {"2025": 66, "2026": 93}',
  `periodos` JSON NULL COMMENT 'Periodos de vacaciones. Ejemplo: [{"inicio": "2025-01-15", "fin": "2025-01-20"}]',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_party_id` (`party_id`),
  INDEX `idx_correo` (`correo`),
  INDEX `idx_id_usuario` (`id_usuario`),
  UNIQUE INDEX `idx_unique_party_id_number` (`party_id`, `party_number`),
  CONSTRAINT `fk_usuario_marketing_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Comentarios adicionales sobre la tabla
-- Esta tabla es independiente pero puede relacionarse opcionalmente con la tabla 'usuario' mediante 'id_usuario'
-- Los campos JSON permiten flexibilidad en la estructura de días pendientes y periodos de vacaciones
