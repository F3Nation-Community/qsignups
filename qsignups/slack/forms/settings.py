from qsignups.database import DbManager
from qsignups.database.orm import Region
from qsignups.slack import actions, forms, inputs
from qsignups import google
from qsignups.google import commands

def general_form(team_id, user_id, client, logger):
    # Pull current settings
    region: Region = DbManager.get_record(Region, team_id)

    initial_q_reminder = None
    if region.signup_reminders == 1:
        initial_q_reminder = inputs.Q_REMINDER_ENABLED
    elif region.signup_reminders == 0:
        initial_q_reminder = inputs.Q_REMINDER_DISABLED
    else:
        initial_q_reminder = None

    initial_ao_reminder = None
    if region.weekly_ao_reminders == 1:
        initial_ao_reminder = inputs.AO_REMINDER_ENABLED
    elif region.weekly_ao_reminders == 0:
        initial_ao_reminder = inputs.AO_REMINDER_DISABLED
    else:
        initial_ao_reminder = None

    blocks = [
        forms.make_header_row("General Region Settings"),
        inputs.WEINKIE_INPUT.as_form_field(initial_value = region.weekly_weinke_channel),
        inputs.Q_REMINDER_RADIO.as_form_field(initial_value = initial_q_reminder),
        inputs.AO_REMINDER_RADIO.as_form_field(initial_value = initial_ao_reminder)
    ]
    if google.is_enabled() and commands.is_connected(team_id):
        input = inputs.GOOGLE_CALENDAR_SELECT
        calendars = commands.get_calendars(team_id)
        input.options = [ inputs.SelectorOption(name = x.name, value = x.id) for x in calendars]
        blocks.append(input.as_form_field(initial_value = region.google_calendar_id))
    blocks.append(
        forms.make_action_button_row([
            inputs.make_submit_button(actions.EDIT_SETTINGS_ACTION),
            inputs.CANCEL_BUTTON
        ])
    )

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
