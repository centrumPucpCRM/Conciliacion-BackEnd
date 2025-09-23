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
-- Table structure for table `usuario`
--

DROP TABLE IF EXISTS `usuario`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuario` (
  `id_usuario` int NOT NULL AUTO_INCREMENT,
  `dni` varchar(20) DEFAULT NULL,
  `correo` varchar(120) NOT NULL,
  `nombres` varchar(150) NOT NULL,
  `celular` varchar(30) DEFAULT NULL,
  `id_rol` int NOT NULL,
  PRIMARY KEY (`id_usuario`),
  UNIQUE KEY `correo` (`correo`),
  KEY `id_rol` (`id_rol`),
  KEY `ix_usuario_id_usuario` (`id_usuario`),
  CONSTRAINT `usuario_ibfk_1` FOREIGN KEY (`id_rol`) REFERENCES `rol` (`id_rol`)
) ENGINE=InnoDB AUTO_INCREMENT=77 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `usuario`
--

LOCK TABLES `usuario` WRITE;
/*!40000 ALTER TABLE `usuario` DISABLE KEYS */;
INSERT INTO `usuario` VALUES (1,NULL,'132465789@pucp.edu.pe','daf.supervisor',NULL,3),(2,NULL,'132465789-sub@pucp.edu.pe','daf.subdirector',NULL,4),(3,NULL,'amdmin@pucp.edu.pe','admin',NULL,5),(46,NULL,'jefe.grado@pucp.edu.pe','Jefe grado',NULL,2),(47,NULL,'jefe.ee@pucp.edu.pe','Jefe ee',NULL,2),(48,NULL,'jefe.centrumx@pucp.edu.pe','Jefe CentrumX',NULL,2),(63,'USR1','adriana.crespo@ejemplo.com','Adriana Crespo','999999999',1),(64,'USR2','liliana.cabrejos@ejemplo.com','Liliana Cabrejos','999999999',1),(65,'USR3','shalom.gonzales@ejemplo.com','Shalom Gonzales','999999999',1),(66,'USR4','amador.rivera@ejemplo.com','Amador Rivera','999999999',1),(67,'USR5','claudia.miranda@ejemplo.com','Claudia Miranda','999999999',1),(68,'USR6','elizabeth.sanchez@ejemplo.com','Elizabeth Sanchez','999999999',1),(69,'USR7','isabel.nolasco@ejemplo.com','Isabel Nolasco','999999999',1),(70,'USR8','jean.gomez@ejemplo.com','Jean Gomez','999999999',1),(71,'USR9','cristina.zaconeta@ejemplo.com','Cristina Zaconeta','999999999',1),(72,'USR10','gabriela.calderon@ejemplo.com','Gabriela Calderon','999999999',1),(73,'USR11','gerson.lopez@ejemplo.com','Gerson Lopez','999999999',1),(74,'USR12','jorge.huaman@ejemplo.com','Jorge Huaman','999999999',1),(75,'USR13','lizbeth.alvarado@ejemplo.com','Lizbeth Alvarado','999999999',1),(76,'USR14','paola.chau@ejemplo.com','Paola Chau','999999999',1);
/*!40000 ALTER TABLE `usuario` ENABLE KEYS */;
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
