import logging
import json
import os
import mysql.connector
from contextlib import ContextDecorator
from datetime import datetime, timezone, timedelta, date
import pandas as pd

from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from slack_bolt.adapter.aws_lambda.lambda_s3_oauth_flow import LambdaS3OAuthFlow


# process_before_response must be True when running on FaaS
app = App(
    process_before_response=True,
    oauth_flow=LambdaS3OAuthFlow(),
)

# Inputs
schedule_create_length_days = 365

# Construct class for connecting to the db
# Takes team_id as an input, pulls schema name from paxminer.regions
class my_connect(ContextDecorator):
    def __init__(self, team_id):
        self.conn = ''
        self.team_id = team_id
        self.db = ''

    def __enter__(self):
        self.conn = mysql.connector.connect(
            host=os.environ['DATABASE_HOST'],
            user=os.environ['ADMIN_DATABASE_USER'],
            passwd=os.environ['ADMIN_DATABASE_PASSWORD']
        )

        # sql_select = f'SELECT schema_name, user, password FROM paxminer.regions WHERE team_id = {self.team_id};'

        # with self.conn.cursor() as mycursor:
        #     mycursor.execute(sql_select)
        #     db, user, password = mycursor.fetchone()
        db = 'f3stcharles'

        self.db = db
        return self

    def __exit__(self, *exc):
        self.conn.close()
        return False

# Helper functions
def safeget(dct, *keys):
    for key in keys:
        try:
            dct = dct[key]
        except KeyError:
            return None
    return dct

def get_channel_id_and_name(body, logger):
    # returns channel_iid, channel_name if it exists as an escaped parameter of slashcommand
    user_id = body.get("user_id")
    # Get "text" value which is everything after the /slash-command
    # e.g. /slackblast #our-aggregate-backblast-channel
    # then text would be "#our-aggregate-backblast-channel" if /slash command is not encoding
    # but encoding needs to be checked so it will be "<#C01V75UFE56|our-aggregate-backblast-channel>" instead
    channel_name = body.get("text") or ''
    channel_id = ''
    try:
        channel_id = channel_name.split('|')[0].split('#')[1]
        channel_name = channel_name.split('|')[1].split('>')[0]
    except IndexError as ierr:
        logger.error('Bad user input - cannot parse channel id')
    except Exception as error:
        logger.error('User did not pass in any input')
    return channel_id, channel_name


def get_channel_name(id, logger, client):
    channel_info_dict = client.conversations_info(
        channel=id
    )
    channel_name = safeget(channel_info_dict, 'channel', 'name') or None
    logger.info('channel_name is {}'.format(channel_name))
    return channel_name


def get_user_names(array_of_user_ids, logger, client):
    names = []
    for user_id in array_of_user_ids:
        user_info_dict = client.users_info(
            user=user_id
        )
        user_name = safeget(user_info_dict, 'user', 'profile', 'display_name') or safeget(
            user_info_dict, 'user', 'profile', 'real_name') or None
        if user_name:
            names.append(user_name)
        logger.info('user_name is {}'.format(user_name))
    logger.info('names are {}'.format(names))
    return names

