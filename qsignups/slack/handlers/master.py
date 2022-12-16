from qsignups.database import DbManager
from qsignups.database.orm import Master
from qsignups.slack import inputs
from . import UpdateResponse
from datetime import date

def delete(client, user_id, team_id, logger, input_data) -> UpdateResponse:
    
    # Gather filters (should this be in a handler?)
    selected_ao, selected_day, selected_event_type, selected_start_time, selected_end_time, selected_ao_id = str.split(input_data, '|')
    weekly_filter = [
        Master.team_id == team_id,
        Master.ao_channel_id == selected_ao_id,
        Master.event_day_of_week == selected_day,
        Master.event_time == selected_start_time,
        Master.event_date >= date.today() # This didn't work - just deleted everything (that may be what we end up doing anyway if we cascade)
    ]   

    # Perform deletions
    try:
        DbManager.delete_records(Master, weekly_filter)
        return UpdateResponse(success = True)
    except Exception as e:
        logger.error(f"Error deleting: {e}")
        return UpdateResponse(success = False, message = f"{e}")


