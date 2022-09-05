from imp import reload
import logging
import json
import os
from time import strftime, strptime
import mysql.connector
from contextlib import ContextDecorator
from datetime import datetime, timezone, timedelta, date
import pandas as pd

from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from slack_bolt.adapter.aws_lambda.lambda_s3_oauth_flow import LambdaS3OAuthFlow
# import re

def get_oauth_flow():
    if os.environ.get("SLACK_BOT_TOKEN"):
        return None
    else:
        return LambdaS3OAuthFlow()

# process_before_response must be True when running on FaaS
app = App(
  process_before_response=True,
  oauth_flow=get_oauth_flow(),
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
            passwd=os.environ['ADMIN_DATABASE_PASSWORD'],
            database=os.environ['ADMIN_DATABASE_SCHEMA']
        )

        # sql_select = f'SELECT schema_name, user, password FROM paxminer.regions WHERE team_id = {self.team_id};'

        # with self.conn.cursor() as mycursor:
        #     mycursor.execute(sql_select)
        #     db, user, password = mycursor.fetchone()
        db = os.environ['ADMIN_DATABASE_SCHEMA']

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

def refresh_home_tab(client, user_id, logger, top_message, team_id, context):
    print("CLIENT", client)
    print("CONTEXT", context)
    print("TEAM", team_id)
    sMsg = ""
    current_week_weinke_url = None
    ao_list = None
    upcoming_qs_df = pd.DataFrame()
    try:
        with my_connect(team_id) as mydb:
            mycursor = mydb.conn.cursor()
            # Build SQL queries
            # list of upcoming Qs for user
            sql_upcoming_qs = f"""
            SELECT m.*, a.ao_display_name
            FROM {mydb.db}.qsignups_master m
            LEFT JOIN {mydb.db}.qsignups_aos a
            ON m.team_id = a.team_id
                AND m.ao_channel_id = a.ao_channel_id
            WHERE m.team_id = "{team_id}"
                AND m.q_pax_id = "{user_id}"
                AND m.event_date > DATE("{date.today()}")
            ORDER BY m.event_date, m.event_time
            LIMIT 5;
            """

            # list of all upcoming events for the region
            sql_upcoming_events = f"""
            SELECT m.*, a.ao_display_name, a.ao_location_subtitle
            FROM qsignups_master m
            LEFT JOIN qsignups_aos a
            ON m.team_id = a.team_id
                AND m.ao_channel_id = a.ao_channel_id
            WHERE m.team_id = "{team_id}"
                AND m.event_date > DATE("{date.today()}")
                AND m.event_date <= DATE("{date.today()+timedelta(days=7)}")
            ORDER BY m.event_date, m.event_time
            ;
            """

            # list of AOs for dropdown
            sql_ao_list = f"SELECT * FROM {mydb.db}.qsignups_aos WHERE team_id = '{team_id}' ORDER BY REPLACE(ao_display_name, 'The ', '');"

            # weinke urls
            # sql_weinkes = f"SELECT current_week_weinke, next_week_weinke FROM paxminer.regions WHERE region_schema = '{mydb.db}';"
            # TODO: fix this
            sql_weinkes = f"SELECT current_week_weinke, next_week_weinke, bot_token FROM {mydb.db}.qsignups_regions WHERE team_id = '{team_id}';"

            # Make pulls
            upcoming_qs_df = pd.read_sql(sql_upcoming_qs, mydb.conn, parse_dates=['event_date'])
            ao_list = pd.read_sql(sql_ao_list, mydb.conn)
            upcoming_events_df = pd.read_sql(sql_upcoming_events, mydb.conn, parse_dates=['event_date'])

            current_week_weinke_url = None
            if os.environ['USE_WEINKES']:
                mycursor.execute(sql_weinkes)
                weinkes_list = mycursor.fetchone()

                if weinkes_list is None:
                    # team_id not on region table, so we insert it
                    sql_insert = f"""
                    INSERT INTO {mydb.db}.qsignups_regions (team_id, bot_token)
                    VALUES ("{team_id}", "{context['bot_token']}");
                    """
                    mycursor.execute(sql_insert)
                    mycursor.execute("COMMIT;")

                    current_week_weinke_url = None
                    next_week_weinke_url = None
                else:
                    current_week_weinke_url = weinkes_list[0]
                    next_week_weinke_url = weinkes_list[1]

                if weinkes_list[2] != context['bot_token']:
                    sql_update = f"UPDATE {mydb.db}.qsignups_regions SET bot_token = '{context['bot_token']}' WHERE team_id = '{team_id}';"
                    mycursor.execute(sql_update)
                    mycursor.execute("COMMIT;")

            # Create upcoming schedule message
            sMsg = '*Upcoming Schedule:*'
            iterate_date = ''
            for index, row in upcoming_events_df.iterrows():
                if row['event_date'] != iterate_date:
                    sMsg += f"\n\n:calendar: *{row['event_date'].strftime('%A %m/%d/%y')}*"
                    iterate_date = row['event_date']

                if row['q_pax_name'] is None:
                    q_name = '*OPEN!*'
                else:
                    q_name = row['q_pax_name']

                location = row['ao_location_subtitle'].split('\n')[0]
                sMsg += f"\n{row['ao_display_name']} - {row['event_type']} @ {row['event_time']} - {q_name}"

    except Exception as e:
        logger.error(f"Error pulling user db info: {e}")

    # Extend top message with upcoming qs list
    if len(upcoming_qs_df) > 0:
        top_message += '\n\nYou have some upcoming Qs:'
        for index, row in upcoming_qs_df.iterrows():
            dt_fmt = row['event_date'].strftime("%a %m-%d")
            top_message += f"\n- {row['event_type']} on {dt_fmt} @ {row['event_time']} at {row['ao_display_name']}"

    # Build AO options list
    options = []
    if ao_list is not None:
        for index, row in ao_list.iterrows():
            new_option = {
                "text": {
                    "type": "plain_text",
                    "text": row['ao_display_name']
                },
                "value": row['ao_channel_id']
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
    ]
    if len(options) == 0:
        new_block = {
            "type": "section",
            "block_id": "ao_select_block",
            "text": {
                "type": "mrkdwn",
                "text": "Please use the button below to add some AOs!"
            }
        }
    else:
        new_block = {
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
    blocks.append(new_block)

    if (os.environ['USE_WEINKES']) and (current_week_weinke_url != None) and (next_week_weinke_url != None):
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
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Weekly schedules updated hourly, and may not reflect the latest changes"
                    }
                ]
            },
            {
                "type": "divider"
            }
        ]

        for block in weinke_blocks:
            blocks.append(block)

    # add upcoming schedule text block
    if sMsg:
        upcoming_schedule_block = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": sMsg
            }
        }
        blocks.append(upcoming_schedule_block)

    # add page refresh button
    refresh_button = {
        "type":"actions",
        "elements":[
            {
                "type":"button",
                "text":{
                    "type":"plain_text",
                    "text":"Refresh Schedule",
                    "emoji":True
                },
                "action_id":"refresh_home"
            }
        ]
    }
    blocks.append(refresh_button)

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

