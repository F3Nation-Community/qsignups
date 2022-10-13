ALTER TABLE `qsignup`.`qsignups_regions`
ADD COLUMN `google_calendar_id` VARCHAR(45) NULL AFTER `weekly_ao_reminders`;
ALTER TABLE `qsignup`.`qsignups_master`
ADD COLUMN `google_event_id` VARCHAR(45) NULL AFTER `team_id`;
