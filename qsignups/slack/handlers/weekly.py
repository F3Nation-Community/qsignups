from qsignups.database import DbManager
from qsignups.database.orm import Weekly, Master
from qsignups.database.orm.views import vwWeeklyEvents
from . import UpdateResponse
import ast
from datetime import date

def delete(client, user_id, team_id, logger, input_data) -> UpdateResponse:

    event_id = input_data['id']

    weekly_event = DbManager.get_record(vwWeeklyEvents, event_id)

    # in the future we can use the FK from Weekly
    master_filter = [
        Master.team_id == team_id,
        Master.ao_channel_id == weekly_event.ao_channel_id,
        Master.event_day_of_week == weekly_event.event_day_of_week,
        Master.event_time == weekly_event.event_time,
        Master.event_date >= date.today()
    ]

    # Perform deletions
    try:
        DbManager.delete_records(Master, master_filter)
        DbManager.delete_record(Weekly, event_id)
        return UpdateResponse(success = True, message=f"I've deleted all future {weekly_event.event_type}s from the schedule for {weekly_event.event_day_of_week}s at {weekly_event.event_time} at {weekly_event.ao_display_name}.")
    except Exception as e:
        logger.error(f"Error deleting: {e}")
        return UpdateResponse(success = False, message = f"Sorry, there was an error of some sort; please try again or contact your local administrator / Weasel Shaker. Errors:\n{e}")



