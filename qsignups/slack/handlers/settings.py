from qsignups.database import DbManager
from qsignups.database.orm.region import Region, RegionService
from qsignups.slack import inputs
from . import UpdateResponse

def update(client, user_id, team_id, logger, input_data) -> UpdateResponse:
    updated_region = Region(
        weekly_weinke_channel = inputs.WEINKIE_INPUT.get_selected_value(input_data),
        signup_reminders = inputs.Q_REMINDER_RADIO.get_selected_value(input_data) == inputs.Q_REMINDER_ENABLED.value,
        weekly_ao_reminders = inputs.AO_REMINDER_RADIO.get_selected_value(input_data) == inputs.AO_REMINDER_ENABLED.value,
        google_calendar_id = inputs.GOOGLE_CALENDAR_INPUT.get_selected_value(input_data)
    )
    try:
        DbManager.update_record(RegionService, team_id, updated_region)
        return UpdateResponse(success = True)
    except Exception as e:
        logger.error(f"Error writing to db: {e}")
        return UpdateResponse(success = False, message = f"{e}")

