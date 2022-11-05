import pandas as pd

from qsignups.database import my_connect
from qsignups.slack import utilities
from qsignups import actions

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

    action_button = utilities.make_button("Submit", action_id = actions.ADD_AO_ACTION)
    blocks.append(action_button)
    blocks.append(utilities.make_cancel_button())

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
    try:
        with my_connect(team_id) as mydb:
            sql_ao_list = f"SELECT * FROM {mydb.db}.qsignups_aos WHERE team_id = '{team_id}' ORDER BY REPLACE(ao_display_name, 'The ', '');"
            ao_df = pd.read_sql(sql_ao_list, mydb.conn)
    except Exception as e:
        logger.error(f"Error pulling AO list: {e}")

    ao_options = []
    for index, row in ao_df.iterrows():
        new_option = {
            "text": {
                "type": "plain_text",
                "text": row['ao_display_name'],
                "emoji": True
            },
            "value": row['ao_channel_id']
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
