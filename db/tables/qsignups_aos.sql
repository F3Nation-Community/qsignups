CREATE TABLE `qsignups_aos` (
  `ao_channel_id` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `ao_display_name` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `ao_location_subtitle` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `team_id` varchar(100) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `current_month_weinke` longtext,
  PRIMARY KEY (`ao_channel_id`,`team_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
