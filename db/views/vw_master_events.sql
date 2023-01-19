CREATE OR REPLACE VIEW vw_master_events AS
SELECT m.*, a.ao_display_name, a.ao_location_subtitle
FROM qsignups_master m
LEFT JOIN qsignups_aos a
ON m.team_id = a.team_id
  AND m.ao_channel_id = a.ao_channel_id
ORDER BY m.event_date, m.event_time
;