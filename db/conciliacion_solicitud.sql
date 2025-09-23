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
-- Table structure for table `solicitud`
--

DROP TABLE IF EXISTS `solicitud`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `solicitud` (
  `id_solicitud` int NOT NULL AUTO_INCREMENT,
  `id_propuesta` int DEFAULT NULL,
  `id_usuario_generador` int DEFAULT NULL,
  `id_usuario_receptor` int DEFAULT NULL,
  `aceptado_por_responsable` tinyint(1) DEFAULT NULL,
  `tipo_solicitud` varchar(50) NOT NULL,
  `comentario` varchar(800) DEFAULT NULL,
  `creado_en` datetime DEFAULT NULL,
  `abierta` tinyint(1) DEFAULT '0',
  `valor_solicitud` varchar(50) NOT NULL,
  PRIMARY KEY (`id_solicitud`),
  KEY `id_propuesta` (`id_propuesta`),
  KEY `id_usuario_generador` (`id_usuario_generador`),
  KEY `id_usuario_receptor` (`id_usuario_receptor`),
  KEY `ix_solicitud_id_solicitud` (`id_solicitud`),
  CONSTRAINT `solicitud_ibfk_1` FOREIGN KEY (`id_propuesta`) REFERENCES `propuesta` (`id_propuesta`),
  CONSTRAINT `solicitud_ibfk_2` FOREIGN KEY (`id_usuario_generador`) REFERENCES `usuario` (`id_usuario`),
  CONSTRAINT `solicitud_ibfk_3` FOREIGN KEY (`id_usuario_receptor`) REFERENCES `usuario` (`id_usuario`)
) ENGINE=InnoDB AUTO_INCREMENT=134 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `solicitud`
--

LOCK TABLES `solicitud` WRITE;
/*!40000 ALTER TABLE `solicitud` DISABLE KEYS */;
INSERT INTO `solicitud` VALUES (118,5,1,66,0,'EDICION_ALUMNO','DAF ajustó el monto propuesto de 1250 a 41','2025-09-11 14:44:17',1,'PENDIENTE'),(119,5,1,66,0,'EDICION_ALUMNO','DAF ajustó el monto propuesto de 1250 a 51','2025-09-11 14:44:17',1,'PENDIENTE'),(120,5,1,66,0,'EDICION_ALUMNO','DAF ajustó el monto propuesto de 1250 a 61','2025-09-11 14:44:17',1,'PENDIENTE'),(121,5,1,74,0,'EDICION_ALUMNO','DAF ajustó el monto propuesto de 3213 a 3360','2025-09-11 14:44:17',1,'PENDIENTE'),(122,5,66,1,0,'EDICION_ALUMNO','El jp propone 1300 sobre esta solicitud anterior\nSolicitud anterior: DAF ajustó el monto propuesto de 1250 a 31','2025-09-11 14:44:17',1,'ACEPTADO'),(123,5,1,66,0,'EDICION_ALUMNO','DAF ajustó el monto propuesto de 1250 a 11','2025-09-11 14:44:17',1,'ACEPTADO'),(124,5,1,68,0,'EDICION_ALUMNO','DAF ajustó el monto propuesto de 5310 a 5500','2025-09-11 14:44:17',1,'PENDIENTE'),(125,5,1,70,0,'EXCLUSION_PROGRAMA','DAF solicitó suprimir este programa ya que no cumple el mínimo de apertura (mínimo: 14, matriculados actuales: 40)','2025-09-11 14:44:17',1,'PENDIENTE'),(126,5,1,76,0,'EDICION_ALUMNO','DAF ajustó el monto propuesto de 50175 a 50175','2025-09-11 14:44:17',1,'PENDIENTE'),(127,5,1,70,0,'EDICION_ALUMNO','DAF ajustó el monto propuesto de 1250 a 1300','2025-09-11 14:44:17',1,'PENDIENTE'),(128,5,1,70,0,'EXCLUSION_PROGRAMA','DAF solicitó suprimir este programa ya que no cumple el mínimo de apertura (mínimo: 18, matriculados actuales: 0)','2025-09-11 14:44:17',1,'PENDIENTE'),(129,5,1,74,0,'EXCLUSION_PROGRAMA','DAF solicitó suprimir este programa ya que no cumple el mínimo de apertura (mínimo: 19, matriculados actuales: 18)','2025-09-11 14:44:17',1,'PENDIENTE'),(130,5,1,68,0,'EXCLUSION_PROGRAMA','DAF solicitó suprimir este programa ya que no cumple el mínimo de apertura (mínimo: 11, matriculados actuales: 10)','2025-09-11 14:44:17',1,'PENDIENTE'),(131,5,1,68,0,'EXCLUSION_PROGRAMA','DAF solicitó suprimir este programa ya que no cumple el mínimo de apertura (mínimo: 14, matriculados actuales: 12)','2025-09-11 14:44:17',1,'PENDIENTE'),(132,5,1,74,0,'EXCLUSION_PROGRAMA','DAF solicitó suprimir este programa ya que no cumple el mínimo de apertura (mínimo: 18, matriculados actuales: 16)','2025-09-11 14:44:17',1,'PENDIENTE'),(133,5,1,73,0,'EXCLUSION_PROGRAMA','DAF solicitó suprimir este programa ya que no cumple el mínimo de apertura (mínimo: 20, matriculados actuales: 16)','2025-09-11 14:44:17',1,'PENDIENTE');
/*!40000 ALTER TABLE `solicitud` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-09-11 15:20:29
