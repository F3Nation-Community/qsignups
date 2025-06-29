from datetime import timedelta, date, datetime
import traceback
import pytz
from database import DbManager
from database.orm import AO, Region
from database.orm.views import vwMasterEvents
import constants
from slack import actions, forms, inputs
import google
# from google import authenticate
from utilities import User

def get_timezone_for_team(team_id: str) -> str:
    """
    Finds the timezone for a given Slack team_id.
    Connects to the DB, finds the matching region, and returns its timezone.
    Defaults to EST if not found.
    """
    try:
        with DbManager.get_session() as session:
            region = session.query(Region).filter(Region.team_id == team_id).first()
            if region and region.timezone:
                return region.timezone
    except Exception as e:
        # For now, we'll just fall back without explicit logging here.
        # In a real scenario, you'd want to log 'e' to understand why it failed.
        pass
    return "EST" # A sensible default if no region is found or an error occurs

def refresh(client, user: User, logger, top_message, team_id, context):
    sMsg = ""
    current_week_weinke_url = None
    ao_list = None

    upcoming_qs = []

    try:
        # list of AOs for dropdown
        ao_list = DbManager.find_records(AO, [
            AO.team_id == team_id
        ])
        ao_list.sort( key = lambda x: x.ao_display_name.replace('The ', ''))

        # Get the timezone *once* at the beginning of the function if it's used multiple times
        region_timezone_str = get_timezone_for_team(team_id)
        tz = pytz.timezone(region_timezone_str)
        now_in_region = datetime.now(tz=tz) # Use this variable for all time-based queries

        # Event pulls
        upcoming_qs = DbManager.find_records(vwMasterEvents, [
            vwMasterEvents.team_id == team_id,
            vwMasterEvents.q_pax_id == user.id,
            vwMasterEvents.event_date > now_in_region,
        ])
        upcoming_events = DbManager.find_records(vwMasterEvents, [
            vwMasterEvents.team_id == team_id,
            vwMasterEvents.event_date > now_in_region,
            vwMasterEvents.event_date <= date.today()+timedelta(days=7),
        ])

        current_week_weinke_url = None
        
        region_record = DbManager.get_record(Region, team_id)

        if region_record is None:
            # team_id not on region table, so we insert it
            region_record = DbManager.create_record(Region(
                team_id = team_id,
                bot_token = context['bot_token']
            ))
        else:
            current_week_weinke_url = region_record.current_week_weinke
            next_week_weinke_url = region_record.next_week_weinke

        if region_record.bot_token != context['bot_token']:
            DbManager.update_record(Region, team_id, {
                Region.bot_token: context['bot_token']
            })

        # Create upcoming schedule message
        sMsg = '*Upcoming Schedule:*'
        iterate_date = ''
        for event in upcoming_events:
            if event.event_date != iterate_date:
                sMsg += f"\n\n:calendar: *{event.event_date.strftime('%A %m/%d/%y')}*"
                iterate_date = event.event_date

            if event.q_pax_name is None:
                q_name = '*OPEN!*'
            else:
                q_name = event.q_pax_name
            sMsg += f"\n{event.ao_display_name} - {event.event_type} @ {event.event_time} - {q_name}"

        print(sMsg)

    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error pulling user db info: {e}")

    # Extend top message with upcoming qs list
    if len(upcoming_qs) > 0:
        top_message += '\n\nYou have some upcoming Qs:'
        for q in upcoming_qs:
            dt_fmt = q.event_date.strftime("%a %m-%d")
            top_message += f"\n- {q.event_type} on {dt_fmt} @ {q.event_time} at {q.ao_display_name}"

    # First, get the correct timezone using our new helper function
    region_timezone_str = get_timezone_for_team(team_id) # Use the team_id passed to build_home_tab
    tz = pytz.timezone(region_timezone_str)
    now_in_region = datetime.now(tz=tz)

    # Then, format the string using that timezone's information
    # The %Z will automatically use the correct abbreviation (EST, CST, PST, etc.)
    last_updated_str = now_in_region.strftime("%m/%d/%Y %I:%M %p %Z")

    # Build AO options list
    # Build view blocks
    refresh_button = forms.make_action_button_row([inputs.ActionButton("Refresh Screen", action = actions.REFRESH_ACTION)])
    refresh_context = {
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": "QSignups screen no longer updates automatically. Please use the refresh button to update the screen. Last updated: " + last_updated_str
            }
        ]
    }
    
    blocks = [
        forms.make_header_row(top_message),
        refresh_button,
        refresh_context,
        forms.make_divider(),
    ]
    if not ao_list:
        blocks.append(forms.make_header_row("Please use the button below to add some AOs!"))
    else:
        options = []
        for ao_row in ao_list:
            new_option = {
                "text": {
                    "type": "plain_text",
                    "text": ao_row.ao_display_name
                },
                "value": ao_row.ao_channel_id
            }
            options.append(new_option)

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

    if (current_week_weinke_url != None) and (next_week_weinke_url != None):
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
    
    # blocks.append({
    #     "type": "context",
    #     "elements": [
    #         {
    #             "type": "mrkdwn",
    #             "text": "Looking for the calendar view? Slack broke something and it's not working right now. We're working on it!"
    #         }
    #     ]
    # })

    # add upcoming schedule text block
    if sMsg:
        upcoming_schedule_block = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": sMsg[:3000]
            }
        }
        blocks.append(upcoming_schedule_block)

    # Optionally add admin button
    # user_info_dict = client.users_info(
    #     user=user.id
    # )
    # if user_info_dict['user']['is_admin']:
    button = forms.make_action_button_row([inputs.ActionButton("Manage Region Calendar", action = actions.MANAGE_SCHEDULE_ACTION)])
    blocks.append(button)
    blocks.append(forms.make_action_button_row([inputs.GENERAL_SETTINGS]))

    # if google.is_available(team_id):
    #     if authenticate.is_connected(team_id):
    #         blocks.append(forms.make_action_button_row([inputs.GOOGLE_DISCONNECT]))
    #     else:
    #         blocks.append(forms.make_action_button_row([inputs.GOOGLE_CONNECT]))

    # Attempt to publish view
    try:
        logger.debug(blocks)
        client.views_publish(
            user_id=user.id,
            view={
                "type": "home",
                "blocks":blocks
            }
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")
        traceback.print_exc()
