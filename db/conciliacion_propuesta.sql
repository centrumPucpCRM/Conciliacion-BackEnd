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
-- Table structure for table `propuesta`
--

DROP TABLE IF EXISTS `propuesta`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `propuesta` (
  `id_propuesta` int NOT NULL AUTO_INCREMENT,
  `id_conciliacion` int DEFAULT NULL,
  `nombre` varchar(200) NOT NULL,
  `descripcion` varchar(800) DEFAULT NULL,
  `tipo_propuesta` varchar(50) NOT NULL,
  `estado_propuesta` varchar(50) NOT NULL,
  `creado_en` datetime DEFAULT NULL,
  PRIMARY KEY (`id_propuesta`),
  KEY `id_conciliacion` (`id_conciliacion`),
  KEY `ix_propuesta_id_propuesta` (`id_propuesta`),
  CONSTRAINT `propuesta_ibfk_1` FOREIGN KEY (`id_conciliacion`) REFERENCES `conciliacion` (`id_conciliacion`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `propuesta`
--

LOCK TABLES `propuesta` WRITE;
/*!40000 ALTER TABLE `propuesta` DISABLE KEYS */;
INSERT INTO `propuesta` VALUES (1,NULL,'Propuesta_20250905_110628','Propuesta generada automáticamente desde archivo CSV','CREACION','CANCELADA','2025-09-05 11:06:28'),(2,NULL,'Propuesta_20250905_111604','Propuesta generada automáticamente desde archivo CSV','CREACION','PROGRAMADA','2025-10-05 11:06:00'),(3,NULL,'Propuesta_20250905_113037','Propuesta generada automáticamente desde archivo CSV','CREACION','CONCILIADA','2025-08-05 11:06:00'),(4,NULL,'Propuesta_20250908_225057','Propuesta generada automáticamente desde archivo CSV','CREACION','CANCELADA','2025-09-08 22:50:58'),(5,NULL,'Propuesta_20250910_093941','Propuesta generada automáticamente desde archivo CSV','CREACION','PRECONCILIADA','2025-09-10 09:39:42');
/*!40000 ALTER TABLE `propuesta` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-09-11 15:20:31
