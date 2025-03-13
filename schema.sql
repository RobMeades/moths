-- --------------------------------------------------------
-- Host:                         10.10.1.7
-- Server version:               9.2.0 - MySQL Community Server - GPL
-- Server OS:                    Win64
-- HeidiSQL Version:             12.10.0.7000
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


-- Dumping database structure for moths
CREATE DATABASE IF NOT EXISTS `moths` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `moths`;

-- Dumping structure for table moths.instance
CREATE TABLE IF NOT EXISTS `instance` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `count` int unsigned NOT NULL DEFAULT '0',
  `variant` tinytext,
  `image` mediumblob,
  `trapping_id` int unsigned NOT NULL,
  `moth_id` int unsigned DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `moth_id` (`moth_id`),
  KEY `trapping_id` (`trapping_id`),
  CONSTRAINT `moth_id` FOREIGN KEY (`moth_id`) REFERENCES `moth` (`id`),
  CONSTRAINT `trapping_id` FOREIGN KEY (`trapping_id`) REFERENCES `trapping` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=36 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='An instance of a moth in  trapping, with a count and, usually, a picture.';

-- Data exporting was unselected.

-- Dumping structure for table moths.location
CREATE TABLE IF NOT EXISTS `location` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `name` tinytext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'Name the location (e.g. garden at number 12)',
  `latitude_longitude` point NOT NULL /*!80003 SRID 0 */ COMMENT 'The latitude/longitude of the locaton; to get a POINT value into this field, you can''t use the HeidiSQL GUI, you have to run an SQL Query as follows:\r\n\r\nINSERT INTO `moths`.`location` (`name`, `latitude_longitude`) VALUES (''THe name of the location'', ST_GeomFromText(''POINT(52.01868898299692 0.24707864012902547)''));\r\n\r\n...noting that there is NO COMMA between the latitude and longitude values.',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Where a moth trapping has occurred.';

-- Data exporting was unselected.

-- Dumping structure for table moths.moth
CREATE TABLE IF NOT EXISTS `moth` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `common_name` tinytext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `scientific_name` tinytext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `agg_id` int unsigned DEFAULT NULL,
  `confusion_1_id` int unsigned DEFAULT NULL,
  `confusion_2_id` int unsigned DEFAULT NULL,
  `confusion_3_id` int unsigned DEFAULT NULL,
  `confusion_4_id` int unsigned DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `agg_id` (`agg_id`) USING BTREE,
  KEY `confusion_1_id` (`confusion_1_id`) USING BTREE,
  KEY `confusion_2_id` (`confusion_2_id`) USING BTREE,
  KEY `confusion_3_id` (`confusion_3_id`) USING BTREE,
  KEY `confusion_4_id` (`confusion_4_id`) USING BTREE,
  CONSTRAINT `agg_id` FOREIGN KEY (`agg_id`) REFERENCES `moth` (`id`),
  CONSTRAINT `confusion_1_id` FOREIGN KEY (`confusion_1_id`) REFERENCES `moth` (`id`),
  CONSTRAINT `confusion_2_id` FOREIGN KEY (`confusion_2_id`) REFERENCES `moth` (`id`),
  CONSTRAINT `confusion_3_id` FOREIGN KEY (`confusion_4_id`) REFERENCES `moth` (`id`),
  CONSTRAINT `confusion_4_id` FOREIGN KEY (`confusion_4_id`) REFERENCES `moth` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Not a butterfly.';

-- Data exporting was unselected.

-- Dumping structure for table moths.trapping
CREATE TABLE IF NOT EXISTS `trapping` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `date` date NOT NULL COMMENT 'The date of the day that followed a moth-trapping night.',
  `temperature_celsius` int DEFAULT NULL COMMENT 'The average temperature during the night in Celsius.',
  `description` text COMMENT 'A description of the trapping, which will be used in the web-page generated from this data.',
  `location_id` int unsigned DEFAULT NULL COMMENT 'The ID of the location where the trapping occurred.',
  PRIMARY KEY (`id`),
  UNIQUE KEY `date` (`date`),
  KEY `location_id` (`location_id`),
  CONSTRAINT `location_id` FOREIGN KEY (`location_id`) REFERENCES `location` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='A night of moth trapping.';

-- Data exporting was unselected.

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;