def refresh_home_tab(client, user_id, logger, top_message, team_id):

    upcoming_qs_df = pd.DataFrame()
    try:
        with my_connect(team_id) as mydb:
            mycursor = mydb.conn.cursor()
            # Build SQL queries
            # list of upcoming Qs for user
            sql_upcoming_qs = f"""
            SELECT m.*, a.ao_display_name
            FROM {mydb.db}.schedule_master m
            LEFT JOIN {mydb.db}.aos a
            ON m.ao_channel_id = a.channel_id
            WHERE m.q_pax_id = "{user_id}"
                AND m.event_date > DATE("{date.today()}")
            ORDER BY m.event_date, m.event_time
            LIMIT 5; 
            """
            
            # list of AOs for dropdown
            sql_ao_list = f"SELECT * FROM {mydb.db}.aos WHERE qsignups_enabled = 1 ORDER BY REPLACE(ao_display_name, 'The ', '');"

            # weinke urls
            # sql_weinkes = f"SELECT current_week_weinke, next_week_weinke FROM paxminer.regions WHERE region_schema = '{mydb.db}';"
            sql_weinkes = f"SELECT current_week_weinke, next_week_weinke FROM {mydb.db}.schedule_weinkes WHERE region_schema = '{mydb.db}';"
            
            # Make pulls
            upcoming_qs_df = pd.read_sql(sql_upcoming_qs, mydb.conn, parse_dates=['event_date'])
            ao_list = pd.read_sql(sql_ao_list, mydb.conn)
            
            if os.environ['USE_WEINKES']:
                mycursor.execute(sql_weinkes)
                weinkes_list = mycursor.fetchone()
                current_week_weinke_url = weinkes_list[0]
                next_week_weinke_url = weinkes_list[1] 

    except Exception as e:
        logger.error(f"Error pulling user db info: {e}")

    # Extend top message with upcoming qs list
    if len(upcoming_qs_df) > 0:
        top_message += '\n\nYou have some upcoming Qs:'
        for index, row in upcoming_qs_df.iterrows():
            dt_fmt = row['event_date'].strftime("%m-%d-%Y")
            top_message += f"\n- {dt_fmt} @ {row['event_time']} at {row['ao_display_name']}" 

    # Build AO options list
    options = []
    for index, row in ao_list.iterrows():
        new_option = {
            "text": {
                "type": "plain_text",
                "text": row['ao_display_name']
            },
            "value": row['channel_id']
        }
        options.append(new_option)
    
    # Build view blocks
    blocks = [
        {
            "type": "section",
            "block_id": "section678",
            "text": {
                "type": "mrkdwn",
                "text": top_message
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "block_id": "ao_select_block",
            "text": {
                "type": "mrkdwn",
                "text": "Please select an AO to take a Q slot:"
            },
            "accessory": {
                "action_id": "ao-select",
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select an AO"
            },
            "options": options
            }
        }
    ]
    
    if os.environ['USE_WEINKES']:
        weinke_blocks = [
            {
                "type": "image",
                "title": {
                    "type": "plain_text",
                    "text": "This week's schedule",
                    "emoji": True
                },
                "image_url": current_week_weinke_url,
                "alt_text": "This week's schedule"
            },
            {
                "type": "image",
                "title": {
                    "type": "plain_text",
                    "text": "Next week's schedule",
                    "emoji": True
                },
                "image_url": next_week_weinke_url,
                "alt_text": "Next week's schedule"
            },
            {
                "type": "divider"
            }
        ]

        for block in weinke_blocks:
            blocks.append(block)

    # Optionally add admin button
    user_info_dict = client.users_info(
        user=user_id
    )
    if user_info_dict['user']['is_admin']:
        admin_button = {
            "type":"actions",
            "elements":[
                {
                    "type":"button",
                    "text":{
                        "type":"plain_text",
                        "text":"Manage Region Calendar",
                        "emoji":True
                    },
                    "action_id":"manage_schedule_button"
                }
            ]
        }
        blocks.append(admin_button)

    # Attempt to publish view
    try:
        logger.debug(blocks)
        client.views_publish(
            user_id=user_id,
            view={
                "type": "home",
                "blocks":blocks
            }
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")
        print(e)


@app.event("app_mention")
def handle_app_mentions(body, say, logger):
    logger.info(f'INFO: {body}')
    say("What's up, world?")


@app.command("/hello-bolt-python-lambda")
def respond_to_slack_within_3_seconds(ack):
    # This method is for synchronous communication with the Slack API server
    ack("Thanks!")

@app.event("app_home_opened")
def update_home_tab(client, event, logger, context):
    logger.info(event)
    user_id = context["user_id"]
    team_id = context["team_id"]
    user_name = (get_user_names([user_id], logger, client))[0]
    top_message = f'Welcome to QSignups, {user_name}!' 
    refresh_home_tab(client, user_id, logger, top_message, team_id)


# triggers when user chooses to schedule a q
# @app.action("schedule_q_button")
# def handle_take_q_button(ack, body, client, logger, context):
#     ack()
#     logger.info(body)
#     user_id = context["user_id"]
#     team_id = context["team_id"]
#     refresh_home_tab(client, user_id, logger)

# triggers when user chooses to manager the schedule
@app.action("manage_schedule_button")
def handle_manager_schedule_button(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    team_id = context["team_id"]
    
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Choose an option for managing the schedule:"
            }
        }
    ]

    button_list = [
        "Add an AO",
        "Add an event",
        "Edit an event"
    ]

    for button in button_list:
        new_block = {
            "type":"actions",
            "elements":[
                {
                    "type":"button",
                    "text":{
                        "type":"plain_text",
                        "text":button,
                        "emoji":True
                    },
                    "action_id":"manage_schedule_option_button",
                    "value":button
                }
            ]
        }
        blocks.append(new_block)

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

# triggers when user selects a manage schedule option
@app.action("manage_schedule_option_button")
def handle_manage_schedule_option_button(ack, body, client, logger, context):
    ack()
    logger.info(body)

    selected_action = body['actions'][0]['value']
    user_id = context["user_id"]
    team_id = context["team_id"]

    # 'Add an AO' selected
    if selected_action == 'Add an AO':
        logger.info('gather input data')
        blocks = [
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
                "block_id": "ao_channel_id",
                "element": {
                    "type": "channels_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select the AO",
                        "emoji": True
                    },
                    "action_id": "ao_channel_id"
                },
                "label": {
                    "type": "plain_text",
                    "text": "Slack channel",
                    "emoji": True
                }
            },
            {
                "type": "input",
                "block_id": "ao_location_subtitle",
                "element": {
                    "type": "plain_text_input",
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

        action_button = {
            "type":"actions",
            "elements":[
                {
                    "type":"button",
                    "text":{
                        "type":"plain_text",
                        "text":"Submit",
                        "emoji":True
                    },
                    "action_id":"submit_add_ao_button",
                    "style":"primary",
                    "value":"Submit"
                }
            ]    
        }
        cancel_button = {
            "type":"actions",
            "elements":[
                {
                    "type":"button",
                    "text":{
                        "type":"plain_text",
                        "text":"Cancel",
                        "emoji":True
                    },
                    "action_id":"cancel_button_select",
                    "style":"danger",
                    "value":"Cancel"
                }
            ]    
        }
        blocks.append(action_button)
        blocks.append(cancel_button)

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
    # Add an event
    elif selected_action == 'Add an event':
        logging.info('add an event')

        # list of AOs for dropdown
        try:
            with my_connect(team_id) as mydb:
                sql_ao_list = f"SELECT ao_display_name FROM {mydb.db}.aos WHERE qsignups_enabled = 1 ORDER BY REPLACE(ao_display_name, 'The ', '');"
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

        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Is this a recurring or single event?"
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
                                    "text": "Recurring event / beatdown",
                                    "emoji": True
                                },
                                "value": "recurring"
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "Single event / beatdown",
                                    "emoji": True
                                },
                                "value": "single"
                            },
                        ],
                        "action_id": "add_event_recurring_select_action",
                        "initial_option": {
                            "text": {
                                "type": "plain_text",
                                "text": "Recurring event / beatdown",
                                "emoji": True
                            },
                            "value": "recurring"
                        }
                    }
                ]
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
                "block_id": "event_time_select",
                "element": {
                    "type": "timepicker",
                    "initial_time": "05:30",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select time",
                        "emoji": True
                    },
                    "action_id": "event_time_select"
                },
                "label": {
                    "type": "plain_text",
                    "text": "Beatdown Start",
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
            {
                "type": "actions",
                "block_id": "submit_cancel_buttons",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Submit",
                            "emoji": True
                        },
                        "value": "submit",
                        "action_id": "submit_add_event_button",
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Cancel",
                            "emoji": True
                        },
                        "value": "cancel",
                        "action_id": "cancel_button_select",
                        "style": "danger"
                    }
                ]
            },
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
    # Edit an event
    elif selected_action == 'Edit an event':
        logging.info('Edit an event')

        # list of AOs for dropdown
        try:
            with my_connect(team_id) as mydb:
                sql_ao_list = f"SELECT * FROM {mydb.db}.aos WHERE qsignups_enabled = 1 ORDER BY REPLACE(ao_display_name, 'The ', '');"
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
                "value": row['channel_id']
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

