from qsignups.database import DbManager
from qsignups.database.orm import Weekly
from qsignups.slack import inputs
from . import UpdateResponse

def delete(client, user_id, team_id, logger, input_data) -> UpdateResponse:
    
    # Gather filters (should this be in a handler?)
    selected_ao, selected_day, selected_event_type, selected_start_time, selected_end_time, selected_ao_id = str.split(input_data, '|')
    weekly_filter = [
        Weekly.team_id == team_id,
        Weekly.ao_channel_id == selected_ao_id,
        Weekly.event_day_of_week == selected_day,
        Weekly.event_time == selected_start_time
    ]   

    # Perform deletions
    try:
        DbManager.delete_records(Weekly, weekly_filter)
        return UpdateResponse(success = True)
    except Exception as e:
        logger.error(f"Error deleting: {e}")
        return UpdateResponse(success = False, message = f"{e}")


