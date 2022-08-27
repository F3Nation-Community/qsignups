CREATE TABLE `qsignups_master` (
  `ao_channel_id` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `event_date` date NOT NULL,
  `event_time` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `event_day_of_week` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `event_type` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `event_special` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL,
  `event_recurring` tinyint(1) NOT NULL,
  `q_pax_id` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL,
  `q_pax_name` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL,
  `team_id` varchar(100) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  PRIMARY KEY (`ao_channel_id`,`event_date`,`event_time`,`team_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