@app.action("add_event_recurring_select_action")
def handle_add_event_recurring_select_action(ack, body, client, logger, context):
    ack()
    logger.info(body)
    print(body)
    user_id = context["user_id"]
    team_id = context["team_id"]
    recurring_select_option = body['view']['state']['values']['recurring_select_block']['add_event_recurring_select_action']['selected_option']
    recurring_select = recurring_select_option['value']

    logging.info('add an event - switch recurring type')

    # list of AOs for dropdown
    try:
        with my_connect(team_id) as mydb:
            sql_ao_list = f"SELECT ao_display_name FROM {mydb.db}.aos WHERE qsignups_enabled = 1 ORDER BY REPLACE(ao_display_name, 'The ', '');"
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
            "elements": [
                {
                    "type": "radio_buttons",
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Recurring event / beatdown",
                                "emoji": True
                            },
                            "value": "recurring"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Single event / beatdown",
                                "emoji": True
                            },
                            "value": "single"
                        },
                    ],
                    "action_id": "add_event_recurring_select_action",
                    "initial_option": recurring_select_option
                }
            ]
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
        }
    ]
    new_blocks = []
    if recurring_select == 'recurring':
        new_blocks.append([
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
                "block_id": "event_time_select",
                "element": {
                    "type": "timepicker",
                    "initial_time": "05:30",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select time",
                        "emoji": True
                    },
                    "action_id": "event_time_select"
                },
                "label": {
                    "type": "plain_text",
                    "text": "Beatdown Start",
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
            {
                "type": "actions",
                "block_id": "submit_cancel_buttons",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Submit",
                            "emoji": True
                        },
                        "value": "submit",
                        "action_id": "submit_add_event_button",
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Cancel",
                            "emoji": True
                        },
                        "value": "cancel",
                        "action_id": "cancel_button_select",
                        "style": "danger"
                    }
                ]
            },
            {
            "type": "context",
            "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Please wait after hitting Submit, and do not hit it more than once"
                    }
                ]
            }
        ])
    else:
        # TODO: have "other" / freeform option
        # TODO: add this to form
        special_list = [
            'None',
            'The Forge',
            'VQ',
            'F3versary',
            'Birthday Q',
            'AO Launch'
        ]
        special_options = []
        for option in special_list:
            new_option = {
                "text": {
                    "type": "plain_text",
                    "text": option,
                    "emoji": True
                },
                "value": option
            }
            special_options.append(new_option)

        new_blocks.append([
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
                    "text": "Event Date",
                    "emoji": True
                }
            },
            {
                "type": "input",
                "block_id": "event_time_select",
                "element": {
                    "type": "timepicker",
                    "initial_time": "05:30",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select time",
                        "emoji": True
                    },
                    "action_id": "event_time_select"
                },
                "label": {
                    "type": "plain_text",
                    "text": "Event Start",
                    "emoji": True
                }
            }, 
            {
                "type": "actions",
                "block_id": "submit_cancel_buttons",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Submit",
                            "emoji": True
                        },
                        "value": "submit",
                        "action_id": "submit_add_single_event_button",
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Cancel",
                            "emoji": True
                        },
                        "value": "cancel",
                        "action_id": "cancel_button_select",
                        "style": "danger"
                    }
                ]
            }
        ])

    try:
        for block in new_blocks:
            blocks.append(block)
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

