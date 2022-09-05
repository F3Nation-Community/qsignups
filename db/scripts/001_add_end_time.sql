ALTER TABLE `qsignup`.`qsignups_master`
ADD COLUMN `event_end_time` VARCHAR(255) NULL AFTER `event_time`;
ALTER TABLE `qsignup`.`qsignups_weekly`
ADD COLUMN `event_end_time` VARCHAR(45) NULL AFTER `event_time`;

