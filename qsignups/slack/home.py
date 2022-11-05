from datetime import timedelta, date
import pandas as pd
from qsignups.database import my_connect
from qsignups import actions, constants
from qsignups.slack import utilities

def refresh(client, user_id, logger, top_message, team_id, context):
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
            if constants.use_weinkes():
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
    refresh_button = utilities.make_button("Refresh Schedule", action_id = actions.REFRESH_ACTION)
    blocks.append(refresh_button)

    # Optionally add admin button
    user_info_dict = client.users_info(
        user=user_id
    )
    if user_info_dict['user']['is_admin']:
        blocks.append(utilities.make_button("Manage Region Calendar", action_id = actions.MANAGE_SCHEDULE_ACTION))

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