@app.action("edit_event_ao_select")
def handle_edit_event_ao_select(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    team_id = context["team_id"]
    ao_display_name = body['actions'][0]['selected_option']['text']['text']
    ao_channel_id = body['actions'][0]['selected_option']['value']

    # Pull upcoming schedule from db
    try:
        with my_connect(team_id) as mydb:
            # TODO: make this specific to event type
            sql_pull = f'''
            SELECT m.*, a.ao_display_name
            FROM {mydb.db}.schedule_master m
            INNER JOIN {mydb.db}.aos a
            ON m.ao_channel_id = a.channel_id
            WHERE a.ao_channel_id = "{ao_channel_id}"
                AND m.event_date > DATE("{date.today()}")
                AND m.event_date <= DATE("{date.today() + timedelta(weeks=12)}");
            '''
            logging.info(f'Pulling from db, attempting SQL: {sql_pull}')
            results_df = pd.read_sql_query(sql_pull, mydb.conn, parse_dates=['event_date'])
    except Exception as e:
        logger.error(f"Error pulling from schedule_master: {e}")

    # Construct view
    # Top of view
    blocks = [{
        "type": "section",
        "text": {"type": "mrkdwn", "text": "Please select a Q slot to edit for:"}
    },
    {
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*{ao_display_name}*"}
    },
    {
        "type": "divider"
    }]

    # Show next x number of events
    # TODO: future add: make a "show more" button?
    results_df['event_date_time'] = pd.to_datetime(results_df['event_date'].dt.strftime('%Y-%m-%d') + ' ' + results_df['event_time'], infer_datetime_format=True)
    for index, row in results_df.iterrows():
        # Pretty format date
        date_fmt = row['event_date_time'].strftime("%a, %m-%d @ %H%M")
        date_fmt_value = row['event_date_time'].strftime('%Y-%m-%d %H:%M:%S')
        
        # Build buttons
        if row['q_pax_id'] is None:
            date_status = "OPEN!"
        else: 
            date_status = row['q_pax_name']
        
        action_id = "edit_single_event_button"
        value = date_fmt_value + '|' + row['ao_display_name']
        
        # Button template
        new_button = {
            "type":"actions",
            "elements":[
                {
                    "type":"button",
                    "text":{
                        "type":"plain_text",
                        "text":f"{date_fmt}: {date_status}",
                        "emoji":True
                    },
                    "action_id":action_id,
                    "value":value
                }
            ]
        }
        
        # Append button to list
        blocks.append(new_button)
    
    # Cancel button
    new_button = {
        "type":"actions",
        "elements":[
            {
                "type":"button",
                "text":{
                    "type":"plain_text",
                    "text":"Cancel",
                    "emoji":True
                },
                "action_id":"cancel_button_select",
                "value":"cancel",
                "style":"danger"
            }
        ]
    }
    blocks.append(new_button)
    
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

@app.action("submit_add_ao_button")
def handle_submit_add_ao_button(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    team_id = context["team_id"]

    # Gather inputs from form
    input_data = body['view']['state']['values']
    ao_channel_id = input_data['ao_channel_id']['ao_channel_id']['selected_channel']
    ao_display_name = input_data['ao_display_name']['ao_display_name']['value']
    ao_location_subtitle = input_data['ao_location_subtitle']['ao_location_subtitle']['value']

    # TODO: test to see if there's a " in the display_name or location - this will make the query below bomb

    # Write to AO table
    success_status = False
    try:
        with my_connect(team_id) as mydb:

            sql_update = f"""
            UPDATE {mydb.db}.aos
            SET qsignups_enabled = 1,
                ao_display_name = "{ao_display_name}",
                ao_location_subtitle = "{ao_location_subtitle}"
            WHERE channel_id = "{ao_channel_id}"
            ;
            """
            logger.info(f"Attempting SQL UPDATE: {sql_update}")
            
            mycursor = mydb.conn.cursor()
            mycursor.execute(sql_update)
            mycursor.execute("COMMIT;")
            success_status = True
    except Exception as e:
        logger.error(f"Error writing to db: {e}")
        error_msg = e

    # Take the user back home
    if success_status:
        top_message = f"Success! Added {ao_display_name} to the list of AOs on the schedule"
    else:
        top_message = f"Sorry, there was a problem of some sort; please try again or contact your local administrator / Weasel Shaker. Error:\n{error_msg}"
    
    refresh_home_tab(client, user_id, logger, top_message, team_id)

@app.action("submit_add_event_button")
def handle_submit_add_event_button(ack, body, client, logger, context):
    ack()
    logger.info(body)  
    user_id = context["user_id"]
    team_id = context["team_id"]

    # Gather inputs from form
    input_data = body['view']['state']['values']
    ao_display_name = input_data['ao_display_name_select']['ao_display_name_select_action']['selected_option']['value']
    event_day_of_week = input_data['event_day_of_week_select']['event_day_of_week_select_action']['selected_option']['value']
    starting_date = input_data['add_event_datepicker']['add_event_datepicker']['selected_date']
    event_time = input_data['event_time_select']['event_time_select']['selected_time'].replace(':','')
    event_type = 'Beatdown' # eventually this will be dynamic
    event_recurring = True # this would be false for one-time events

    # Grab channel id
    try:
        with my_connect(team_id) as mydb:
            mycursor = mydb.conn.cursor()
            mycursor.execute(f'SELECT channel_id FROM {mydb.db}.aos WHERE ao_display_name = "{ao_display_name}";')
            ao_channel_id = mycursor.fetchone()[0]
    except Exception as e:
           logger.error(f"Error pulling from db: {e}")

    # Write to weekly table
    try:
        with my_connect(team_id) as mydb:
            sql_insert = f"""
            INSERT INTO {mydb.db}.schedule_weekly (ao_channel_id, event_day_of_week, event_time, event_type)
            VALUES ("{ao_channel_id}", "{event_day_of_week}", "{event_time}", "{event_type}");
            """
            logger.info(f"Attempting SQL INSERT: {sql_insert}")

            mycursor = mydb.conn.cursor()
            mycursor.execute(sql_insert)
            mycursor.execute("COMMIT;")
    except Exception as e:
           logger.error(f"Error writing to db: {e}")

    # Write to master schedule table
    logger.info(f"Attempting SQL INSERT into schedule_master")
    success_status = False
    try:
        with my_connect(team_id) as mydb:
            mycursor = mydb.conn.cursor()
            iterate_date = datetime.strptime(starting_date, '%Y-%m-%d').date()
            while iterate_date < (date.today() + timedelta(days=schedule_create_length_days)):
                if iterate_date.strftime('%A') == event_day_of_week:
                    sql_insert = f"""
                    INSERT INTO {mydb.db}.schedule_master (ao_channel_id, event_date, event_time, event_day_of_week, event_type, event_recurring)
                    VALUES ("{ao_channel_id}", DATE("{iterate_date}"), "{event_time}", "{event_day_of_week}", "{event_type}", {event_recurring})    
                    """
                    mycursor.execute(sql_insert)
                    # print(sql_insert)
                iterate_date += timedelta(days=1)

            mycursor.execute("COMMIT;")
            success_status = True
    except Exception as e:
           logger.error(f"Error writing to schedule_master: {e}")
           error_msg = e

    # Give status message and return to home
    if success_status:
        top_message = f"Thanks, I got it! I've added {round(schedule_create_length_days/365)} year's worth of {event_type}s to the schedule for {event_day_of_week}s at {event_time} at {ao_display_name}."
    else:
        top_message = f"Sorry, there was an error of some sort; please try again or contact your local administrator / Weasel Shaker. Error:\n{error_msg}"
    refresh_home_tab(client, user_id, logger, top_message, team_id)

@app.action("submit_add_single_event_button")
def handle_submit_add_single_event_button(ack, body, client, logger, context):
    ack()
    logger.info(body)  
    user_id = context["user_id"]
    team_id = context["team_id"]

    # Gather inputs from form
    input_data = body['view']['state']['values']
    ao_display_name = input_data['ao_display_name_select']['ao_display_name_select_action']['selected_option']['value']
    event_date = input_data['add_event_datepicker']['add_event_datepicker']['selected_date']
    event_time = input_data['event_time_select']['event_time_select']['selected_time'].replace(':','')
    event_type = 'Beatdown' # eventually this will be dynamic
    event_recurring = False

    # Grab channel id
    try:
        with my_connect(team_id) as mydb:
            mycursor = mydb.conn.cursor()
            mycursor.execute(f'SELECT channel_id FROM {mydb.db}.aos WHERE ao_display_name = "{ao_display_name}";')
            ao_channel_id = mycursor.fetchone()[0]
    except Exception as e:
           logger.error(f"Error pulling from db: {e}")

    # Write to master schedule table
    logger.info(f"Attempting SQL INSERT into schedule_master")
    success_status = False
    try:
        with my_connect(team_id) as mydb:
            mycursor = mydb.conn.cursor()
            event_date_fmt = datetime.strptime(event_date, '%Y-%m-%d').date()
            sql_insert = f"""
            INSERT INTO {mydb.db}.schedule_master (ao_channel_id, event_date, event_time, event_day_of_week, event_type, event_recurring)
            VALUES ("{ao_channel_id}", DATE("{event_date_fmt}"), "{event_time}", "{event_date.strftime('%A')}", "{event_type}", {event_recurring})    
            """

            mycursor.execute(sql_insert)
            mycursor.execute("COMMIT;")
            success_status = True

    except Exception as e:
           logger.error(f"Error writing to schedule_master: {e}")
           error_msg = e

    # Give status message and return to home
    if success_status:
        top_message = f"Thanks, I got it! I've added your event to the schedule for {event_date_fmt} at {event_time} at {ao_display_name}."
    else:
        top_message = f"Sorry, there was an error of some sort; please try again or contact your local administrator / Weasel Shaker. Error:\n{error_msg}"
    refresh_home_tab(client, user_id, logger, top_message, team_id)


# triggered when user makes an ao selection
@app.action("ao-select")
def ao_select_slot(ack, client, body, logger, context):
    # acknowledge action and log payload
    ack()
    logger.info(body)
    
    user_id = context["user_id"]
    team_id = context["team_id"]
    ao_display_name = body['actions'][0]['selected_option']['text']['text']
    ao_channel_id = body['actions'][0]['selected_option']['value']

    # Pull upcoming schedule from db
    try:
        with my_connect(team_id) as mydb:
            # TODO: make this specific to event type
            sql_pull = f"""
            SELECT *
            FROM {mydb.db}.schedule_master
            WHERE ao_channel_id = '{ao_channel_id}'
                AND event_date > DATE('{date.today()}')
                AND event_date <= DATE('{date.today() + timedelta(weeks=10)}');
            """
            logging.info(f'Pulling from db, attempting SQL: {sql_pull}')

            results_df = pd.read_sql_query(sql_pull, mydb.conn, parse_dates=['event_date'])
    except Exception as e:
        logger.error(f"Error pulling from schedule_master: {e}")

    # Construct view
    # Top of view
    blocks = [{
        "type": "section",
        "text": {"type": "mrkdwn", "text": "Please select an open Q slot for:"}
    },
    {
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*{ao_display_name}*"}
    },
    {
        "type": "divider"
    }]

    # Show next x number of events
    # TODO: future add: make a "show more" button?
    results_df['event_date_time'] = pd.to_datetime(results_df['event_date'].dt.strftime('%Y-%m-%d') + ' ' + results_df['event_time'], infer_datetime_format=True)
    for index, row in results_df.iterrows():
        # Pretty format date
        date_fmt = row['event_date_time'].strftime("%a, %m-%d @ %H%M")
        
        # If slot is empty, show green button with primary (green) style button
        if row['q_pax_id'] is None:
            date_status = "OPEN!"
            date_style = "primary"
            action_id = "date_select_button"
            value = str(row['event_date_time'])
        # Otherwise default (grey) button, listing Qs name
        else:
            date_status = row['q_pax_name']
            date_style = "default"
            action_id = "taken_date_select_button" 
            value = str(row['event_date_time']) + '|' + row['q_pax_name']
        
        # TODO: add functionality to take self off schedule by clicking your already taken slot?
        # Button template
        new_button = {
            "type":"actions",
            "elements":[
                {
                    "type":"button",
                    "text":{
                        "type":"plain_text",
                        "text":f"{date_fmt}: {date_status}",
                        "emoji":True
                    },
                    "action_id":action_id,
                    "value":value
                }
            ]
        }
        if date_style == "primary":
            new_button['elements'][0]["style"] = "primary"
        
        # Append button to list
        blocks.append(new_button)
    
    # Cancel button
    new_button = {
        "type":"actions",
        "elements":[
            {
                "type":"button",
                "text":{
                    "type":"plain_text",
                    "text":"Cancel",
                    "emoji":True
                },
                "action_id":"cancel_button_select",
                "value":"cancel",
                "style":"danger"
            }
        ]
    }
    blocks.append(new_button)
    
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

# triggered when user selects open slot
@app.action("date_select_button")
def handle_date_select_button(ack, client, body, logger, context):
    # acknowledge action and log payload
    ack()
    logger.info(body)
    user_id = context["user_id"]
    team_id = context["team_id"]
    user_name = (get_user_names([user_id], logger, client))[0]

    # gather and format selected date and time
    selected_date = body['actions'][0]['value']
    selected_date_dt = datetime.strptime(selected_date, '%Y-%m-%d %H:%M:%S')
    selected_date_db = datetime.date(selected_date_dt).strftime('%Y-%m-%d')
    selected_time_db = datetime.time(selected_date_dt).strftime('%H%M')
    
    # gather info needed for message and SQL
    ao_display_name = body['view']['blocks'][1]['text']['text'].replace('*','')
    
    try:
        with my_connect(team_id) as mydb:
            sql_channel_pull = f'SELECT channel_id FROM {mydb.db}.aos WHERE ao_display_name = "{ao_display_name}";'
            ao_channel_id = pd.read_sql_query(sql_channel_pull, mydb.conn).iloc[0,0]
    except Exception as e:
        logger.error(f"Error pulling channel id: {e}")
    
    # Attempt db update
    success_status = False
    try:
        with my_connect(team_id) as mydb:
            sql_update = \
            f"""
            UPDATE {mydb.db}.schedule_master 
            SET q_pax_id = '{user_id}'
                , q_pax_name = '{user_name}'
            WHERE ao_channel_id = '{ao_channel_id}'
                AND event_date = DATE('{selected_date_db}')
                AND event_time = '{selected_time_db}'
            ;
            """
            logging.info(f'Attempting SQL UPDATE: {sql_update}')

            mycursor = mydb.conn.cursor()
            mycursor.execute(sql_update)
            mycursor.execute("COMMIT;")
            success_status = True
    except Exception as e:
        logger.error(f"Error updating schedule: {e}")
        error_msg = e

    # Generate top message and go back home
    if success_status:
        top_message = f"Got it, {user_name}! I have you down for the Q at *{ao_display_name}* on *{selected_date_dt.strftime('%A, %B %-d @ %H%M')}*"
        # TODO: if selected date was in weinke range (current or next week), update local weinke png
    else:
        top_message = f"Sorry, there was an error of some sort; please try again or contact your local administrator / Weasel Shaker. Error:\n{error_msg}"
    
    refresh_home_tab(client, user_id, logger, top_message, team_id)

# triggered when user selects an already-taken slot
@app.action("taken_date_select_button")
def handle_taken_date_select_button(ack, client, body, logger, context):
    # acknowledge action and log payload
    ack()
    logger.info(body)

    # Get user id / name / admin status
    user_id = context["user_id"]
    team_id = context["team_id"]
    user_info_dict = client.users_info(user=user_id)
    user_name = safeget(user_info_dict, 'user', 'profile', 'display_name') or safeget(
            user_info_dict, 'user', 'profile', 'real_name') or None
    user_admin = user_info_dict['user']['is_admin']

    selected_value = body['actions'][0]['value']
    selected_list = str.split(selected_value, '|')
    selected_date = selected_list[0]
    selected_date_dt = datetime.strptime(selected_date, '%Y-%m-%d %H:%M:%S')
    selected_user = selected_list[1]
    selected_ao = body['view']['blocks'][1]['text']['text'].replace('*','')
    

    if (user_name == selected_user) or user_admin:
        label = 'yourself' if user_name == selected_user else selected_user
        label2 = 'myself' if user_name == selected_user else selected_user
        blocks = [{
            "type": "section",
            "text": {
                "type": "mrkdwn", 
                "text": f"Would you like to edit or clear this slot?"
            }
        },
        {
            "type":"actions",
            "elements":[
                {
                    "type":"button",
                    "text":{
                        "type":"plain_text",
                        "text":f"Edit this event",
                        "emoji":True
                    },
                    "value":f"{selected_date}|{selected_ao}",
                    "action_id":"edit_single_event_button"
                }
            ]
        },
        {
            "type":"actions",
            "elements":[
                {
                    "type":"button",
                    "text":{
                        "type":"plain_text",
                        "text":f"Take {label2} off this Q slot",
                        "emoji":True
                    },
                    "value":f"{selected_date}|{selected_ao}",
                    "action_id":"clear_slot_button",
                    "style":"danger"
                }
            ]
        }, 
        {
            "type":"actions",
            "elements":[
                {
                    "type":"button",
                    "text":{
                        "type":"plain_text",
                        "text":"Cancel",
                        "emoji":True
                    },
                    "action_id":"cancel_button_select"
                }
            ]
        }]

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
    # Check to see if user matches selected user id OR if they are an admin
    # If so, bring up buttons:
    #   block 1: drop down to add special qualifier (VQ, Birthday Q, F3versary, Forge, etc.)
    #   block 2: danger button to take Q off slot
    #   block 3: cancel button that takes the user back home


# triggered when user hits cancel or some other button that takes them home
@app.action("edit_single_event_button")
def handle_edit_single_event_button(ack, client, body, logger, context):
    # acknowledge action and log payload
    ack()
    logger.info(body)
    user_id = context['user_id']
    team_id = context['team_id']
    # user_name = (get_user_names([user_id], logger, client))[0]

    # gather and format selected date and time
    selected_list = str.split(body['actions'][0]['value'],'|')
    selected_date = selected_list[0]
    selected_date_dt = datetime.strptime(selected_date, '%Y-%m-%d %H:%M:%S')
    selected_date_db = datetime.date(selected_date_dt).strftime('%Y-%m-%d')
    selected_time_db = datetime.time(selected_date_dt).strftime('%H%M')

    # gather info needed for input form
    ao_display_name = selected_list[1]

    try:
        with my_connect(team_id) as mydb:
            sql_channel_pull = f'''
            SELECT m.q_pax_id, m.q_pax_name, m.event_special, m.ao_channel_id 
            FROM {mydb.db}.schedule_master m
            INNER JOIN {mydb.db}.aos a
            ON m.ao_channel_id = a.channel_id
            WHERE a.ao_display_name = "{ao_display_name}"
                AND m.event_date = DATE("{selected_date_db}")
                AND m.event_time = "{selected_time_db}"
            ;
            '''
            result_df = pd.read_sql_query(sql_channel_pull, mydb.conn)
    except Exception as e:
        logger.error(f"Error pulling event info: {e}")
    
    q_pax_id = result_df.loc[0,'q_pax_id']
    q_pax_name = result_df.loc[0,'q_pax_name']
    event_special = result_df.loc[0,'event_special']
    ao_channel_id = result_df.loc[0,'ao_channel_id']

    # build special qualifier
    # TODO: have "other" / freeform option
    special_list = [
        'None',
        'The Forge',
        'VQ',
        'F3versary',
        'Birthday Q',
        'AO Launch'
    ]
    special_options = []
    for option in special_list:
        new_option = {
            "text": {
                "type": "plain_text",
                "text": option,
                "emoji": True
            },
            "value": option
        }
        special_options.append(new_option)
    
    if event_special in special_list:
        initial_special = special_options[special_list.index(event_special)]
    else:
        initial_special = special_options[0]

    user_select_element = {
        "type": "multi_users_select",
        "placeholder": {
            "type": "plain_text",
            "text": "Select the Q",
            "emoji": True
        },
        "action_id": "edit_event_q_select",
        "max_selected_items": 1
    }
    if q_pax_id is not None:
        user_select_element['initial_users'] = [q_pax_id]

    # Build blocks
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn", 
                "text": f"Editing info for:\n{selected_date_db} @ {selected_time_db} @ {ao_display_name}\nQ: {q_pax_name}"
            }
        },
        {
			"type": "input",
            "block_id": "edit_event_datepicker",
			"element": {
				"type": "datepicker",
				"initial_date": selected_date_dt.strftime('%Y-%m-%d'),
				"placeholder": {
					"type": "plain_text",
					"text": "Select date",
					"emoji": True
				},
				"action_id": "edit_event_datepicker"
			},
			"label": {
				"type": "plain_text",
				"text": "Event Date",
				"emoji": True
			}
		},
		{
			"type": "input",
            "block_id": "edit_event_timepicker",
			"element": {
				"type": "timepicker",
				"initial_time": datetime.time(selected_date_dt).strftime('%H:%M'),
				"placeholder": {
					"type": "plain_text",
					"text": "Select time",
					"emoji": True
				},
				"action_id": "edit_event_timepicker"
			},
			"label": {
				"type": "plain_text",
				"text": "Event Time",
				"emoji": True
			}
		},
        {
			"type": "input",
            "block_id": "edit_event_q_select",
			"element": user_select_element,
			"label": {
				"type": "plain_text",
				"text": "Q",
				"emoji": True
			}
		},
        {
            "type": "input",
            "block_id": "edit_event_special_select",
            "element": {
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Special event?",
                    "emoji": True   
                },
                "options": special_options,
                "initial_option": initial_special,
                "action_id": "edit_event_special_select"
            },
            "label": {
                "type": "plain_text",
                "text": "Special Event Qualifier",
                "emoji": True
            }  
        }
    ]

    # Sumbit / Cancel buttons
    action_button = {
        "type":"actions",
        "elements":[
            {
                "type":"button",
                "text":{
                    "type":"plain_text",
                    "text":"Submit",
                    "emoji":True
                },
                "action_id":"submit_edit_event_button",
                "style":"primary",
                "value":ao_channel_id
            }
        ]    
    }
    cancel_button = {
        "type":"actions",
        "elements":[
            {
                "type":"button",
                "text":{
                    "type":"plain_text",
                    "text":"Cancel",
                    "emoji":True
                },
                "action_id":"cancel_button_select",
                "style":"danger",
                "value":"Cancel"
            }
        ]    
    }
    blocks.append(action_button)
    blocks.append(cancel_button)

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


