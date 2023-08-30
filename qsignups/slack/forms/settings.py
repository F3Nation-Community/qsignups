from database import DbManager
from database.orm import Region
from slack import actions, forms, inputs
import google
# from google import calendar, authenticate

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
    # if google.is_available(team_id) and authenticate.is_connected(team_id):
    #     calendars = calendar.get_calendars(team_id)
    #     options = [ inputs.SelectorOption(name = x.name, value = x.id) for x in calendars]
    #     input = inputs.GOOGLE_CALENDAR_SELECT.with_options(options)
    #     blocks.append(input.as_form_field(initial_value = region.google_calendar_id))

    #     blocks.append(inputs.TIMEZONE_SELECT.as_form_field(initial_value = region.timezone))
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
