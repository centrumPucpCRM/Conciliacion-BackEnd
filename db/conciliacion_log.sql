-- MySQL dump 10.13  Distrib 8.0.41, for Win64 (x86_64)
--
-- Host: localhost    Database: conciliacion
-- ------------------------------------------------------
-- Server version	8.0.41

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `log`
--

DROP TABLE IF EXISTS `log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_solicitud` int DEFAULT NULL,
  `id_propuesta` int DEFAULT NULL,
  `id_usuario_generador` int DEFAULT NULL,
  `id_usuario_receptor` int DEFAULT NULL,
  `aceptado_por_responsable` tinyint(1) DEFAULT NULL,
  `tipo_solicitud` varchar(30) DEFAULT NULL,
  `valor_solicitud` varchar(30) DEFAULT NULL,
  `comentario` varchar(800) DEFAULT NULL,
  `id_propuesta_programa` int DEFAULT NULL,
  `id_propuesta_oportunidad` int DEFAULT NULL,
  `monto_propuesto` decimal(18,2) DEFAULT NULL,
  `monto_objetado` decimal(18,2) DEFAULT NULL,
  `fecha_creacion` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `id_solicitud` (`id_solicitud`),
  KEY `id_propuesta` (`id_propuesta`),
  KEY `id_usuario_generador` (`id_usuario_generador`),
  KEY `id_usuario_receptor` (`id_usuario_receptor`),
  KEY `id_propuesta_programa` (`id_propuesta_programa`),
  KEY `id_propuesta_oportunidad` (`id_propuesta_oportunidad`),
  KEY `ix_log_id` (`id`),
  CONSTRAINT `log_ibfk_1` FOREIGN KEY (`id_solicitud`) REFERENCES `solicitud` (`id_solicitud`),
  CONSTRAINT `log_ibfk_2` FOREIGN KEY (`id_propuesta`) REFERENCES `propuesta` (`id_propuesta`),
  CONSTRAINT `log_ibfk_3` FOREIGN KEY (`id_usuario_generador`) REFERENCES `usuario` (`id_usuario`),
  CONSTRAINT `log_ibfk_4` FOREIGN KEY (`id_usuario_receptor`) REFERENCES `usuario` (`id_usuario`),
  CONSTRAINT `log_ibfk_5` FOREIGN KEY (`id_propuesta_programa`) REFERENCES `propuesta_programa` (`id_propuesta_programa`),
  CONSTRAINT `log_ibfk_6` FOREIGN KEY (`id_propuesta_oportunidad`) REFERENCES `propuesta_oportunidad` (`id_propuesta_oportunidad`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `log`
--

LOCK TABLES `log` WRITE;
/*!40000 ALTER TABLE `log` DISABLE KEYS */;
/*!40000 ALTER TABLE `log` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-09-11 15:20:30
