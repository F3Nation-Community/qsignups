ALTER TABLE `qsignup`.`qsignups_aos`
ADD COLUMN `google_calendar_id` VARCHAR(45) NULL AFTER `current_month_weinke`,
ADD COLUMN `map_url` VARCHAR(256) NULL AFTER `google_calendar_id`,
ADD COLUMN `latitude` DECIMAL(9,6) NULL AFTER `map_url`,
ADD COLUMN `longitude` DECIMAL(9,6) NULL AFTER `latitude`
;

ALTER TABLE `qsignup`.`qsignups_weekly`
ADD COLUMN `map_url` VARCHAR(256) NULL AFTER `google_calendar_id`;
ADD COLUMN `latitude` DECIMAL(9,6) NULL AFTER `map_url`,
ADD COLUMN `longitude` DECIMAL(9,6) NULL AFTER `latitude`
;
