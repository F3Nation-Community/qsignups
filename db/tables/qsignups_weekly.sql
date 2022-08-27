CREATE TABLE `qsignups_weekly` (
  `ao_channel_id` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `event_day_of_week` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `event_time` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `event_type` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `team_id` varchar(100) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  PRIMARY KEY (`ao_channel_id`,`event_day_of_week`,`event_time`,`team_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
