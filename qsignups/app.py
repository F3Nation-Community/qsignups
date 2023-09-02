import logging
import os
from datetime import datetime, timedelta, date
import pytz

from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from slack_bolt.adapter.aws_lambda.lambda_s3_oauth_flow import LambdaS3OAuthFlow
from slack_bolt.oauth.oauth_settings import OAuthSettings

from utilities import safe_get, get_user
# from google import authenticate, commands

from database import DbManager
from database.orm import Region, AO, Master, helper
from database.orm.views import vwAOsSort, vwMasterEvents

from slack import forms
from slack.forms import ao, event, home, settings
from slack.handlers import settings as settings_handler, weekly as weekly_handler, master as master_handler, ao as ao_handler
from slack import actions, inputs

import constants

def get_oauth_flow():
    if constants.LOCAL_DEVELOPMENT:
        return None
    else:
        return LambdaS3OAuthFlow(
            oauth_state_bucket_name=os.environ[constants.SLACK_STATE_S3_BUCKET_NAME],
            installation_bucket_name=os.environ[constants.SLACK_INSTALLATION_S3_BUCKET_NAME],
            settings=OAuthSettings(
                client_id=os.environ[constants.SLACK_CLIENT_ID],
                client_secret=os.environ[constants.SLACK_CLIENT_SECRET],
                scopes=os.environ[constants.SLACK_SCOPES].split(","),
            ),
        )

# process_before_response must be True when running on FaaS
app = App(
  process_before_response=True,
  oauth_flow=get_oauth_flow(),
)

# Inputs
schedule_create_length_days = 365

