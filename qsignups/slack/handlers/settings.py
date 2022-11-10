from qsignups.database import my_connect
from qsignups.slack import inputs
from . import UpdateResponse

def update(client, user_id, team_id, logger, input_data) -> UpdateResponse:

    query_params = {
        'team_id': team_id
    }

    query_params['weekly_weinke_channel'] = inputs.WEINKIE_INPUT.get_selected_value(input_data)
    query_params['signup_reminders'] = inputs.Q_REMINDER_RADIO.get_selected_value(input_data) == inputs.Q_REMINDER_ENABLED.value
    query_params['weekly_ao_reminders'] = inputs.AO_REMINDER_RADIO.get_selected_value(input_data) == inputs.AO_REMINDER_ENABLED.value
    query_params['google_calendar_id'] = inputs.GOOGLE_CALENDAR_INPUT.get_selected_value(input_data)

    print("FOUND GPARAMS ", query_params)

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
            return UpdateResponse(success = True)
    except Exception as e:
        logger.error(f"Error writing to db: {e}")
        return UpdateResponse(success = False, message = f"{e}")