# triggered when user hits submit on event edit
@app.action("submit_edit_event_button")
def handle_submit_edit_event_button(ack, client, body, logger, context):
    # acknowledge action and log payload
    ack()
    logger.info(body)
    user_id = context['user_id']
    team_id = context['team_id']

    # gather inputs
    original_info = body['view']['blocks'][0]['text']['text']
    ignore, event, q_name = original_info.split('\n')
    original_date, original_time, original_ao_name = event.split(' @ ')
    original_channel_id = body['actions'][0]['value']

    results = body['view']['state']['values']
    selected_date = results['edit_event_datepicker']['edit_event_datepicker']['selected_date']
    selected_time = results['edit_event_timepicker']['edit_event_timepicker']['selected_time'].replace(':','')
    selected_q_id = results['edit_event_q_select']['edit_event_q_select']['selected_users'][0]
    selected_special = results['edit_event_special_select']['edit_event_special_select']['selected_option']['text']['text']
    if selected_special == 'None':
        selected_special_fmt = 'NULL'
    else:
        selected_special_fmt = f'"{selected_special}"'
    user_info_dict = client.users_info(user=selected_q_id)
    selected_q_name = safeget(user_info_dict, 'user', 'profile', 'display_name') or safeget(
            user_info_dict, 'user', 'profile', 'real_name') or None

    # Attempt db update
    success_status = False
    try:
        with my_connect(team_id) as mydb:
            sql_update = \
            f'''
            UPDATE {mydb.db}.schedule_master 
            SET q_pax_id = "{selected_q_id}"
                , q_pax_name = "{selected_q_name}"
                , event_date = DATE("{selected_date}")
                , event_time = "{selected_time}"
                , event_special = {selected_special_fmt}
            WHERE ao_channel_id = "{original_channel_id}"
                AND event_date = DATE("{original_date}")
                AND event_time = "{original_time}"
            ;
            '''
            logging.info(f'Attempting SQL UPDATE: {sql_update}')

            mycursor = mydb.conn.cursor()
            mycursor.execute(sql_update)
            mycursor.execute("COMMIT;")
            success_status = True
    except Exception as e:
        logger.error(f"Error updating schedule: {e}")
        error_msg = e

    # Generate top message and go back home
    if success_status:
        top_message = f"Got it! I've edited this slot with the following values: {selected_date} @ {selected_time} @ {original_ao_name} - Q: {selected_q_name} - Special: {selected_special}."
        # TODO: if selected date was in weinke range (current or next week), update local weinke png
    else:
        top_message = f"Sorry, there was an error of some sort; please try again or contact your local administrator / Weasel Shaker. Error:\n{error_msg}"
    
    refresh_home_tab(client, user_id, logger, top_message, team_id)

