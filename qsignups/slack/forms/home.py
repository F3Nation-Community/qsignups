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

        # Event pulls
        upcoming_qs = DbManager.find_records(vwMasterEvents, [
            vwMasterEvents.team_id == team_id,
            vwMasterEvents.q_pax_id == user.id,
            vwMasterEvents.event_date > datetime.now(tz=pytz.timezone('US/Central'))
        ])
        upcoming_events = DbManager.find_records(vwMasterEvents, [
            vwMasterEvents.team_id == team_id,
            vwMasterEvents.event_date > datetime.now(tz=pytz.timezone('US/Central')),
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

    # Build AO options list
    # Build view blocks
    blocks = [
        forms.make_header_row(top_message),
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

    # add page refresh button
    refresh_button = forms.make_action_button_row([inputs.ActionButton("Refresh Schedule", action = actions.REFRESH_ACTION)])
    blocks.append(refresh_button)

    # Optionally add admin button
    user_info_dict = client.users_info(
        user=user.id
    )
    if user_info_dict['user']['is_admin']:
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
