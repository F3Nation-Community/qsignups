CREATE TABLE `qsignups_regions` (
  `current_week_weinke` longtext CHARACTER SET utf8 COLLATE utf8_general_ci,
  `next_week_weinke` longtext CHARACTER SET utf8 COLLATE utf8_general_ci,
  `team_id` varchar(100) NOT NULL,
  `bot_token` varchar(100) DEFAULT NULL,
  `signup_reminders` tinyint DEFAULT NULL,
  `weekly_weinke_channel` varchar(100) DEFAULT NULL,
  `workspace_name` varchar(100) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL,
  `current_week_weinke_updated` varchar(100) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL,
  `next_week_weinke_updated` varchar(100) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL,
  `weekly_ao_reminders` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`team_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
