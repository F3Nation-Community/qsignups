ALTER TABLE `qsignup`.`qsignups_aos`
ADD COLUMN `google_calendar_id` VARCHAR(45) NULL AFTER `current_month_weinke`;

ALTER TABLE `qsignup`.`qsignups_aos`
ADD COLUMN `map_url` VARCHAR(256) NULL AFTER `google_calendar_id`;
