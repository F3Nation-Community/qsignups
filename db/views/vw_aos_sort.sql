CREATE OR REPLACE VIEW vw_aos_sort AS
SELECT *
FROM qsignups_aos
ORDER BY REPLACE(ao_display_name, 'The ', '')