# triggered when user hits cancel or some other button that takes them home
@app.action("clear_slot_button")
def handle_clear_slot_button(ack, client, body, logger, context):
    # acknowledge action and log payload
    ack()
    logger.info(body)
    user_id = context['user_id']
    team_id = context['team_id']
    user_name = (get_user_names([user_id], logger, client))[0]

    # gather and format selected date and time
    selected_list = str.split(body['actions'][0]['value'],'|')
    selected_date = selected_list[0]
    selected_date_dt = datetime.strptime(selected_date, '%Y-%m-%d %H:%M:%S')
    selected_date_db = datetime.date(selected_date_dt).strftime('%Y-%m-%d')
    selected_time_db = datetime.time(selected_date_dt).strftime('%H%M')

    # gather info needed for message and SQL
    ao_display_name = selected_list[1]
    
    try:
        with my_connect(team_id) as mydb:
            sql_channel_pull = f'SELECT channel_id FROM {mydb.db}.aos WHERE ao_display_name = "{ao_display_name}";'
            ao_channel_id = pd.read_sql_query(sql_channel_pull, mydb.conn).iloc[0,0]
    except Exception as e:
        logger.error(f"Error pulling channel id: {e}")
    
    # Attempt db update
    success_status = False
    try:
        with my_connect(team_id) as mydb:
            sql_update = \
            f"""
            UPDATE {mydb.db}.schedule_master 
            SET q_pax_id = NULL
                , q_pax_name = NULL
            WHERE ao_channel_id = '{ao_channel_id}'
                AND event_date = DATE('{selected_date_db}')
                AND event_time = '{selected_time_db}'
            ;
            """
            logging.info(f'Attempting SQL UPDATE: {sql_update}')

            mycursor = mydb.conn.cursor()
            mycursor.execute(sql_update)
            mycursor.execute("COMMIT;")
            success_status = True
    except Exception as e:
        logger.error(f"Error updating schedule: {e}")
        error_msg = e

    # Generate top message and go back home
    if success_status:
        top_message = f"Got it, {user_name}! I have cleared the Q slot at *{ao_display_name}* on *{selected_date_dt.strftime('%A, %B %-d @ %H%M')}*"
        # TODO: if selected date was in weinke range (current or next week), update local weinke png
    else:
        top_message = f"Sorry, there was an error of some sort; please try again or contact your local administrator / Weasel Shaker. Error:\n{error_msg}"
    
    refresh_home_tab(client, user_id, logger, top_message, team_id)

