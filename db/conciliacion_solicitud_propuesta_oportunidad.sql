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
-- Table structure for table `solicitud_propuesta_oportunidad`
--

DROP TABLE IF EXISTS `solicitud_propuesta_oportunidad`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `solicitud_propuesta_oportunidad` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_solicitud` int DEFAULT NULL,
  `id_propuesta_oportunidad` int DEFAULT NULL,
  `monto_propuesto` decimal(18,2) DEFAULT NULL,
  `monto_objetado` decimal(18,2) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `id_solicitud` (`id_solicitud`),
  KEY `id_propuesta_oportunidad` (`id_propuesta_oportunidad`),
  KEY `ix_solicitud_propuesta_oportunidad_id` (`id`),
  CONSTRAINT `solicitud_propuesta_oportunidad_ibfk_1` FOREIGN KEY (`id_solicitud`) REFERENCES `solicitud` (`id_solicitud`),
  CONSTRAINT `solicitud_propuesta_oportunidad_ibfk_2` FOREIGN KEY (`id_propuesta_oportunidad`) REFERENCES `propuesta_oportunidad` (`id_propuesta_oportunidad`)
) ENGINE=InnoDB AUTO_INCREMENT=80 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `solicitud_propuesta_oportunidad`
--

LOCK TABLES `solicitud_propuesta_oportunidad` WRITE;
/*!40000 ALTER TABLE `solicitud_propuesta_oportunidad` DISABLE KEYS */;
INSERT INTO `solicitud_propuesta_oportunidad` VALUES (71,118,30687,41.00,0.00),(72,120,30690,61.00,0.00),(73,121,34708,3360.00,0.00),(74,119,30689,51.00,0.00),(75,122,30684,31.00,1300.00),(76,123,30681,11.00,0.00),(77,124,31116,5500.00,0.00),(78,126,34939,50175.00,0.00),(79,127,30725,1300.00,0.00);
/*!40000 ALTER TABLE `solicitud_propuesta_oportunidad` ENABLE KEYS */;
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