@app.action(actions.REFRESH_ACTION)
def handle_refresh_home_button(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    team_id = context["team_id"]
    user = get_user(user_id, client)
    top_message = f'Welcome to QSignups, {user.name}!'
    home.refresh(client, user, logger, top_message, team_id, context)

@app.event("app_mention")
def handle_app_mentions(body, say, logger):
    logger.info(f'INFO: {body}')
    say("Looking for me? Click on my icon to go to the app and sign up to Q!")

@app.command("/hello")
def respond_to_slack_within_3_seconds(ack):
    # This method is for synchronous communication with the Slack API server
    ack("Thanks!")

# @app.command("/google")
# def connect_google_calendar(ack, respond, command):
#     # This method is for synchronous communication with the Slack API server
#     ack()
#     commands.execute_command(command["text"], command["team_id"], command, respond)

@app.command("/schedule")
def display_upcoming_schedule(ack):
    # This method is for synchronous communication with the Slack API server
    ack("To be implemented: Upcoming Schedule!")

@app.event("app_home_opened")
def update_home_tab(client, event, logger, context):
    logger.info(event)
    user_id = context["user_id"]
    team_id = context["team_id"]
    user = get_user(user_id, client)
    top_message = f'Welcome to QSignups, {user.name}!'
    home.refresh(client, user, logger, top_message, team_id, context)

# @app.action(inputs.GOOGLE_DISCONNECT.action)
# def handle_google_disconnect(ack, body, client, logger, context):
#     ack()
#     team_id = context["team_id"]
#     user_id = context["user_id"]
#     user = get_user(user_id, client)
#     result = authenticate.disconnect(team_id)
#     if result.success:
#         top_message = f'You have disconnected from Google!'
#         home.refresh(client, user, logger, top_message, team_id, context)
#     else:
#         top_message = f'Something went wrong trying to disconnect!'
#         home.refresh(client, user, logger, top_message, team_id, context)

# @app.action(inputs.GOOGLE_CONNECT.action)
# def handle_google_connect(ack, body, client, logger, context):
#     ack()
#     team_id = context["team_id"]
#     user_id = context["user_id"]
#     user = get_user(user_id, client)
#     result = authenticate.connect(team_id)
#     if result.success:
#         top_message = f'You have connected from Google!'
#         home.refresh(client, user, logger, top_message, team_id, context)
#     else:
#         top_message = f'Something went wrong trying to connect!'
#         home.refresh(client, user, logger, top_message, team_id, context)


# triggers when user chooses to schedule a q
# @app.action("schedule_q_button")
# def handle_take_q_button(ack, body, client, logger, context):
#     ack()
#     logger.info(body)
#     user_id = context["user_id"]
#     user = get_user(user_id, client)
#     team_id = context["team_id"]
#     home.refresh(client, user, logger)

# triggers when user chooses to manager the schedule
@app.action(actions.MANAGE_SCHEDULE_ACTION)
def handle_manager_schedule_button(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    team_id = context["team_id"]

    blocks = [
        forms.make_header_row("Choose an option to manage your AOs:"),
        forms.make_action_button_row([inputs.ADD_AO_FORM, inputs.EDIT_AO_FORM, inputs.DELETE_AO_FORM]),
        forms.make_header_row("Choose an option to manage your Recurring Events:"),
        forms.make_action_button_row([inputs.ADD_RECURRING_EVENT_FORM, inputs.EDIT_RECURRING_EVENT_FORM, inputs.DELETE_RECURRING_EVENT_FORM]),
        forms.make_header_row("Choose an option to manage your Single Events:"),
        forms.make_action_button_row([inputs.ADD_SINGLE_EVENT_FORM, inputs.EDIT_SINGLE_EVENT_FORM, inputs.DELETE_SINGLE_EVENT_FORM]),
        forms.make_header_row("Return to the Home Page:"),
        forms.make_action_button_row([inputs.CANCEL_BUTTON])
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


@app.action(inputs.ADD_AO_FORM.action)
def handle_add_ao_form(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    team_id = context["team_id"]
    ao.add_form(team_id, user_id, client, logger)

@app.action(inputs.EDIT_AO_FORM.action)
def handle_edit_ao_form(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    team_id = context["team_id"]
    ao.edit_form(team_id, user_id, client, logger)
    
@app.action(inputs.DELETE_AO_FORM.action)
def handle_delete_ao_form(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    team_id = context["team_id"]
    ao.delete_form(team_id, user_id, client, logger)

@app.action(inputs.ADD_SINGLE_EVENT_FORM.action)
def handle_add_event_form(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    team_id = context["team_id"]
    event.add_single_form(team_id, user_id, client, logger)

@app.action(inputs.EDIT_SINGLE_EVENT_FORM.action)
def handle_edit_event_form(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    team_id = context["team_id"]
    event.edit_single_form(team_id, user_id, client, logger)

@app.action(inputs.DELETE_SINGLE_EVENT_FORM.action)
def handle_delete_single_event_form(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    team_id = context["team_id"]
    event.delete_single_form(team_id, user_id, client, logger)

@app.action(inputs.ADD_RECURRING_EVENT_FORM.action)
def handle_add_event_form(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    team_id = context["team_id"]
    event.add_recurring_form(team_id, user_id, client, logger)

@app.action(inputs.EDIT_RECURRING_EVENT_FORM.action)
def handle_edit_event_form(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    team_id = context["team_id"]
    event.make_ao_section_selector(team_id, user_id, client, logger, label="Please select an AO to edit:", action=actions.EDIT_RECURRING_EVENT_AO_SELECT)
    
@app.action(actions.EDIT_RECURRING_EVENT_AO_SELECT)
def handle_edit_event_form(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    team_id = context["team_id"]
    input_data = body
    event.select_recurring_form_for_edit(team_id, user_id, client, logger, input_data)

@app.action(inputs.DELETE_RECURRING_EVENT_FORM.action)
def handle_delete_event_form(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    team_id = context["team_id"]
    event.make_ao_section_selector(team_id, user_id, client, logger, label="Please select an AO to edit:", action=actions.DELETE_RECURRING_EVENT_AO_SELECT)

@app.action(actions.DELETE_RECURRING_EVENT_AO_SELECT)
def handle_delete_single_event_form(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    team_id = context["team_id"]
    input_data = body
    event.select_recurring_form_for_delete(team_id, user_id, client, logger, input_data)

@app.action(inputs.GENERAL_SETTINGS.action)
def handle_general_settings_form(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    team_id = context["team_id"]
    settings.general_form(team_id, user_id, client, logger)

@app.action(actions.DELETE_RECURRING_SELECT_ACTION)
def handle_delete_recurring_select(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context['user_id']
    user = get_user(user_id, client)
    team_id = context['team_id']
    input_data = body['actions'][0]['value']
    response = weekly_handler.delete(client, user_id, team_id, logger, input_data)
    home.refresh(client, user, logger, response.message, team_id, context)

@app.action(actions.SELECT_SLOT_EDIT_RECURRING_EVENT_FORM)
def handle_edit_recurring_event_slot_select(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context['user_id']
    team_id = context['team_id']
    input_data = body['actions'][0]['value']
    event.edit_recurring_form(team_id, user_id, client, logger, input_data)

@app.action(actions.EDIT_RECURRING_EVENT_ACTION)
def handle_edit_recurring_event(ack, body, client, logger, context):
    ack()
    logger.info(body)
    print(body)
    user_id = context["user_id"]
    user = get_user(user_id, client)
    team_id = context["team_id"]
    input_data = body
    response = weekly_handler.edit(client, user_id, team_id, logger, input_data)
    home.refresh(client, user, logger, response.message, team_id, context)

@app.action("delete_single_event_ao_select")
def handle_delete_single_event_ao_select(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    team_id = context["team_id"]
    ao_display_name = body['actions'][0]['selected_option']['text']['text']
    ao_channel_id = body['actions'][0]['selected_option']['value']

    events = DbManager.find_records(vwMasterEvents, [
        vwMasterEvents.team_id == team_id,
        vwMasterEvents.ao_channel_id == ao_channel_id,
        vwMasterEvents.event_date > datetime.now(tz=pytz.timezone('US/Central')),
        vwMasterEvents.event_date <= date.today() + timedelta(weeks=12)
    ])

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

    for event in events:
        event_date_time = datetime.strptime(event.event_date.strftime('%Y-%m-%d') + ' ' + event.event_time, '%Y-%m-%d %H%M')
        date_fmt = event_date_time.strftime("%a, %m-%d @ %H%M")
        date_fmt_value = event_date_time.strftime('%Y-%m-%d %H:%M:%S')

        # Build buttons
        if event.q_pax_id is None:
            date_status = "OPEN!"
        else:
            date_status = event.q_pax_name

        action_id = "delete_single_event_button"
        value = date_fmt_value + '|' + event.ao_channel_id
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
        new_button = inputs.ActionButton(
            label = f"{date_fmt}: {date_status}", value = value, action = action_id, confirm = confirm_obj)
        # Append button to list
        blocks.append(forms.make_action_button_row([new_button]))

    blocks.append(forms.make_action_button_row([inputs.CANCEL_BUTTON]))

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
    user = get_user(user_id, client)
    team_id = context['team_id']
    input_data = body['actions'][0]['value']
    response = master_handler.delete(client, user_id, team_id, logger, input_data)
    home.refresh(client, user, logger, response.message, team_id, context)

@app.action("edit_ao_select")
def handle_edit_ao_select(ack, body, client, logger, context):
    ack()
    logger.info(body)
    print(body)
    user_id = context["user_id"]
    user = get_user(user_id, client)
    team_id = context["team_id"]

    selected_channel = body['view']['state']['values']['edit_ao_select']['edit_ao_select']['selected_option']['value']
    selected_channel_name = body['view']['state']['values']['edit_ao_select']['edit_ao_select']['selected_option']['text']['text']

    aos: list[vwAOsSort] = DbManager.find_records(vwAOsSort, [vwAOsSort.team_id == team_id])

    if selected_channel not in [ao.ao_channel_id for ao in aos]:
        home.refresh(client, user, logger, top_message="Selected channel not found - PAXMiner may not have added it to the aos table yet", team_id=team_id, context=context)
    else:
        ao_index = [ao.ao_channel_id for ao in aos].index(selected_channel)
        ao_display_name = aos[ao_index].ao_display_name or ""
        ao_location_subtitle = aos[ao_index].ao_location_subtitle or ""

        # rebuild blocks
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
        blocks.append(forms.make_action_button_row([
            inputs.make_submit_button(actions.EDIT_AO_ACTION),
            inputs.CANCEL_BUTTON
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
            
@app.action(actions.DELETE_AO_SELECT_ACTION)
def handle_delete_ao_select(ack, body, client, logger, context):
    ack()
    logger.info(body)
    print(body)
    user_id = context["user_id"]
    team_id = context["team_id"]
    
    blocks = [
        {
            "type": "section",
            "block_id": "page_label",
            "text": {
                "type": "mrkdwn",
                "text": f"Are you sure you want to delete this AO from QSignups? This will also delete all associated events."
            }
        },
        forms.make_action_button_row([
            inputs.make_submit_button(actions.DELETE_AO_ACTION),
            inputs.CANCEL_BUTTON
        ]),
    ]
    try:
        client.views_publish(
            user_id=user_id,
            view={
                "type": "home",
                "blocks": blocks,
                "private_metadata": body["actions"][0]["selected_option"]["value"]
            }
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")
        print(e)

@app.action(actions.EDIT_SINGLE_EVENT_AO_SELECT)
def handle_edit_event_ao_select(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    team_id = context["team_id"]
    ao_channel_id, ao_display_name = inputs.SECTION_SELECTOR.get_selected_value(input_data=body, text_too=True)

    events = DbManager.find_records(vwMasterEvents, [
        vwMasterEvents.team_id == team_id,
        vwMasterEvents.ao_channel_id == ao_channel_id,
        vwMasterEvents.event_date > datetime.now(tz=pytz.timezone('US/Central')),
        vwMasterEvents.event_date <= date.today() + timedelta(weeks=12)
    ])

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

    for event in events:
        event_date_time = datetime.strptime(event.event_date.strftime('%Y-%m-%d') + ' ' + event.event_time, '%Y-%m-%d %H%M')
        date_fmt = event_date_time.strftime("%a, %m-%d @ %H%M")
        date_fmt_value = event_date_time.strftime('%Y-%m-%d %H:%M:%S')

        # Build buttons
        if event.q_pax_id is None:
            date_status = "OPEN!"
        else:
            date_status = event.q_pax_name

        action_id = "edit_single_event_button"
        value = date_fmt_value + '|' + event.ao_display_name

        # Button template
        new_button = {
            "type":"actions",
            "elements":[
                {
                    "type":"button",
                    "text":{
                        "type":"plain_text",
                        "text":f"{event.event_type} {date_fmt}: {date_status}",
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
    blocks.append(forms.make_action_button_row([inputs.CANCEL_BUTTON]))

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

@app.action(actions.EDIT_AO_ACTION)
def submit_edit_ao_button(ack, body, client, logger, context):
    ack()
    logger.info(body)
    print(body)
    user_id = context["user_id"]
    user = get_user(user_id, client)
    team_id = context["team_id"]
    page_label = body['view']['blocks'][0]['text']['text']
    input_data = body['view']['state']['values']
    response = ao_handler.edit(client, user_id, team_id, logger, page_label, input_data)
    home.refresh(client, user, logger, response.message, team_id, context)

@app.action(actions.DELETE_AO_ACTION)
def submit_delete_ao_button(ack, body, client, logger, context):
    ack()
    logger.info(body)
    print(body)
    user_id = context["user_id"]
    team_id = context["team_id"]
    user = get_user(user_id, client)
    ao_channel_id = body['view']['private_metadata']
    response = ao_handler.delete(client, user_id, team_id, logger, ao_channel_id)
    home.refresh(client, user, logger, response.message, team_id, context)

@app.action(actions.EDIT_SETTINGS_ACTION)
def handle_submit_general_settings_button(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    user = get_user(user_id, client)
    team_id = context["team_id"]
    # Gather inputs from form
    input_data = body['view']['state']['values']
    response = settings_handler.update(client, user_id, team_id, logger, input_data)
    # Take the user back home
    if response.success:
        top_message = f"Success! Changed general region settings"
    else:
        top_message = f"Sorry, there was a problem of some sort; please try again or contact your local administrator / Weasel Shaker. Error:\n{response.message}"
    home.refresh(client, user, logger, top_message, team_id, context)

@app.action(actions.ADD_AO_ACTION)
def handle_submit_add_ao_button(ack, body, client, logger, context):
    ack()
    logger.info(body)
    print(body)
    user_id = context["user_id"]
    user = get_user(user_id, client)
    team_id = context["team_id"]
    input_data = body['view']['state']['values']
    response = ao_handler.insert(client, user_id, team_id, logger, input_data)
    home.refresh(client, user, logger, response.message, team_id, context)

@app.action(actions.ADD_RECURRING_EVENT_ACTION)
def handle_submit_add_recurring_event_button(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    user = get_user(user_id, client)
    team_id = context["team_id"]

    # Gather inputs from form
    input_data = body['view']['state']['values']
    response = weekly_handler.insert(client, user_id, team_id, logger, input_data)
    home.refresh(client, user, logger, response.message, team_id, context)

@app.action(actions.ADD_SINGLE_EVENT_ACTION)
def handle_submit_add_single_event_button(ack, body, client, logger, context):
    ack()
    logger.info(body)
    user_id = context["user_id"]
    user = get_user(user_id, client)
    team_id = context["team_id"]
    input_data = body['view']['state']['values']
    response = master_handler.insert(client, user_id, team_id, logger, input_data)
    home.refresh(client, user, logger, response.message, team_id, context)

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

    events = DbManager.find_records(Master, [
        Master.team_id == team_id,
        Master.ao_channel_id == ao_channel_id,
        Master.event_date > datetime.now(tz=pytz.timezone('US/Central')),
        Master.event_date <= date.today() + timedelta(weeks=12)
    ])

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

    for event in events:
        event_date_time = datetime.strptime(event.event_date.strftime('%Y-%m-%d') + ' ' + event.event_time, '%Y-%m-%d %H%M')
        date_fmt = event_date_time.strftime("%a, %m-%d @ %H%M")

        # If slot is empty, show green button with primary (green) style button
        if event.q_pax_id is None:
            date_status = "OPEN!"
            date_style = "primary"
            action_id = "date_select_button"
            value = str(event_date_time)
            button_text = "Take slot"
        # Otherwise default (grey) button, listing Qs name
        else:
            date_status = event.q_pax_name
            date_style = "default"
            action_id = "taken_date_select_button"
            value = str(event_date_time) + '|' + event.q_pax_name
            button_text = "Edit Slot"

        # Button template
        new_section = {
            "type":"section",
            "text":{
                "type":"mrkdwn",
                "text":f"{event.event_type} {date_fmt}: {date_status}"
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

    # Cancel button
    blocks.append(forms.make_action_button_row([inputs.CANCEL_BUTTON]))

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
    user = get_user(user_id, client)

    # gather and format selected date and time
    selected_date = body['actions'][0]['value']
    selected_dt = datetime.strptime(selected_date, '%Y-%m-%d %H:%M:%S')

    # gather info needed for message and SQL
    ao_display_name = body['view']['blocks'][1]['text']['text'].replace('*','')

    response = master_handler.assign_event_q(client, user, team_id, logger, selected_dt, ao_display_name = ao_display_name)

    # Generate top message and go back home
    if response.success:
        top_message = f"Got it, {user.name}! I have you down for the Q at *{ao_display_name}* on *{selected_dt.strftime('%A, %B %-d @ %H%M')}*"
        # TODO: if selected date was in weinke range (current or next week), update local weinke png
    elif not top_message:
        top_message = f"Sorry, there was an error of some sort; please try again or contact your local administrator / Weasel Shaker."

    home.refresh(client, user, logger, top_message, team_id, context)

# triggered when user selects open slot on a message
@app.action("date_select_button_from_message")
def handle_date_select_button_from_message(ack, client, body, logger, context):
    # acknowledge action and log payload
    ack()
    logger.info(body)
    user_id = context["user_id"]
    user = get_user(user_id, client)
    team_id = context["team_id"]
    input_data = body

    ao_channel_id = body['channel']['id']
    selected_date = input_data['actions'][0]['value']
    response = master_handler.assign_event_q(client, user, team_id, logger, selected_date, ao_channel_id = ao_channel_id)
    if response.success:

        # gather info needed for message and SQL
        message_ts = body['message']['ts']
        message_blocks = body['message']['blocks']
        message_ts = input_data['message']['ts']
        message_blocks = input_data['message']['blocks']

        # Update original message
        open_count = 0
        block_num = -1
        for counter, block in enumerate(message_blocks):
            print(f"comparing {safe_get(block, 'accessory', 'value')} and {selected_date}")
            if safe_get(block, 'accessory', 'value') == selected_date:
                block_num = counter

            if safe_get(block, 'accessory', 'text', 'text'):
                if block['accessory']['text']['text'][-5] == 'OPEN!':
                    open_count += 1

        print(block_num)
        if block_num >= 0:
            message_blocks[block_num]['text']['text'] = message_blocks[block_num]['text']['text'].replace('OPEN!', user.name)
            message_blocks[block_num]['accessory']['action_id'] = 'ignore_button'
            message_blocks[block_num]['accessory']['value'] = selected_date + '|' + user.name
            message_blocks[block_num]['accessory']['text']['text'] = user.name
            del(message_blocks[block_num]['accessory']['style'])

            # update top message
            open_count += -1
            if open_count == 1:
                open_msg = ' I see there is an open spot - who wants it?'
            elif open_count > 1:
                open_msg = ' I see there are some open spots - who wants them?'
            else:
                open_msg = ''

            message_blocks[0]['text']['text'] = f"Hello HIMs! Here is your Q lineup for the week.{open_msg}"

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
    user_name = safe_get(user_info_dict, 'user', 'profile', 'display_name') or \
                safe_get(user_info_dict, 'user', 'profile', 'real_name') or None
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
        blocks = [
            {
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
            forms.make_action_button_row([inputs.CANCEL_BUTTON])
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

    # gather and format selected date and time
    selected_list = str.split(body['actions'][0]['value'],'|')
    selected_date = selected_list[0]
    selected_date_dt = datetime.strptime(selected_date, '%Y-%m-%d %H:%M:%S')
    selected_date_db = datetime.date(selected_date_dt).strftime('%Y-%m-%d')
    selected_time_db = datetime.time(selected_date_dt).strftime('%H%M')

    # gather info needed for input form
    ao_display_name = selected_list[1]

    event = DbManager.find_records(vwMasterEvents, [
        vwMasterEvents.team_id == team_id,
        vwMasterEvents.ao_display_name == ao_display_name,
        vwMasterEvents.event_date == selected_date_dt.date(),
        vwMasterEvents.event_time == selected_time_db
    ])[0]

    q_pax_id = event.q_pax_id
    q_pax_name = event.q_pax_name
    event_special = event.event_special
    ao_channel_id = event.ao_channel_id

    # build special qualifier
    # TODO: have "other" / freeform option
    special_list = [
        'None',
        'The Forge',
        'VQ',
        'F3versary',
        'Birthday Q',
        'AO Launch',
        'IronPAX',
        'Convergence',
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
        
    if not event.event_end_time:
        end_time_default = datetime.strftime(selected_date_dt + timedelta(minutes=45), "%H%M")

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
            "block_id": "edit_event_end_timepicker",
			"element": {
				"type": "timepicker",
				"initial_time": datetime.strptime(event.event_end_time or end_time_default, '%H%M').strftime('%H:%M'),
				"placeholder": {
					"type": "plain_text",
					"text": "Select time",
					"emoji": True
				},
				"action_id": "edit_event_end_timepicker"
			},
			"label": {
				"type": "plain_text",
				"text": "Event End Time",
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
    submit_button = inputs.ActionButton(
        label = 'Submit', style = 'primary', value = ao_channel_id, action = actions.EDIT_EVENT_ACTION)
    blocks.append(forms.make_action_button_row([submit_button, inputs.CANCEL_BUTTON]))

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
@app.action(actions.EDIT_EVENT_ACTION)
def handle_submit_edit_event_button(ack, client, body, logger, context):
    # acknowledge action and log payload
    ack()
    logger.info(body)
    user = get_user(context['user_id'], client)
    team_id = context['team_id']
    response = master_handler.update_events(client, user, team_id, logger, body)
    home.refresh(client, user, logger, response.message, team_id, context)

# triggered when user hits cancel or some other button that takes them home
@app.action("clear_slot_button")
def handle_clear_slot_button(ack, client, body, logger, context):
    # acknowledge action and log payload
    ack()
    logger.info(body)
    user_id = context['user_id']
    user = get_user(user_id, client)
    team_id = context['team_id']
    input_data = body['actions'][0]['value']
    selected_list = str.split(input_data,'|')
    selected_date = datetime.strptime(selected_list[0], '%Y-%m-%d %H:%M:%S')

    # gather info needed for message and SQL
    ao_display_name = selected_list[1]

    response = master_handler.clear_event_q(client, user, team_id, logger, ao_display_name, selected_date)
    home.refresh(client, user, logger, response.message, team_id, context)

# triggered when user hits cancel or some other button that takes them home
@app.action(actions.CANCEL_BUTTON_ACTION)
def cancel_button_select(ack, client, body, logger, context):
    # acknowledge action and log payload
    ack()
    # print('Logging body and context:')
    # logging.info(body)
    # logging.info(context)
    user_id = context['user_id']
    team_id = context['team_id']
    user = get_user(user_id, client)
    top_message = f"Welcome to QSignups, {user.name}!"
    home.refresh(client, user, logger, top_message, team_id, context)


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