# triggered when user hits cancel or some other button that takes them home
@app.action("cancel_button_select")
def cancel_button_select(ack, client, body, logger, context):
    # acknowledge action and log payload
    ack()
    logger.info(body)
    user_id = context['user_id']
    team_id = context['team_id']
    user_name = (get_user_names([user_id], logger, client))[0]
    top_message = f"Welcome to QSignups, {user_name}!"
    refresh_home_tab(client, user_id, logger, top_message, team_id)





SlackRequestHandler.clear_all_log_handlers()
logging.basicConfig(format="%(asctime)s %(message)s", level=logging.DEBUG)


def handler(event, context):
    print(f'Original event: {event}')
    print(f'Original context: {context}')
    # parsed_event = json.loads(event['body'])
    # team_id = parsed_event['team_id']
    # print(f'Team ID: {team_id}')
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)


# # -- OAuth flow -- #
# export SLACK_SIGNING_SECRET=***
# export SLACK_BOT_TOKEN=xoxb-***
# export SLACK_CLIENT_ID=111.111
# export SLACK_CLIENT_SECRET=***
# export SLACK_SCOPES=app_mentions:read,chat:write

# AWS IAM Role: bolt_python_s3_storage
#   - AmazonS3FullAccess
#   - AWSLambdaBasicExecutionRole

# rm -rf latest_slack_bolt && cp -pr ../../src latest_slack_bolt
# pip install python-lambda
# lambda deploy --config-file aws_lambda_oauth_config.yaml --requirements requirements_oauth.txt
