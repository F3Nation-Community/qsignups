from datetime import date
import pandas as pd

from qsignups.database import my_connect
from qsignups.slack import utilities
from qsignups import actions

def add_form(team_id, user_id, client, logger):

    # list of AOs for dropdown
    try:
        with my_connect(team_id) as mydb:
            sql_ao_list = f"SELECT ao_display_name FROM {mydb.db}.qsignups_aos WHERE team_id = '{team_id}' ORDER BY REPLACE(ao_display_name, 'The ', '');"
            ao_list = pd.read_sql(sql_ao_list, mydb.conn)
            ao_list = ao_list['ao_display_name'].values.tolist()
    except Exception as e:
        logger.error(f"Error pulling AO list: {e}")

    ao_options = []
    for option in ao_list:
        new_option = {
            "text": {
                "type": "plain_text",
                "text": option,
                "emoji": True
            },
            "value": option
        }
        ao_options.append(new_option)

    day_list = [
        'Monday',
        'Tuesday',
        'Wednesday',
        'Thursday',
        'Friday',
        'Saturday',
        'Sunday'
    ]
    day_options = []
    for option in day_list:
        new_option = {
            "text": {
                "type": "plain_text",
                "text": option,
                "emoji": True
            },
            "value": option
        }
        day_options.append(new_option)

    event_type_list = ['Bootcamp', 'QSource', 'Custom']
    event_type_options = []
    for option in event_type_list:
        new_option = {
            "text": {
                "type": "plain_text",
                "text": option,
                "emoji": True
            },
            "value": option
        }
        event_type_options.append(new_option)


    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Is this a recurring or single event?*"
	    }
        },
        {
            "type": "actions",
            "block_id": "recurring_select_block",
            "elements": [
                {
                    "type": "radio_buttons",
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Recurring event",
                                "emoji": True
                            },
                            "value": "recurring"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Single event",
                                "emoji": True
                            },
                            "value": "single"
                        },
                    ],
                    "action_id": "add_event_recurring_select_action",
                    "initial_option": {
                        "text": {
                            "type": "plain_text",
                            "text": "Recurring event",
                            "emoji": True
                        },
                        "value": "recurring"
                    }
                }
            ]
        },
        {
            "type": "input",
            "block_id": "event_type_select",
            "element": {
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select an event type",
                    "emoji": True
                },
                "options": event_type_options,
                "action_id": "event_type_select_action",
                "initial_option": event_type_options[0]
            },
            "label": {
                "type": "plain_text",
                "text": "Event Type",
                "emoji": True
            }
        },
        {
            "type": "input",
            "block_id": "event_type_custom",
            "element": {
                "type": "plain_text_input",
                "action_id": "event_type_custom",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Custom Event Name"
                },
                "initial_value": "CustomEventType"
            },
            "label": {
                "type": "plain_text",
                "text": "If Custom selected, please specify"
            },
            "optional": True
        },
        {
            "type": "input",
            "block_id": "ao_display_name_select",
            "element": {
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select an AO",
                    "emoji": True
                },
                "options": ao_options,
                "action_id": "ao_display_name_select_action"
            },
            "label": {
                "type": "plain_text",
                "text": "AO",
                "emoji": True
            }
        },
        {
            "type": "input",
            "block_id": "event_day_of_week_select",
            "element": {
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select a day",
                    "emoji": True
                },
                "options": day_options,
                "action_id": "event_day_of_week_select_action"
            },
            "label": {
                "type": "plain_text",
                "text": "Day of Week",
                "emoji": True
            }
        },
        {
            "type": "input",
            "block_id": "event_start_time_select",
            "element": {
                "type": "timepicker",
                "initial_time": "05:30",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select time",
                    "emoji": True
                },
                "action_id": "event_start_time_select"
            },
            "label": {
                "type": "plain_text",
                "text": "Event Start",
                "emoji": True
            }
    },
        {
            "type": "input",
            "block_id": "event_end_time_select",
            "element": {
                "type": "timepicker",
                "initial_time": "06:30",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select time",
                    "emoji": True
                },
                "action_id": "event_end_time_select"
            },
            "label": {
                "type": "plain_text",
                "text": "Event End",
                "emoji": True
            }
    },
        {
            "type": "input",
            "block_id": "add_event_datepicker",
            "element": {
                "type": "datepicker",
                "initial_date": date.today().strftime('%Y-%m-%d'),
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select date",
                    "emoji": True
                },
                "action_id": "add_event_datepicker"
            },
            "label": {
                "type": "plain_text",
                "text": "Start Date",
                "emoji": True
            }
        },
        utilities.make_action_buttons([
          utilities.ActionButton(text = 'Submit', action = actions.ADD_EVENT_ACTION),
          utilities.CANCEL_BUTTON
        ]),
        {
          	"type": "context",
          	"elements": [
                {
                    "type": "mrkdwn",
                    "text": "Please wait after hitting Submit, and do not hit it more than once"
                }
            ]
        }
    ]
    print(blocks)
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
            "block_id": "ao_select_block",
            "text": {
                "type": "mrkdwn",
                "text": "Please select an AO to edit:"
            },
            "accessory": {
                "action_id": "edit_event_ao_select",
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

def delete_single_form(team_id, user_id, client, logger):
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
            "block_id": "delete_single_event_ao_select",
            "text": {
                "type": "mrkdwn",
                "text": "Please select an AO to delete an event from:"
            },
            "accessory": {
                "action_id": "delete_single_event_ao_select",
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
