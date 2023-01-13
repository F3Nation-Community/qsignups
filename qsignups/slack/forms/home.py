from datetime import timedelta, date, datetime
import pytz
import pandas as pd
from qsignups.database import my_connect, DbManager
from qsignups.database.orm import AO, Region
from qsignups import constants
from qsignups.slack import actions, forms, inputs
from qsignups import google
from qsignups.google import commands

def refresh(client, user_id, logger, top_message, team_id, context):
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
                AND m.event_date > DATE("{datetime.now(tz=pytz.timezone('US/Central')).strftime('%Y-%m-%d')}")
            ORDER BY m.event_date, m.event_time
            ;
            """

            # list of all upcoming events for the region
            sql_upcoming_events = f"""
            SELECT m.*, a.ao_display_name, a.ao_location_subtitle
            FROM qsignups_master m
            LEFT JOIN qsignups_aos a
            ON m.team_id = a.team_id
                AND m.ao_channel_id = a.ao_channel_id
            WHERE m.team_id = "{team_id}"
                AND m.event_date > DATE("{datetime.now(tz=pytz.timezone('US/Central')).strftime('%Y-%m-%d')}")
                AND m.event_date <= DATE("{date.today()+timedelta(days=7)}")
            ORDER BY m.event_date, m.event_time
            ;
            """

            # list of AOs for dropdown
            ao_list = DbManager.find_records(AO, [
                AO.team_id == team_id
            ])

            ao_list.sort( key = lambda x: x.ao_display_name.replace('The ', ''))

            # weinke urls
            # sql_weinkes = f"SELECT current_week_weinke, next_week_weinke FROM paxminer.regions WHERE region_schema = '{mydb.db}';"
            # TODO: fix this

            # Make pulls
            upcoming_qs_df = pd.read_sql(sql_upcoming_qs, mydb.conn, parse_dates=['event_date'])
            upcoming_events_df = pd.read_sql(sql_upcoming_events, mydb.conn, parse_dates=['event_date'])

            current_week_weinke_url = None
            if constants.use_weinkes():
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
            for _, row in upcoming_events_df.iterrows():
                if row['event_date'] != iterate_date:
                    sMsg += f"\n\n:calendar: *{row['event_date'].strftime('%A %m/%d/%y')}*"
                    iterate_date = row['event_date']

                if row['q_pax_name'] is None:
                    q_name = '*OPEN!*'
                else:
                    q_name = row['q_pax_name']
                sMsg += f"\n{row['ao_display_name']} - {row['event_type']} @ {row['event_time']} - {q_name}"

            print(sMsg)

    except Exception as e:
        logger.error(f"Error pulling user db info: {e}")

    # Extend top message with upcoming qs list
    if len(upcoming_qs_df) > 0:
        top_message += '\n\nYou have some upcoming Qs:'
        for index, row in upcoming_qs_df.iterrows():
            dt_fmt = row['event_date'].strftime("%a %m-%d")
            top_message += f"\n- {row['event_type']} on {dt_fmt} @ {row['event_time']} at {row['ao_display_name']}"

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

    if (constants.use_weinkes()) and (current_week_weinke_url != None) and (next_week_weinke_url != None):
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
    refresh_button = forms.make_action_button_row([inputs.ActionButton("Refresh Schedule", action = actions.REFRESH_ACTION)])
    blocks.append(refresh_button)

    # Optionally add admin button
    user_info_dict = client.users_info(
        user=user_id
    )
    if user_info_dict['user']['is_admin']:
        button = forms.make_action_button_row([inputs.ActionButton("Manage Region Calendar", action = actions.MANAGE_SCHEDULE_ACTION)])
        blocks.append(button)
        blocks.append(forms.make_action_button_row([inputs.GENERAL_SETTINGS]))

    if google.is_enabled():
        if commands.is_connected(team_id):
            blocks.append(forms.make_action_button_row([inputs.GOOGLE_DISCONNECT]))
        else:
            blocks.append(forms.make_action_button_row([inputs.GOOGLE_CONNECT]))

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
