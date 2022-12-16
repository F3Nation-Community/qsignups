from qsignups.database import DbManager
from qsignups.database.orm import Weekly, Master
from qsignups.slack import inputs
from . import UpdateResponse
import ast
from datetime import date

def delete(client, user_id, team_id, logger, input_data) -> UpdateResponse:
    
    # Gather filters
    input_data_dict = ast.literal_eval(input_data)
    weekly_id = input_data_dict['id']
    ao_channel_id = input_data_dict['ao_channel_id']
    event_day_of_week = input_data_dict['event_day_of_week']
    event_time = input_data_dict['event_time']
    event_type = input_data_dict['event_type']
    ao_display_name = input_data_dict['ao_display_name']

    # in the future we can use the FK from Weekly
    master_filter = [
        Master.team_id == team_id,
        Master.ao_channel_id == ao_channel_id,
        Master.event_day_of_week == event_day_of_week,
        Master.event_time == event_time,
        Master.event_date >= date.today()
    ]   

    # Perform deletions
    try:
        DbManager.delete_records(Master, master_filter)
        DbManager.delete_record(Weekly, weekly_id)
        return UpdateResponse(success = True, message=f"I've deleted all future {event_type}s from the schedule for {event_day_of_week}s at {event_time} at {ao_display_name}.")
    except Exception as e:
        logger.error(f"Error deleting: {e}")
        return UpdateResponse(success = False, message = f"Sorry, there was an error of some sort; please try again or contact your local administrator / Weasel Shaker. Errors:\n{e}")
    


