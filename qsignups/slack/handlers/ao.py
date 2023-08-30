from database import DbManager
from database.orm import Weekly, Master, AO
from utilities import safe_get
from . import UpdateResponse
import ast
from datetime import date, datetime
from sqlalchemy import func

def edit(client, user_id, team_id, logger, page_label, input_data) -> UpdateResponse:
    
    # Parse inputs
    label, ao_display_name, ao_channel_id = page_label.replace('*','').split('\n')
    ao_display_name = input_data['ao_display_name']['ao_display_name']['value']
    ao_location_subtitle = input_data['ao_location_subtitle']['ao_location_subtitle']['value']

    # Attempt updates
    try:
        DbManager.update_records(cls=AO, filters=[
            AO.ao_channel_id == ao_channel_id
        ], fields={
            AO.ao_display_name: ao_display_name,
            AO.ao_location_subtitle: ao_location_subtitle
        })
        return UpdateResponse(success = True, message=f"Got it - I've made your updates!")
    except Exception as e:
        logger.error(f"Error updating: {e}")
        return UpdateResponse(success = False, message = f"Sorry, there was an error of some sort; please try again or contact your local administrator / Weasel Shaker. Errors:\n{e}")

def delete(client, user_id, team_id, logger, ao_channel_id) -> UpdateResponse:

    # Attempt deletion
    try:
        DbManager.delete_records(cls=AO, filters=[
            AO.ao_channel_id == ao_channel_id
        ])
        DbManager.delete_records(cls=Weekly, filters=[
            Weekly.ao_channel_id == ao_channel_id
        ])
        DbManager.delete_records(cls=Master, filters=[
            Master.ao_channel_id == ao_channel_id
        ])
        return UpdateResponse(success = True, message=f"Got it - I've made your updates!")
    except Exception as e:
        logger.error(f"Error deleting AO: {e}")
        return UpdateResponse(success = False, message = f"Sorry, there was an error of some sort; please try again or contact your local administrator / Weasel Shaker. Errors:\n{e}")
    
def insert(client, user_id, team_id, logger, input_data) -> UpdateResponse:
    
    # Parse inputs
    ao_channel_id = safe_get(input_data, 'add_ao_channel_select', 'add_ao_channel_select', 'selected_channel')
    ao_display_name = safe_get(input_data, 'ao_display_name', 'ao_display_name', 'value')
    ao_location_subtitle = safe_get(input_data, 'ao_location_subtitle','ao_location_subtitle', 'value')
    
    # replace double quotes with single quotes
    ao_display_name = ao_display_name.replace('"',"'")
    if ao_location_subtitle:
        ao_location_subtitle = ao_location_subtitle.replace('"',"'")
    else:
        ao_location_subtitle = '' # TODO: I don't like this, but this field is currently non-nullable

    # Attempt insert
    try:
        ao_record = DbManager.create_record(AO(
            ao_channel_id = ao_channel_id,
            ao_display_name = ao_display_name,
            ao_location_subtitle = ao_location_subtitle,
            team_id = team_id
        ))
        return UpdateResponse(success = True, message=f"Got it - I've made your updates!")
    except Exception as e:
        logger.error(f"Error inserting: {e}")
        return UpdateResponse(success = False, message = f"Sorry, there was an error of some sort; please try again or contact your local administrator / Weasel Shaker. Errors:\n{e}")
