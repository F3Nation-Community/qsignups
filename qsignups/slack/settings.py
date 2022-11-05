import pandas as pd

from qsignups.database import my_connect
from qsignups.slack import actions, utilities

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
        utilities.make_input_field(actions.WEINKIE_INPUT),
        utilities.make_radio_button_input(actions.Q_REMINDER_RADIO),
        utilities.make_radio_button_input(actions.AO_REMINDER_RADIO),
        utilities.make_input_field(actions.GOOGLE_CALENDAR_INPUT, initial_value = region_df['google_calendar_id']),
    ]

    blocks.append(utilities.make_action_button_row([
        actions.make_submit_button(actions.EDIT_SETTINGS_ACTION),
        actions.CANCEL_BUTTON
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
