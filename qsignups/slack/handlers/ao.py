from database import DbManager
from database.orm import Weekly, Master, AO
from utilities import safe_get
from . import UpdateResponse
from slack import inputs

def edit(client, user_id, team_id, logger, ao_channel_id, input_data) -> UpdateResponse:

    # Attempt updates
    try:
        DbManager.update_records(cls=AO, filters=[
            AO.ao_channel_id == ao_channel_id
        ], fields={
            AO.ao_display_name: inputs.AO_TITLE_INPUT.get_selected_value(input_data),
            AO.ao_location_subtitle: inputs.AO_SUBTITLE_INPUT.get_selected_value(input_data),
            AO.google_calendar_id: inputs.GOOGLE_CALENDAR_SELECT.get_selected_value(input_data),
            AO.map_url: inputs.MAP_URL_INPUT.get_selected_value(input_data),
            AO.latitude: inputs.LATITUDE_INPUT.get_selected_value(input_data),
            AO.longitude: inputs.LONGITUDE_INPUT.get_selected_value(input_data)
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
    ao_channel_id = inputs.AO_CHANNEL_SELECT.get_selected_value(input_data)
    ao_display_name = inputs.AO_TITLE_INPUT.get_selected_value(input_data)
    ao_location_subtitle = inputs.AO_SUBTITLE_INPUT.get_selected_value(input_data)

    # replace double quotes with single quotes
    ao_display_name = ao_display_name.replace('"',"'")
    if ao_location_subtitle:
        ao_location_subtitle = ao_location_subtitle.replace('"',"'")
    else:
        ao_location_subtitle = '' # TODO: I don't like this, but this field is currently non-nullable

    # Attempt insert
    try:
        DbManager.create_record(AO(
            ao_channel_id = ao_channel_id,
            ao_display_name = ao_display_name,
            ao_location_subtitle = ao_location_subtitle,
            team_id = team_id,
            map_url = inputs.MAP_URL_INPUT.get_selected_value(input_data),
            google_calendar_id = inputs.GOOGLE_CALENDAR_SELECT.get_selected_value(input_data),
            latitude = inputs.LATITUDE_INPUT.get_selected_value(input_data),
            longitude = inputs.LONGITUDE_INPUT.get_selected_value(input_data)
        ))
        return UpdateResponse(success = True, message=f"Got it - I've made your updates!")
    except Exception as e:
        logger.error(f"Error inserting: {e}")
        return UpdateResponse(success = False, message = f"Sorry, there was an error of some sort; please try again or contact your local administrator / Weasel Shaker. Errors:\n{e}")