@app.action("refresh_home")
def handle_refresh_home_button(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    team_id = context["team_id"]
    user_name = (get_user_names([user_id], logger, client))[0]
    top_message = f'Welcome to QSignups, {user_name}!'
    refresh_home_tab(client, user_id, logger, top_message, team_id, context)

@app.event("app_mention")
def handle_app_mentions(body, say, logger):
    logger.info(f'INFO: {body}')
    say("Looking for me? Click on my icon to go to the app and sign up to Q!")

@app.command("/hello")
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
    refresh_home_tab(client, user_id, logger, top_message, team_id, context)


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
        "Edit an AO",
        # "Delete an AO",
        "Add an event",
        "Edit an event",
        "Delete a single event",
        "General settings"
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
    # 'Add an AO' selected
    elif selected_action == 'Edit an AO':
        logger.info('edit an ao')

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

        # # list of AOs for dropdown
        # try:
        #     with my_connect(team_id) as mydb:
        #         sql_ao_list = f"SELECT ao_display_name, ao_channel_id FROM {mydb.db}.qsignups_aos WHERE team_id = '{team_id}' ORDER BY REPLACE(ao_display_name, 'The ', '');"
        #         ao_list = pd.read_sql(sql_ao_list, mydb.conn)
        #         # ao_list = ao_list['ao_display_name'].values.tolist()
        # except Exception as e:
        #     logger.error(f"Error pulling AO list: {e}")

        # ao_options = []
        # for index, row in ao_list.iterrows():
        #     new_option = {
        #         "text": {
        #             "type": "plain_text",
        #             "text": row['ao_display_name'],
        #             "emoji": True
        #         },
        #         "value": row['ao_channel_id']
        #     }
        #     ao_options.append(new_option)

        # blocks = [
        #     {
        #         "type": "section",
        #         "text": {
        #             "type": "mrkdwn",
        #             "text": "*Select an AO channel:*"
		# 	    }
        #     },
        #     {
        #         "type": "actions",
        #         "block_id": "edit_ao_select",
        #         "elements": [{
        #             "type": "static_select",
        #             "placeholder": {
        #                 "type": "plain_text",
        #                 "text": "Select an AO to edit",
        #                 "emoji": True
        #             },
        #             "options": ao_options,
        #             "action_id": "edit_ao_select"
        #         }]
        #     },
        #     {
        #         "type": "input",
        #         "block_id": "ao_display_name",
        #         "element": {
        #             "type": "plain_text_input",
        #             "action_id": "ao_display_name",
        #             "placeholder": {
        #                 "type": "plain_text",
        #                 "text": "Weasel's Ridge"
        #             }
        #         },
        #         "label": {
        #             "type": "plain_text",
        #             "text": "AO Title"
        #         }
        #     },
        #     {
        #         "type": "input",
        #         "block_id": "ao_location_subtitle",
        #         "element": {
        #             "type": "plain_text_input",
        #             "multiline": True,
        #             "action_id": "ao_location_subtitle",
        #             "placeholder": {
        #                 "type": "plain_text",
        #                 "text": "Oompa Loompa Kingdom"
        #             }
        #         },
        #         "label": {
        #             "type": "plain_text",
        #             "text": "Location (township, park, etc.)"
        #         }
        #     }
        # ]

        # action_button = {
        #     "type":"actions",
        #     "elements":[
        #         {
        #             "type":"button",
        #             "text":{
        #                 "type":"plain_text",
        #                 "text":"Submit",
        #                 "emoji":True
        #             },
        #             "action_id":"submit_edit_ao_button",
        #             "style":"primary",
        #             "value":"Submit"
        #         }
        #     ]
        # }
        # cancel_button = {
        #     "type":"actions",
        #     "elements":[
        #         {
        #             "type":"button",
        #             "text":{
        #                 "type":"plain_text",
        #                 "text":"Cancel",
        #                 "emoji":True
        #             },
        #             "action_id":"cancel_button_select",
        #             "style":"danger",
        #             "value":"Cancel"
        #         }
        #     ]
        # }
        # blocks.append(action_button)
        # blocks.append(cancel_button)

        # try:
        #     print(blocks)
        #     client.views_publish(
        #         user_id=user_id,
        #         view={
        #             "type": "home",
        #             "blocks": blocks
        #         }
        #     )
        # except Exception as e:
        #     logger.error(f"Error publishing home tab: {e}")
        #     print(e)

    # Add an event
    elif selected_action == 'Add an event':
        logging.info('add an event')

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


    elif selected_action == 'Delete a single event':
        logging.info('Delete an event')

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

    # General settings
    elif selected_action == 'General settings':
        logger.info('setting general settings')

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
                    "action_id":"submit_general_settings",
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

@app.action("delete_single_event_ao_select")
def handle_delete_single_event_ao_select(ack, body, client, logger, context):
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
            FROM {mydb.db}.qsignups_master m
            INNER JOIN {mydb.db}.qsignups_aos a
            ON m.ao_channel_id = a.ao_channel_id
            WHERE a.team_id = "{team_id}"
                AND a.ao_channel_id = "{ao_channel_id}"
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
        "text": {"type": "mrkdwn", "text": "Please select a Q slot to delete for:"}
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

        action_id = "delete_single_event_button"
        value = date_fmt_value + '|' + row['ao_channel_id']
        confirm_obj = {
            "title": {
                "type": "plain_text",
                "text": "Delete this event?"
            },
            "text": {
                "type": "mrkdwn",
                "text": "Are you sure you want to delete this event? This cannot be undone."
            },
            "confirm": {
                "type": "plain_text",
                "text": "Yes, delete it"
            },
            "deny": {
                "type": "plain_text",
                "text": "Cancel"
            }
        }

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
                    "value":value,
                    "confirm":confirm_obj
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

@app.action("delete_single_event_button")
def delete_single_event_button(ack, client, body, context):
    # acknowledge action and log payload
    ack()
    logger.info(body)
    user_id = context['user_id']
    team_id = context['team_id']
    # user_name = (get_user_names([user_id], logger, client))[0]

    # gather and format selected date and time
    selected_list = str.split(body['actions'][0]['value'],'|')
    selected_date = selected_list[0]
    selected_ao_id = selected_list[1]
    selected_date_dt = datetime.strptime(selected_date, '%Y-%m-%d %H:%M:%S')
    selected_date_db = datetime.date(selected_date_dt).strftime('%Y-%m-%d')
    selected_time_db = datetime.time(selected_date_dt).strftime('%H%M')


    # attempt delete
    success_status = False
    try:
        with my_connect(team_id) as mydb:
            sql_delete = f"""
            DELETE FROM {mydb.db}.qsignups_master
            WHERE team_id = '{team_id}'
                AND ao_channel_id = '{selected_ao_id}'
                AND event_date = DATE('{selected_date_db}')
                AND event_time = '{selected_time_db}';
            """
            logger.info(f'Attempting SQL: \n{sql_delete}')
            mycursor = mydb.conn.cursor()
            mycursor.execute(sql_delete)
            mycursor.execute('COMMIT;')
            success_status = True
    except Exception as e:
        logger.error(f"Error pulling AO list: {e}")
        error_msg = e

    # Take the user back home
    if success_status:
        top_message = f"Success! Deleted event on {selected_date_db} at {selected_time_db}"
    else:
        top_message = f"Sorry, there was a problem of some sort; please try again or contact your local administrator / Weasel Shaker. Error:\n{error_msg}"

    refresh_home_tab(client, user_id, logger, top_message, team_id, context)

@app.action("edit_ao_select")
def handle_edit_ao_select(ack, body, client, logger, context):
    ack()
    logger.info(body)
    print(body)
    user_id = context["user_id"]
    team_id = context["team_id"]

    selected_channel = body['view']['state']['values']['edit_ao_select']['edit_ao_select']['selected_option']['value']
    selected_channel_name = body['view']['state']['values']['edit_ao_select']['edit_ao_select']['selected_option']['text']['text']

    # pull existing info for this channel
    try:
        with my_connect(team_id) as mydb:
            sql_pull = f"""
            SELECT ao_display_name, ao_location_subtitle
            FROM {mydb.db}.qsignups_aos
            WHERE team_id = '{team_id}'
                AND ao_channel_id = '{selected_channel}';
            """
            mycursor = mydb.conn.cursor()
            mycursor.execute(sql_pull)
            results = mycursor.fetchone()
            if results is None:
                results = (None, None)
            ao_display_name, ao_location_subtitle = results

            sql_ao_list = f"SELECT ao_display_name, ao_channel_id FROM {mydb.db}.qsignups_aos WHERE team_id = '{team_id}' ORDER BY REPLACE(ao_display_name, 'The ', '');"
            ao_list = pd.read_sql(sql_ao_list, mydb.conn)
    except Exception as e:
        logger.error(f"Error pulling AO list: {e}")

    if results is None:
        refresh_home_tab(client, user_id, logger, top_message="Selected channel not found - PAXMiner may not have added it to the aos table yet", team_id=team_id, context=context)
    else:
        if ao_display_name is None:
            ao_display_name = ""
        if ao_location_subtitle is None:
            ao_location_subtitle = ""

        # rebuild blocks
        ao_options = []
        for index, row in ao_list.iterrows():
            new_option = {
                "text": {
                    "type": "plain_text",
                    "text": row['ao_display_name'],
                    "emoji": True
                },
                "value": row['ao_channel_id']
            }
            ao_options.append(new_option)

        blocks = [
            {
                "type": "section",
                "block_id": "page_label",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Edit AO:*\n*{selected_channel_name}*\n{selected_channel}"
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
                    },
                    "initial_value": ao_display_name
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
                    },
                    "initial_value": ao_location_subtitle
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
                    "action_id":"submit_edit_ao_button",
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

@app.action("add_event_recurring_select_action")
def handle_add_event_recurring_select_action(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    team_id = context["team_id"]
    recurring_select_option = body['view']['state']['values']['recurring_select_block']['add_event_recurring_select_action']['selected_option']
    recurring_select = recurring_select_option['value']

    logger.info('add an event - switch recurring type')

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

    event_type_list = ['Beatdown', 'QSource', 'Custom']
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
                    "initial_option": recurring_select_option
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
        }
    ]

    if recurring_select == 'recurring':
        new_blocks = [
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
                    "initial_time": "06:10",
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

        new_blocks = [
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
                    "initial_time": "06:10",
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
        ]

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
            FROM {mydb.db}.qsignups_master m
            INNER JOIN {mydb.db}.qsignups_aos a
            ON m.team_id = a.team_id
                AND m.ao_channel_id = a.ao_channel_id
            WHERE a.team_id = "{team_id}"
                AND a.ao_channel_id = "{ao_channel_id}"
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
                        "text":f"{row['event_type']} {date_fmt}: {date_status}",
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

@app.action("submit_edit_ao_button")
def submit_edit_ao_button(ack, body, client, logger, context):
    ack()
    logger.info(body)
    print(body)
    user_id = context["user_id"]
    team_id = context["team_id"]

    page_label = body['view']['blocks'][0]['text']['text']
    label, ao_display_name, ao_channel_id = page_label.replace('*','').split('\n')

    input_data = body['view']['state']['values']
    ao_display_name = input_data['ao_display_name']['ao_display_name']['value']
    ao_location_subtitle = input_data['ao_location_subtitle']['ao_location_subtitle']['value']

    # Update AO table
    success_status = False
    try:
        with my_connect(team_id) as mydb:

            sql_update = f"""
            UPDATE {mydb.db}.qsignups_aos
            SET ao_display_name = "{ao_display_name}",
                ao_location_subtitle = "{ao_location_subtitle}"
            WHERE ao_channel_id = "{ao_channel_id}"
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
        top_message = f"Success! Edited info for {ao_display_name}"
    else:
        top_message = f"Sorry, there was a problem of some sort; please try again or contact your local administrator / Weasel Shaker. Error:\n{error_msg}"

    refresh_home_tab(client, user_id, logger, top_message, team_id, context)

def safe_get(data, keys):
    try:
        result = data
        for k in keys:
            result = result[k]
        return result
    except:
        return None
@app.action("submit_general_settings")
def handle_submit_general_settings_button(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    team_id = context["team_id"]

    # Gather inputs from form
    input_data = body['view']['state']['values']

    query_params = {
        'team_id': team_id
    }

    query_params['weekly_weinke_channel'] = safe_get(input_data, ['weinke_channel_select','weinke_channel_select','selected_channel'])
    query_params['signup_reminders'] = safe_get(input_data, ['q_reminder_enable','q_reminder_enable','selected_option','value']) == "enable"
    query_params['weekly_ao_reminders'] = safe_get(input_data, ['ao_reminder_enable','ao_reminder_enable','selected_option','value']) == "enable"
    query_params['google_calendar_id'] = safe_get(input_data, ['google_calendar_id','google_calendar_id','value'])

    print("FOUND GPARAMS ", query_params)

    # Update db
    success_status = False
    try:
        with my_connect(team_id) as mydb:

            sql_update = f"""
            UPDATE {mydb.db}.qsignups_regions
            SET weekly_weinke_channel = IFNULL(%(weekly_weinke_channel)s, weekly_weinke_channel),
                signup_reminders = IFNULL(%(signup_reminders)s, signup_reminders),
                weekly_ao_reminders = IFNULL(%(weekly_ao_reminders)s, weekly_ao_reminders),
                google_calendar_id = IFNULL(%(google_calendar_id)s, google_calendar_id)
            WHERE team_id = %(team_id)s;
            """
            print("SQL: ", sql_update)

            mycursor = mydb.conn.cursor()
            mycursor.execute(sql_update, query_params)
            mycursor.execute("COMMIT;")
            success_status = True
    except Exception as e:
        logger.error(f"Error writing to db: {e}")
        error_msg = e

    # Take the user back home
    if success_status:
        top_message = f"Success! Changed general region settings"
    else:
        top_message = f"Sorry, there was a problem of some sort; please try again or contact your local administrator / Weasel Shaker. Error:\n{error_msg}"

    refresh_home_tab(client, user_id, logger, top_message, team_id, context)


@app.action("submit_add_ao_button")
def handle_submit_add_ao_button(ack, body, client, logger, context):
    ack()
    logger.info(body)
    print(body)
    user_id = context["user_id"]
    team_id = context["team_id"]

    # Gather inputs from form
    input_data = body['view']['state']['values']
    ao_channel_id = input_data['add_ao_channel_select']['add_ao_channel_select']['selected_channel']
    ao_display_name = input_data['ao_display_name']['ao_display_name']['value']
    ao_location_subtitle = input_data['ao_location_subtitle']['ao_location_subtitle']['value']
    # qsignups_enabled = input_data['qsignups_enabled_select']['qsignups_enabled_select']['selected_option']['value']

    # if qsignups_enabled == 'Yes':
    #     qsignups_enabled = 1
    # else:
    #     qsignups_enabled = 0

    # replace double quotes with single quotes
    ao_display_name = ao_display_name.replace('"',"'")
    ao_location_subtitle = ao_location_subtitle.replace('"',"'")

    # Write to AO table
    success_status = False
    try:
        with my_connect(team_id) as mydb:
            # find out if ao is already on table
            sql_pull = f"SELECT * FROM {mydb.db}.qsignups_aos WHERE team_id = '{team_id}' and ao_channel_id = '{ao_channel_id}'"
            mycursor = mydb.conn.cursor()
            mycursor.execute(sql_pull)
            result = mycursor.fetchall()
            sql_update = f"""
                INSERT INTO {mydb.db}.qsignups_aos (ao_channel_id, ao_display_name, ao_location_subtitle, team_id)
                VALUES ("{ao_channel_id}", "{ao_display_name}", "{ao_location_subtitle}", "{team_id}");
                """
            # if len(result) == 0:
            #     sql_update = f"""
            #     INSERT INTO {mydb.db}.qsignups_aos (ao_channel_id, ao_display_name, ao_location_subtitle, team_id)
            #     VALUES ("{ao_channel_id}", "{ao_display_name}", "{ao_location_subtitle}", "{team_id}");
            #     """
            # else:
            #     # TODO: fix this
            #     sql_update = f"""
            #     UPDATE {mydb.db}.qsignups_aos
            #     SET ao_display_name = "{ao_display_name}",
            #         ao_location_subtitle = "{ao_location_subtitle}"
            #     WHERE ao_channel_id = "{ao_channel_id}"
            #     ;
            #     """
            logger.info(f"Attempting SQL INSERT / UPDATE: {sql_update}")

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

    refresh_home_tab(client, user_id, logger, top_message, team_id, context)

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
    event_time = input_data['event_start_time_select']['event_start_time_select']['selected_time'].replace(':','')
    event_end_time = input_data['event_end_time_select']['event_end_time_select']['selected_time'].replace(':','')

    # Logic for custom events
    if input_data['event_type_select']['event_type_select_action']['selected_option']['value'] == 'Custom':
        event_type = input_data['event_type_custom']['event_type_custom']['value']
    else:
        event_type = input_data['event_type_select']['event_type_select_action']['selected_option']['value']

    event_recurring = True

    # Grab channel id
    try:
        with my_connect(team_id) as mydb:
            mycursor = mydb.conn.cursor()
            mycursor.execute(f'SELECT ao_channel_id FROM {mydb.db}.qsignups_aos WHERE team_id = "{team_id}" AND ao_display_name = "{ao_display_name}";')
            ao_channel_id = mycursor.fetchone()[0]
    except Exception as e:
           logger.error(f"Error pulling from db: {e}")

    # Write to weekly table
    try:
        with my_connect(team_id) as mydb:
            sql_insert = f"""
            INSERT INTO {mydb.db}.qsignups_weekly (ao_channel_id, event_day_of_week, event_time, event_end_time, event_type, team_id)
            VALUES ("{ao_channel_id}", "{event_day_of_week}", "{event_time}", "{event_end_time}", "{event_type}", "{team_id}");
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
                    INSERT INTO {mydb.db}.qsignups_master (ao_channel_id, event_date, event_time, event_end_time, event_day_of_week, event_type, event_recurring, team_id)
                    VALUES ("{ao_channel_id}", DATE("{iterate_date}"), "{event_time}", "{event_end_time}", "{event_day_of_week}", "{event_type}", {event_recurring}, "{team_id}")
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
    refresh_home_tab(client, user_id, logger, top_message, team_id, context)

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
    event_time = input_data['event_start_time_select']['event_start_time_select']['selected_time'].replace(':','')
    event_end_time = input_data['event_end_time_select']['event_end_time_select']['selected_time'].replace(':','')

    # Logic for custom events
    if input_data['event_type_select']['event_type_select_action']['selected_option']['value'] == 'Custom':
        event_type = input_data['event_type_custom']['event_type_custom']['value']
    else:
        event_type = input_data['event_type_select']['event_type_select_action']['selected_option']['value']

    event_recurring = False

    # Grab channel id
    try:
        with my_connect(team_id) as mydb:
            mycursor = mydb.conn.cursor()
            mycursor.execute(f'SELECT ao_channel_id FROM {mydb.db}.qsignups_aos WHERE team_id = "{team_id}" AND ao_display_name = "{ao_display_name}";')
            ao_channel_id = mycursor.fetchone()[0]
    except Exception as e:
           logger.error(f"Error pulling from db: {e}")

    # Write to master schedule table
    logger.info(f"Attempting SQL INSERT into schedule_master")
    success_status = False
    try:
        with my_connect(team_id) as mydb:
            mycursor = mydb.conn.cursor()
            event_date_dt = datetime.strptime(event_date, '%Y-%m-%d').date()
            sql_insert = f"""
            INSERT INTO {mydb.db}.qsignups_master (ao_channel_id, event_date, event_time, event_end_time, event_day_of_week, event_type, event_recurring, team_id)
            VALUES ("{ao_channel_id}", DATE("{event_date}"), "{event_time}", "{event_end_time}", "{event_date_dt.strftime('%A')}", "{event_type}", {event_recurring}, "{team_id}")
            """

            mycursor.execute(sql_insert)
            mycursor.execute("COMMIT;")
            success_status = True

    except Exception as e:
           logger.error(f"Error writing to schedule_master: {e}")
           error_msg = e

    # Give status message and return to home
    if success_status:
        top_message = f"Thanks, I got it! I've added your event to the schedule for {event_date} at {event_time} at {ao_display_name}."
    else:
        top_message = f"Sorry, there was an error of some sort; please try again or contact your local administrator / Weasel Shaker. Error:\n{error_msg}"
    refresh_home_tab(client, user_id, logger, top_message, team_id, context)


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
            FROM {mydb.db}.qsignups_master
            WHERE team_id = '{team_id}'
                AND ao_channel_id = '{ao_channel_id}'
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
            button_text = "Take slot"
        # Otherwise default (grey) button, listing Qs name
        else:
            date_status = row['q_pax_name']
            date_style = "default"
            action_id = "taken_date_select_button"
            value = str(row['event_date_time']) + '|' + row['q_pax_name']
            button_text = "Edit Slot"

        # try:
        #     date_status_format = re.sub('\s\(([\s\S]*?\))','',date_status)
        #     print(f"formatted: {date_status_format}")
        # except Exception as e:
        #     print(e)

        # Button template
        new_section = {
            "type":"section",
            "text":{
                "type":"mrkdwn",
                "text":f"{row['event_type']} {date_fmt}: {date_status}"
            },
            "accessory":{
                "type":"button",
                "text":{
                    "type":"plain_text",
                    "text":button_text,
                    "emoji":True
                },
                "action_id":action_id,
                "value":value
            }
        }
        if date_style == "primary":
            new_section["accessory"]["style"] = "primary"

        # Append button to list
        blocks.append(new_section)

        # new_button = {
        #     "type":"actions",
        #     "elements":[
        #         {
        #             "type":"button",
        #             "text":{
        #                 "type":"plain_text",
        #                 "text":f"{row['event_type']} {date_fmt}: {date_status}",
        #                 "emoji":True
        #             },
        #             "action_id":action_id,
        #             "value":value
        #         }
        #     ]
        # }
        # if date_style == "primary":
        #     new_button['elements'][0]["style"] = "primary"

        # # Append button to list
        # blocks.append(new_button)

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
    logging.info(body)
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
            sql_channel_pull = f'SELECT ao_channel_id FROM {mydb.db}.qsignups_aos WHERE team_id = "{team_id}" and ao_display_name = "{ao_display_name}";'
            ao_channel_id = pd.read_sql_query(sql_channel_pull, mydb.conn).iloc[0,0]
    except Exception as e:
        logger.error(f"Error pulling channel id: {e}")

    # Attempt db update
    success_status = False
    try:
        with my_connect(team_id) as mydb:
            sql_update = \
            f"""
            UPDATE {mydb.db}.qsignups_master
            SET q_pax_id = '{user_id}'
                , q_pax_name = '{user_name}'
            WHERE team_id = '{team_id}'
                AND ao_channel_id = '{ao_channel_id}'
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

    refresh_home_tab(client, user_id, logger, top_message, team_id, context)

# triggered when user selects open slot on a message
@app.action("date_select_button_from_message")
def handle_date_select_button_from_message(ack, client, body, logger, context):
    # acknowledge action and log payload
    ack()
    logger.info(body)
    logging.info(body)
    user_id = context["user_id"]
    team_id = context["team_id"]
    user_name = (get_user_names([user_id], logger, client))[0]

    # gather and format selected date and time
    selected_date = body['actions'][0]['value']
    selected_date_dt = datetime.strptime(selected_date, '%Y-%m-%d %H:%M:%S')
    selected_date_db = datetime.date(selected_date_dt).strftime('%Y-%m-%d')
    selected_time_db = datetime.time(selected_date_dt).strftime('%H%M')

    # gather info needed for message and SQL
    ao_channel_id = body['channel']['id']
    message_ts = body['message']['ts']
    message_blocks = body['message']['blocks']

    try:
        with my_connect(team_id) as mydb:
            sql_channel_pull = f'SELECT ao_display_name FROM {mydb.db}.qsignups_aos WHERE team_id = "{team_id}" and ao_channel_id = "{ao_channel_id}";'
            ao_name = pd.read_sql_query(sql_channel_pull, mydb.conn).iloc[0,0]
    except Exception as e:
        logger.error(f"Error pulling channel id: {e}")

    # Attempt db update
    success_status = False
    try:
        with my_connect(team_id) as mydb:
            sql_update = \
            f"""
            UPDATE {mydb.db}.qsignups_master
            SET q_pax_id = '{user_id}'
                , q_pax_name = '{user_name}'
            WHERE team_id = '{team_id}'
                AND ao_channel_id = '{ao_channel_id}'
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

    # Update original message
    open_count = 0
    block_num = -1
    if success_status:
        for counter, block in enumerate(message_blocks):
            print(f"comparing {safeget(block, 'accessory', 'value')} and {selected_date}")
            if safeget(block, 'accessory', 'value') == selected_date:
                block_num = counter

            if safeget(block, 'accessory', 'text', 'text'):
                if block['accessory']['text']['text'][-5] == 'OPEN!':
                    open_count += 1

        print(block_num)
        if block_num >= 0:
            message_blocks[block_num]['text']['text'] = message_blocks[block_num]['text']['text'].replace('OPEN!', user_name)
            message_blocks[block_num]['accessory']['action_id'] = 'ignore_button'
            message_blocks[block_num]['accessory']['value'] = selected_date + '|' + user_name
            message_blocks[block_num]['accessory']['text']['text'] = user_name
            del(message_blocks[block_num]['accessory']['style'])

            # update top message
            open_count += -1
            if open_count == 1:
                open_msg = ' I see there is an open spot - who wants it?'
            elif open_count > 1:
                open_msg = ' I see there are some open spots - who wants them?'
            else:
                open_msg = ''

            message_blocks[0]['text']['text'] = f"Hello HIMs of {ao_name}! Here is your Q lineup for the week.{open_msg}"

            # publish update
            logging.info(f'sending blocks:\n{message_blocks}')
            client.chat_update(channel=ao_channel_id, ts=message_ts, blocks = message_blocks)

# triggered when user selects closed slot on a message
@app.action("ignore_button")
def handle_ignore_button(ack, client, body, logger, context):
    # acknowledge action and log payload
    ack()

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
            FROM {mydb.db}.qsignups_master m
            INNER JOIN {mydb.db}.qsignups_aos a
            ON m.team_id = a.team_id
                AND m.ao_channel_id = a.ao_channel_id
            WHERE a.team_id = "{team_id}"
                AND a.ao_display_name = "{ao_display_name}"
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
    selected_q_id_list = results['edit_event_q_select']['edit_event_q_select']['selected_users']
    if len(selected_q_id_list) == 0:
        selected_q_id_fmt = 'NULL'
        selected_q_name_fmt = 'NULL'
    else:
        selected_q_id = selected_q_id_list[0]
        user_info_dict = client.users_info(user=selected_q_id)
        selected_q_name = safeget(user_info_dict, 'user', 'profile', 'display_name') or safeget(
            user_info_dict, 'user', 'profile', 'real_name') or None

        selected_q_id_fmt = f'"{selected_q_id}"'
        selected_q_name_fmt = f'"{selected_q_name}"'
    selected_special = results['edit_event_special_select']['edit_event_special_select']['selected_option']['text']['text']
    if selected_special == 'None':
        selected_special_fmt = 'NULL'
    else:
        selected_special_fmt = f'"{selected_special}"'

    # Attempt db update
    success_status = False
    try:
        with my_connect(team_id) as mydb:
            sql_update = \
            f'''
            UPDATE {mydb.db}.qsignups_master
            SET q_pax_id = {selected_q_id_fmt}
                , q_pax_name = {selected_q_name_fmt}
                , event_date = DATE("{selected_date}")
                , event_time = "{selected_time}"
                , event_special = {selected_special_fmt}
            WHERE team_id = "{team_id}"
                AND ao_channel_id = "{original_channel_id}"
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
        top_message = f"Got it! I've edited this slot with the following values: {selected_date} @ {selected_time} @ {original_ao_name} - Q: {selected_q_name_fmt} - Special: {selected_special}."
        # TODO: if selected date was in weinke range (current or next week), update local weinke png
    else:
        top_message = f"Sorry, there was an error of some sort; please try again or contact your local administrator / Weasel Shaker. Error:\n{error_msg}"

    refresh_home_tab(client, user_id, logger, top_message, team_id, context)

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
            sql_channel_pull = f'SELECT ao_channel_id FROM {mydb.db}.qsignups_aos WHERE team_id = "{team_id}" AND ao_display_name = "{ao_display_name}";'
            ao_channel_id = pd.read_sql_query(sql_channel_pull, mydb.conn).iloc[0,0]
    except Exception as e:
        logger.error(f"Error pulling channel id: {e}")

    # Attempt db update
    success_status = False
    try:
        with my_connect(team_id) as mydb:
            sql_update = \
            f"""
            UPDATE {mydb.db}.qsignups_master
            SET q_pax_id = NULL
                , q_pax_name = NULL
            WHERE team_id = '{team_id}'
                AND ao_channel_id = '{ao_channel_id}'
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

    refresh_home_tab(client, user_id, logger, top_message, team_id, context)

# triggered when user hits cancel or some other button that takes them home
@app.action("cancel_button_select")
def cancel_button_select(ack, client, body, logger, context):
    # acknowledge action and log payload
    ack()
    # print('Logging body and context:')
    # logging.info(body)
    # logging.info(context)
    user_id = context['user_id']
    team_id = context['team_id']
    user_name = (get_user_names([user_id], logger, client))[0]
    top_message = f"Welcome to QSignups, {user_name}!"
    refresh_home_tab(client, user_id, logger, top_message, team_id, context)





SlackRequestHandler.clear_all_log_handlers()
logger = logging.getLogger()
logger.setLevel(level=logging.DEBUG)
# logging.basicConfig(format="%(asctime)s %(message)s", level=logging.DEBUG)


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

if __name__ == "__main__":
  app.start( port=int(os.environ.get("PORT", 3000)))
