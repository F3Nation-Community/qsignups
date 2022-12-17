CREATE OR REPLACE VIEW vw_weekly_events AS
SELECT w.*, a.ao_display_name
FROM qsignups_weekly w
INNER JOIN qsignups_aos a
ON w.ao_channel_id = a.ao_channel_id  AND w.team_id = a.team_id