from database import DbManager
from database.orm import Weekly, Master, AO
from database.orm.views import vwWeeklyEvents
from . import UpdateResponse
import ast
from datetime import date, datetime, timedelta
import pytz
from sqlalchemy import func
from slack import inputs
from utilities import safe_get
from constants import SCHEDULE_CREATE_LENGTH_DAYS

def delete(client, user_id, team_id, logger, input_data) -> UpdateResponse:

    weekly_event = DbManager.get_record(vwWeeklyEvents, input_data)

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
        DbManager.delete_record(Weekly, weekly_event.id)
        return UpdateResponse(success = True, message=f"I've deleted all future {weekly_event.ao_display_name}s from the schedule for {weekly_event.event_day_of_week}s at {weekly_event.event_time} at {weekly_event.ao_display_name}.")
    except Exception as e:
        logger.error(f"Error deleting: {e}")
        return UpdateResponse(success = False, message = f"Sorry, there was an error of some sort; please try again or contact your local administrator / Weasel Shaker. Errors:\n{e}")

def edit(client, user_id, team_id, logger, body) -> UpdateResponse:

    input_data = body['view']['state']['values']
    event_id = int(body['view']['blocks'][-1]['elements'][0]['text'])

    # Gather inputs from form
    ao_display_name = inputs.AO_SELECTOR.get_selected_value(input_data)
    event_day_of_week = inputs.WEEKDAY_SELECTOR.get_selected_value(input_data)
    event_time = inputs.START_TIME_SELECTOR.get_selected_value(input_data).replace(":", "")
    event_end_time = inputs.END_TIME_SELECTOR.get_selected_value(input_data)
    if event_end_time:
        event_end_time = event_end_time.replace(":", "")
    event_type = inputs.EVENT_TYPE_SELECTOR.get_selected_value(input_data)
    starting_date = inputs.START_DATE_SELECTOR.get_selected_value(input_data) or datetime.now(tz=pytz.timezone('US/Central'))

    event_recurring = True
    
    if event_type == 'Custom':
        event_type = inputs.CUSTOM_EVENT_INPUT.get_selected_value(input_data) or 'Custom'

    try:
        # Grab channel id
        ao: AO = DbManager.find_records(AO, [AO.team_id == team_id, AO.ao_display_name == ao_display_name])[0]
        ao_channel_id = ao.ao_channel_id

        original_record: Weekly = DbManager.get_record(Weekly, event_id)

        # Update Weekly table
        DbManager.update_record(Weekly, event_id, {
            Weekly.ao_channel_id: ao_channel_id,
            Weekly.event_day_of_week: event_day_of_week,
            Weekly.event_time: event_time,
            Weekly.event_end_time: event_end_time,
            Weekly.event_type: event_type,
            Weekly.team_id: team_id
        })

        # Support for changing day of week
        if event_day_of_week != original_record.event_day_of_week:
            day_list = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            new_dow_num = day_list.index(event_day_of_week)
            old_dow_num = day_list.index(original_record.event_day_of_week)
            day_adjust = new_dow_num - old_dow_num
        else:
            day_adjust = 0

        # Update Master table
        DbManager.update_records(cls=Master, filters=[
            Master.team_id == team_id,
            Master.ao_channel_id == original_record.ao_channel_id,
            Master.event_day_of_week == original_record.event_day_of_week,
            Master.event_time == original_record.event_time,
            Master.event_date >= starting_date
        ], fields={
            Master.ao_channel_id: ao_channel_id,
            Master.event_date: func.ADDDATE(Master.event_date, day_adjust),
            Master.event_day_of_week: event_day_of_week,
            Master.event_time: event_time,
            Master.event_end_time: event_end_time,
            Master.event_type: event_type,
            Master.team_id: team_id,
            Master.event_recurring: event_recurring
        })

        return UpdateResponse(success = True, message=f"Got it - I've made your updates!")
    except Exception as e:
        logger.error(f"Error updating: {e}")
        return UpdateResponse(success = False, message = f"Sorry, there was an error of some sort; please try again or contact your local administrator / Weasel Shaker. Errors:\n{e}")

def insert(client, user_id, team_id, logger, input_data) -> UpdateResponse:

    ao_display_name = safe_get(input_data, 'ao_display_name_select_action','ao_display_name_select_action','selected_option','value')
    event_day_of_week = safe_get(input_data, 'event_day_of_week_select_action','event_day_of_week_select_action','selected_option','value')
    starting_date = safe_get(input_data, 'add_event_datepicker','add_event_datepicker','selected_date')
    event_time = safe_get(input_data, 'event_start_time_select','event_start_time_select','selected_time').replace(':','')
    event_end_time = safe_get(input_data, 'event_end_time_select','event_end_time_select','selected_time').replace(':','')
    event_type_select = safe_get(input_data, 'event_type_select_action','event_type_select_action','selected_option','value')
    event_type_custom = safe_get(input_data, 'event_type_custom','event_type_custom','value')
    event_recurring = True

    # Logic for custom events
    if event_type_select == 'Custom':
        event_type = event_type_custom
    else:
        event_type = event_type_select

    ao_channel_id = DbManager.find_records(AO, [
        AO.team_id == team_id,
        AO.ao_display_name == ao_display_name
    ])[0].ao_channel_id

    try:
        DbManager.create_record(Weekly(
            ao_channel_id = ao_channel_id,
            event_day_of_week = event_day_of_week,
            event_time = event_time,
            event_end_time = event_end_time,
            event_type = event_type,
            team_id = team_id
        ))

        record_list = []
        iterate_date = datetime.strptime(starting_date, '%Y-%m-%d').date()
        while iterate_date < (date.today() + timedelta(days=SCHEDULE_CREATE_LENGTH_DAYS)):
            if iterate_date.strftime('%A') == event_day_of_week:
                record_list.append(Master(
                    ao_channel_id = ao_channel_id,
                    event_date = iterate_date,
                    event_time = event_time,
                    event_end_time = event_end_time,
                    event_day_of_week = event_day_of_week,
                    event_type = event_type,
                    event_recurring = event_recurring,
                    team_id = team_id
                ))
            iterate_date += timedelta(days=1)

        DbManager.create_records(record_list)
        return UpdateResponse(success = True, message=f"Got it - I've made your updates!")
    except Exception as e:
        logger.error(f"Error updating: {e}")
        return UpdateResponse(success = False, message = f"Sorry, there was an error of some sort; please try again or contact your local administrator / Weasel Shaker. Errors:\n{e}")

