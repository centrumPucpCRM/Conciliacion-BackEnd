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
-- Table structure for table `usuario_cartera`
--

DROP TABLE IF EXISTS `usuario_cartera`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuario_cartera` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_usuario` int DEFAULT NULL,
  `id_cartera` int DEFAULT NULL,
  `fecha_vinculacion` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `id_usuario` (`id_usuario`),
  KEY `id_cartera` (`id_cartera`),
  KEY `ix_usuario_cartera_id` (`id`),
  CONSTRAINT `usuario_cartera_ibfk_1` FOREIGN KEY (`id_usuario`) REFERENCES `usuario` (`id_usuario`),
  CONSTRAINT `usuario_cartera_ibfk_2` FOREIGN KEY (`id_cartera`) REFERENCES `cartera` (`id_cartera`)
) ENGINE=InnoDB AUTO_INCREMENT=158 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `usuario_cartera`
--

LOCK TABLES `usuario_cartera` WRITE;
/*!40000 ALTER TABLE `usuario_cartera` DISABLE KEYS */;
INSERT INTO `usuario_cartera` VALUES (127,63,3,NULL),(128,63,1,NULL),(129,64,9,NULL),(130,64,8,NULL),(131,64,2,NULL),(132,65,3,NULL),(133,65,15,NULL),(134,66,4,NULL),(135,66,8,NULL),(136,67,4,NULL),(137,67,8,NULL),(138,68,11,NULL),(139,68,8,NULL),(140,68,5,NULL),(141,69,6,NULL),(142,69,10,NULL),(143,70,9,NULL),(144,70,5,NULL),(145,70,11,NULL),(146,70,7,NULL),(147,71,8,NULL),(148,71,10,NULL),(149,72,5,NULL),(150,73,5,NULL),(151,74,8,NULL),(152,74,12,NULL),(153,75,2,NULL),(154,75,13,NULL),(155,75,14,NULL),(156,76,13,NULL),(157,76,2,NULL);
/*!40000 ALTER TABLE `usuario_cartera` ENABLE KEYS */;
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
