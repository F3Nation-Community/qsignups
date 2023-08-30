from database import DbManager
from database.orm import AO
from database.orm.views import vwAOsSort

from slack import actions, forms, inputs

def add_form(team_id, user_id, client, logger):
    logger.info('gather input data')
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Select an AO channel:*"
      }
        },
        {
            "type": "input",
            "block_id": "add_ao_channel_select",
            "element": {
                "type": "channels_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select a channel",
                    "emoji": True
                },
                "action_id": "add_ao_channel_select"
            },
            "label": {
                "type": "plain_text",
                "text": "Channel associated with AO",
                "emoji": True
            }
        },
        {
            "type": "input",
            "block_id": "ao_display_name",
            "element": {
                "type": "plain_text_input",
                "action_id": "ao_display_name",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Weasel's Ridge"
                }
            },
            "label": {
                "type": "plain_text",
                "text": "AO Title"
            }
        },
        {
            "type": "input",
            "block_id": "ao_location_subtitle",
            "element": {
                "type": "plain_text_input",
                "multiline": True,
                "action_id": "ao_location_subtitle",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Oompa Loompa Kingdom"
                }
            },
            "label": {
                "type": "plain_text",
                "text": "Location (township, park, etc.)"
            }
        }
    ]

    blocks.append(forms.make_action_button_row([
        inputs.make_submit_button(actions.ADD_AO_ACTION),
        inputs.CANCEL_BUTTON,
    ]))

    try:
        client.views_publish(
            user_id=user_id,
            view={
                "type": "home",
                "blocks": blocks
            }
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")
        print(e)

def edit_form(team_id, user_id, client, logger):

    # list of AOs for dropdown
    aos: list[vwAOsSort] = DbManager.find_records(vwAOsSort, [vwAOsSort.team_id == team_id])
    ao_list = [ao.ao_display_name for ao in aos]

    ao_options = []
    for ao in aos:
        new_option = {
            "text": {
                "type": "plain_text",
                "text": ao.ao_display_name,
                "emoji": True
            },
            "value": ao.ao_channel_id
        }
        ao_options.append(new_option)

    # Build blocks
    blocks = [
        {
            "type": "section",
            "block_id": "edit_ao_select",
            "text": {
                "type": "mrkdwn",
                "text": "Please select an AO to edit:"
            },
            "accessory": {
                "action_id": "edit_ao_select",
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select an AO"
                },
                "options": ao_options
            }
        }
    ]

    # Publish view
    try:
        client.views_publish(
            user_id=user_id,
            view={
                "type": "home",
                "blocks": blocks
            }
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")
        print(e)

def delete_form(team_id, user_id, client, logger):

    # list of AOs for dropdown
    aos: list[vwAOsSort] = DbManager.find_records(vwAOsSort, [vwAOsSort.team_id == team_id])

    ao_options = []
    for ao in aos:
        new_option = {
            "text": {
                "type": "plain_text",
                "text": ao.ao_display_name,
                "emoji": True
            },
            "value": ao.ao_channel_id
        }
        ao_options.append(new_option)

    # Build blocks
    blocks = [
        {
            "type": "section",
            "block_id": actions.DELETE_AO_SELECT_ACTION,
            "text": {
                "type": "mrkdwn",
                "text": "Please select an AO to delete:"
            },
            "accessory": {
                "action_id": actions.DELETE_AO_SELECT_ACTION,
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select an AO"
                },
                "options": ao_options
            }
        }
    ]

    # Publish view
    try:
        client.views_publish(
            user_id=user_id,
            view={
                "type": "home",
                "blocks": blocks
            }
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")
        print(e)

def pull_aos(team_id):
    aos: list[AO] = DbManager.find_records(AO, [AO.team_id == team_id])
    aos_list, aos_sort = {}, {}
    for index, ao in enumerate(aos):
        aos_list[index] = ao.ao_display_name
        aos_sort[index] = ao.ao_display_name.replace('The ', '')
    
    aos_sort = dict(sorted(aos_sort.items(), key=lambda x:x[1]))
    return([aos_list[i] for i in aos_sort.keys()])
