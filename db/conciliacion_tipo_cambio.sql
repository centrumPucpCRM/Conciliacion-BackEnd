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
-- Table structure for table `tipo_cambio`
--

DROP TABLE IF EXISTS `tipo_cambio`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tipo_cambio` (
  `id_tipo_cambio` int NOT NULL AUTO_INCREMENT,
  `moneda_origen` varchar(10) NOT NULL,
  `moneda_target` varchar(10) NOT NULL,
  `equivalencia` decimal(18,6) NOT NULL,
  `creado_en` datetime DEFAULT NULL,
  `fecha_tipo_cambio` date DEFAULT NULL,
  PRIMARY KEY (`id_tipo_cambio`),
  KEY `ix_tipo_cambio_id_tipo_cambio` (`id_tipo_cambio`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tipo_cambio`
--

LOCK TABLES `tipo_cambio` WRITE;
/*!40000 ALTER TABLE `tipo_cambio` DISABLE KEYS */;
INSERT INTO `tipo_cambio` VALUES (1,'PEN','PEN',1.000000,'2025-09-05 11:06:30','2025-09-05'),(2,'USD','PEN',3.750000,'2025-09-05 11:06:30','2025-09-05'),(3,'EUR','PEN',4.100000,'2025-09-05 11:16:06','2025-09-05'),(4,'PEN','PEN',1.000000,'2025-09-08 22:50:59','2025-09-08'),(5,'USD','PEN',3.750000,'2025-09-08 22:50:59','2025-09-08'),(6,'EUR','PEN',4.100000,'2025-09-08 22:50:59','2025-09-08'),(7,'PEN','PEN',1.000000,'2025-09-10 09:39:43','2025-09-10'),(8,'USD','PEN',3.750000,'2025-09-10 09:39:43','2025-09-10'),(9,'EUR','PEN',4.100000,'2025-09-10 09:39:43','2025-09-10');
/*!40000 ALTER TABLE `tipo_cambio` ENABLE KEYS */;
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
