from qsignups.database import DbManager
from qsignups.database.orm import Weekly, Master, AO
from . import UpdateResponse
import ast
from datetime import date, datetime
from sqlalchemy import func
from qsignups.utilities import get_user_name, safe_get

def delete(client, user_id, team_id, logger, input_data) -> UpdateResponse:

    # gather and format selected date and time
    selected_list = str.split(input_data,'|')
    selected_date = selected_list[0]
    selected_ao_id = selected_list[1]
    selected_date_dt = datetime.strptime(selected_date, '%Y-%m-%d %H:%M:%S')
    selected_date_db = datetime.date(selected_date_dt).strftime('%Y-%m-%d')
    selected_time_db = datetime.time(selected_date_dt).strftime('%H%M')

    # in the future we can use the primary key (id)
    master_filter = [
        Master.team_id == team_id,
        Master.ao_channel_id == selected_ao_id,
        Master.event_date == selected_date_dt.date(),
        Master.event_time == selected_time_db
    ]

    # Perform deletions
    try:
        DbManager.delete_records(Master, master_filter)
        return UpdateResponse(success = True, message=f"Success! Deleted event on {selected_date_db} at {selected_time_db}")
    except Exception as e:
        logger.error(f"Error deleting: {e}")
        return UpdateResponse(success = False, message = f"Sorry, there was an error of some sort; please try again or contact your local administrator / Weasel Shaker. Errors:\n{e}")
    
def insert(client, user_id, team_id, logger, input_data) -> UpdateResponse:
    
    ao_display_name = input_data['ao_display_name_select_action']['ao_display_name_select_action']['selected_option']['value']
    event_date = input_data['add_event_datepicker']['add_event_datepicker']['selected_date']
    event_time = input_data['event_start_time_select']['event_start_time_select']['selected_time'].replace(':','')
    event_end_time = input_data['event_end_time_select']['event_end_time_select']['selected_time'].replace(':','')

    # Logic for custom events
    if input_data['event_type_select_action']['event_type_select_action']['selected_option']['value'] == 'Custom':
        event_type = input_data['event_type_custom']['event_type_custom']['value']
    else:
        event_type = input_data['event_type_select_action']['event_type_select_action']['selected_option']['value']

    # Grab channel id
    ao_channel_id = DbManager.find_records(AO, [
        AO.team_id == team_id,
        AO.ao_display_name == ao_display_name
    ])[0].ao_channel_id

    event_day_of_week = datetime.strptime(event_date, '%Y-%m-%d').date().strftime('%A')
    event_recurring = False

    # Attempt insert
    try:
        master_record = DbManager.create_record(Master(
            ao_channel_id = ao_channel_id,
            event_date = event_date,
            event_time = event_time,
            event_end_time = event_end_time,
            event_day_of_week = event_day_of_week,
            event_type = event_type,
            event_recurring = event_recurring,
            team_id = team_id
        ))
        return UpdateResponse(success = True, message=f"Got it - I've made your updates!")
    except Exception as e:
        logger.error(f"Error inserting: {e}")
        return UpdateResponse(success = False, message = f"Sorry, there was an error of some sort; please try again or contact your local administrator / Weasel Shaker. Errors:\n{e}")
    
