ALTER TABLE `qsignup`.`qsignups_regions`
CHANGE COLUMN `google_calendar_id` `google_calendar_id` VARCHAR(100) NULL DEFAULT NULL ;

ALTER TABLE `qsignup`.`qsignups_regions`
ADD COLUMN `google_auth_data` JSON NULL AFTER `google_calendar_id`;

ALTER TABLE `qsignup`.`qsignups_regions`
ADD COLUMN `timezone` VARCHAR(45) NULL DEFAULT 'America/New_York' AFTER `google_auth_data`,
