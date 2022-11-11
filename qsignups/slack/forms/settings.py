import pandas as pd

from qsignups.database import my_connect
from qsignups.slack import actions, forms, inputs

def general_form(team_id, user_id, client, logger):
    # Pull current settings
    region_df = None
    try:
        with my_connect(team_id) as mydb:
            sql_pull = f"SELECT * FROM {mydb.db}.qsignups_regions WHERE team_id = '{team_id}';"
            region_df = pd.read_sql(sql_pull, mydb.conn).iloc[0]
    except Exception as e:
        logger.error(f"Error pulling region info: {e}")
        print(e)

    initial_q_reminder = None
    if region_df["signup_reminders"] == 1:
        initial_q_reminder = inputs.Q_REMINDER_ENABLED
    elif region_df["signup_reminders"] == 0:
        initial_q_reminder = inputs.Q_REMINDER_DISABLED
    else:
        initial_q_reminder = None

    initial_ao_reminder = None
    if region_df["weekly_ao_reminders"] == 1:
        initial_ao_reminder = inputs.AO_REMINDER_ENABLED
    elif region_df["weekly_ao_reminders"] == 0:
        initial_ao_reminder = inputs.AO_REMINDER_DISABLED
    else:
        initial_ao_reminder = None

    blocks = [
        forms.make_header_row("General Region Settings"),
        inputs.WEINKIE_INPUT.as_form_field(initial_value = region_df['weekly_weinke_channel']),
        inputs.Q_REMINDER_RADIO.as_form_field(initial_value = initial_q_reminder),
        inputs.AO_REMINDER_RADIO.as_form_field(initial_value = initial_ao_reminder),
        inputs.GOOGLE_CALENDAR_INPUT.as_form_field(initial_value = region_df['google_calendar_id']),
        forms.make_action_button_row([
            inputs.make_submit_button(actions.EDIT_SETTINGS_ACTION),
            inputs.CANCEL_BUTTON
        ])
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
