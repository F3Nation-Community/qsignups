import pandas as pd

from qsignups.database import my_connect
from qsignups.slack import utilities
from qsignups import actions

def general_form(team_id, user_id, client, logger):
    # Pull current settings
    success_status = False
    region_df = None
    try:
        with my_connect(team_id) as mydb:
            sql_pull = f"SELECT * FROM {mydb.db}.qsignups_regions WHERE team_id = '{team_id}';"
            region_df = pd.read_sql(sql_pull, mydb.conn).iloc[0]
    except Exception as e:
        logger.error(f"Error pulling region info: {e}")
        print(e)

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "General Region Settings",
                "emoji": True
            }
        },
        {
            "type": "input",
            "block_id": "weinke_channel_select",
            "element": {
                "type": "channels_select",
                # "initial_channel": region_df['weekly_weinke_channel'],
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select a channel",
                    "emoji": True
                },
                "action_id": "weinke_channel_select"
            },
            "label": {
                "type": "plain_text",
                "text": "Public channel for posting weekly schedules:",
                "emoji": True
            }
        },
        {
            "type": "input",
            "block_id": "q_reminder_enable",
            "element": {
                "type": "radio_buttons",
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Enable Q reminders",
                            "emoji": True
                        },
                        "value": "enable"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Disable Q reminders",
                            "emoji": True
                        },
                        "value": "disable"
                    },
                ],
                "action_id": "q_reminder_enable"
            },
            "label": {
                "type": "plain_text",
                "text": "Enable Q Reminders?",
                "emoji": True
            }
        },
        {
            "type": "input",
            "block_id": "ao_reminder_enable",
            "element": {
                "type": "radio_buttons",
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Enable AO reminders",
                            "emoji": True
                        },
                        "value": "enable"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Disable AO reminders",
                            "emoji": True
                        },
                        "value": "disable"
                    },
                ],
                "action_id": "ao_reminder_enable"
            },
            "label": {
                "type": "plain_text",
                "text": "Enable AO Reminders?",
                "emoji": True
            }
        },
        {
            "type": "input",
            "block_id": "google_calendar_id",
            "element": {
                "type": "plain_text_input",
                "action_id": "google_calendar_id",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Google Calendar ID"
                },
                "initial_value": region_df['google_calendar_id'] or ''
            },
            "label": {
                "type": "plain_text",
                "text": "To connect to a google calendar, provide the ID"
            },
            "optional": True
        }
     ]

    action_button = utilities.make_button("Submit", action_id = actions.EDIT_SETTINGS_ACTION)
    cancel_button = utilities.make_cancel_button()
    blocks.append(action_button)
    blocks.append(cancel_button)

    try:
        print(blocks)
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