def update(client, user_id, team_id, logger, input_data) -> UpdateResponse:
    
    original_info = input_data['view']['blocks'][0]['text']['text']
    ignore, event, q_name = original_info.split('\n')
    original_date, original_time, original_ao_name = event.split(' @ ')
    original_channel_id = input_data['actions'][0]['value']

    results = input_data['view']['state']['values']
    selected_date = results['edit_event_datepicker']['edit_event_datepicker']['selected_date']
    selected_time = results['edit_event_timepicker']['edit_event_timepicker']['selected_time'].replace(':','')
    selected_q_id_list = results['edit_event_q_select']['edit_event_q_select']['selected_users']
    if len(selected_q_id_list) == 0:
        selected_q_id_fmt = None
        selected_q_name_fmt = None
    else:
        selected_q_id = selected_q_id_list[0]
        user_info_dict = client.users_info(user=selected_q_id)
        selected_q_name = safe_get(user_info_dict, 'user', 'profile', 'display_name') or safe_get(
            user_info_dict, 'user', 'profile', 'real_name') or None

        selected_q_id_fmt = selected_q_id
        selected_q_name_fmt = selected_q_name
    selected_special = results['edit_event_special_select']['edit_event_special_select']['selected_option']['text']['text']
    if selected_special == 'None':
        selected_special_fmt = None
    else:
        selected_special_fmt = selected_special

    try:
        DbManager.update_records(cls=Master, filters=[
            Master.team_id == team_id,
            Master.ao_channel_id == original_channel_id,
            Master.event_date == datetime.strptime(original_date, '%Y-%m-%d'),
            Master.event_time == original_time
        ], fields={
            Master.q_pax_id: selected_q_id_fmt,
            Master.q_pax_name: selected_q_name_fmt,
            Master.event_date: datetime.strptime(selected_date, '%Y-%m-%d'),
            Master.event_time: selected_time,
            Master.event_special: selected_special_fmt
        })
        return UpdateResponse(success = True, message=f"Got it - I've made your updates!")
    except Exception as e:
        logger.error(f"Error inserting: {e}")
        return UpdateResponse(success = False, message = f"Sorry, there was an error of some sort; please try again or contact your local administrator / Weasel Shaker. Errors:\n{e}")
    
def clear(client, user_id, team_id, logger, input_data) -> UpdateResponse:

    # gather and format selected date and time
    selected_list = str.split(input_data,'|')
    selected_date = selected_list[0]
    selected_date_dt = datetime.strptime(selected_date, '%Y-%m-%d %H:%M:%S')
    selected_date_db = datetime.date(selected_date_dt).strftime('%Y-%m-%d')
    selected_time_db = datetime.time(selected_date_dt).strftime('%H%M')

    # gather info needed for message and SQL
    ao_display_name = selected_list[1]
    user_name = get_user_name(user_id, client)
        
    ao_channel_id = DbManager.find_records(AO, [
        AO.team_id == team_id,
        AO.ao_display_name == ao_display_name
    ])[0].ao_channel_id
    
    try:
        DbManager.update_records(cls=Master, filters=[
            Master.team_id == team_id,
            Master.ao_channel_id == ao_channel_id,
            Master.event_date == selected_date_dt.date(),
            Master.event_time == selected_time_db
        ], fields={
            Master.q_pax_id: None,
            Master.q_pax_name: None
        })
        return UpdateResponse(success = True, message=f"Got it, {user_name}! I have cleared the Q slot at *{ao_display_name}* on *{selected_date_dt.strftime('%A, %B %-d @ %H%M')}*")
    except Exception as e:
        logger.error(f"Error updating: {e}")
        return UpdateResponse(success = False, message = f"Sorry, there was an error of some sort; please try again or contact your local administrator / Weasel Shaker. Errors:\n{e}")        
    
def update_post(client, user_id, team_id, logger, input_data, ao_name) -> UpdateResponse:
        
    user_name = get_user_name(user_id, client)
    
    # gather and format selected date and time
    selected_date = input_data['actions'][0]['value']
    selected_date_dt = datetime.strptime(selected_date, '%Y-%m-%d %H:%M:%S')
    selected_time_db = datetime.time(selected_date_dt).strftime('%H%M')

    # gather info needed for message and SQL
    ao_channel_id = input_data['channel']['id']

    try:
        DbManager.update_records(cls=Master, filters=[
            Master.team_id == team_id,
            Master.ao_channel_id == ao_channel_id,
            Master.event_date == selected_date_dt.date(),
            Master.event_time == selected_time_db 
        ], fields={
            Master.q_pax_id: user_id,
            Master.q_pax_name: user_name
        })
        return UpdateResponse(success = True, message=f"Got it - I've made your updates!")
    except Exception as e:
        logger.error(f"Error updating: {e}")
        return UpdateResponse(success = False, message = f"Sorry, there was an error of some sort; please try again or contact your local administrator / Weasel Shaker. Errors:\n{e}")
    