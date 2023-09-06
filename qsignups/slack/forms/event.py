from datetime import date

from database import DbManager
from database.orm.views import vwWeeklyEvents, vwAOsSort
from slack import actions, forms, inputs

from utilities import list_to_dict
import q_google
from q_google import calendar, authenticate

from sqlalchemy import func

def add_single_form(team_id, user_id, client, logger):

    # list of AOs for dropdown
    aos: list[vwAOsSort] = DbManager.find_records(vwAOsSort, [vwAOsSort.team_id == team_id])
    ao_list = [ao.ao_display_name for ao in aos]

    ao_selector = inputs.ActionSelector(
        label = "Select an AO",
        action = "ao_display_name_select_action",
        options = inputs.as_selector_options(ao_list))

    blocks = [
        inputs.EVENT_TYPE_SELECTOR.as_form_field(),
        inputs.ActionInput(
            label = "Custom Event Name",
            action = "event_type_custom",
            placeholder = "If custom is selected, specify a name",
            optional = True).as_form_field(),
        ao_selector.as_form_field(),
    ]

    # TODO: have "other" / freeform option
    # TODO: add this to form
    special_list = [
        'None',
        'The Forge',
        'VQ',
        'F3versary',
        'Birthday Q',
        'AO Launch',
        'IronPAX',
        'Convergence'
    ]
    special_selector = inputs.ActionSelector(
        label = "Special Event Tag",
        action = "event_special_type_selector",
        options = inputs.as_selector_options(special_list))
    blocks.append(special_selector.as_form_field())
    blocks.append(inputs.EVENT_DATE_SELECTOR.as_form_field(initial_value = date.today().strftime('%Y-%m-%d')))

    blocks += [
        inputs.START_TIME_SELECTOR.as_form_field(initial_value = "05:30"),
        inputs.END_TIME_SELECTOR.as_form_field(initial_value = "06:15"),

        forms.make_action_button_row([
            inputs.make_submit_button(actions.ADD_SINGLE_EVENT_ACTION),
            inputs.CANCEL_BUTTON
        ]),
        forms.make_header_row("Please wait after hitting Submit, and do not hit it more than once")
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

def add_recurring_form(team_id, user_id, client, logger):

    # list of AOs for dropdown
    aos: list[vwAOsSort] = DbManager.find_records(vwAOsSort, [vwAOsSort.team_id == team_id])
    ao_list = [ao.ao_display_name for ao in aos]

    ao_selector = inputs.ActionSelector(
        label = "Select an AO",
        action = "ao_display_name_select_action",
        options = inputs.as_selector_options(ao_list))

    blocks = [
        inputs.EVENT_TYPE_SELECTOR.as_form_field(),
        inputs.ActionInput(
            label = "Custom Event Name",
            action = "event_type_custom",
            placeholder = "If custom is selected, specify a name",
            optional = True).as_form_field(),
        ao_selector.as_form_field(),
    ]

    blocks.append(inputs.WEEKDAY_SELECTOR.as_form_field())
    blocks.append(inputs.START_DATE_SELECTOR.as_form_field(initial_value = date.today().strftime('%Y-%m-%d')))

    blocks += [
        inputs.START_TIME_SELECTOR.as_form_field(initial_value = "05:30"),
        inputs.END_TIME_SELECTOR.as_form_field(initial_value = "06:15"),

        forms.make_action_button_row([
            inputs.make_submit_button(actions.ADD_RECURRING_EVENT_ACTION),
            inputs.CANCEL_BUTTON
        ]),
        forms.make_header_row("Please wait after hitting Submit, and do not hit it more than once")
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

def delete_single_form(team_id, user_id, client, logger):

    # list of AOs for dropdown
    aos: list[vwAOsSort] = DbManager.find_records(vwAOsSort, [vwAOsSort.team_id == team_id])

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

    # Build blocks
    blocks = [
        {
            "type": "section",
            "block_id": "delete_single_event_ao_select",
            "text": {
                "type": "mrkdwn",
                "text": "Please select an AO to delete an event from:"
            },
            "accessory": {
                "action_id": "delete_single_event_ao_select",
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select an AO"
            },
            "options": ao_options
            }
        }
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

def select_recurring_for_edit_form(team_id, user_id, client, logger, input_data):

    ao_channel_id = inputs.SECTION_SELECTOR.get_selected_value(input_data)

    weekly_events: list[vwWeeklyEvents] = DbManager.find_records(vwWeeklyEvents, [
        vwWeeklyEvents.team_id == team_id,
        vwWeeklyEvents.ao_channel_id == ao_channel_id
    ])

    # Construct view
    # Top of view
    blocks = [
        forms.make_header_row("Please select a recurring event to edit:"),
        forms.make_divider(),
    ]

    current_ao = ''
    for event in weekly_events:

        if event.ao_display_name != current_ao:
            if current_ao != '':
                blocks.append(forms.make_divider())

            blocks.append(forms.make_section_header_row(event.ao_display_name))
            current_ao = event.ao_display_name

        button = inputs.ActionButton(
            "Edit Event",
            actions.SELECT_SLOT_EDIT_RECURRING_EVENT_FORM,
            value = str(event.id))
        blocks.append(
          forms.make_header_row(
            f"{event.event_type} {event.event_day_of_week}s @ {event.event_time}",
            accessory = button)
        )


    # Cancel block
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

def select_recurring_form_for_delete(team_id, user_id, client, logger, input_data):
    ao_channel_id = inputs.SECTION_SELECTOR.get_selected_value(input_data)
    events = DbManager.find_records(vwWeeklyEvents, [ vwWeeklyEvents.team_id == team_id, vwWeeklyEvents.ao_channel_id == ao_channel_id])

    # Sort results_df
    day_of_week_map = {'Sunday':0, 'Monday':1, 'Tuesday':2, 'Wednesday':3, 'Thursday':4, 'Friday':5, 'Saturday':6}

    # Construct view
    # Top of view
    blocks = [
        forms.make_header_row("Please select a recurring event to delete:"),
        forms.make_divider()
    ]

    events_by_ao = list_to_dict(events, lambda x: x.ao_display_name)

    sorted_event_names = sorted(events_by_ao.keys(), key = lambda a: a.replace('The ', ''))

    # Show next x number of events
    for ao_display_name in sorted_event_names:
        # Header block
        blocks.append(forms.make_section_header_row(ao_display_name))

        sorted_events = sorted(events_by_ao[ao_display_name], key = lambda x: day_of_week_map[x.event_day_of_week])

        # Create button blocks for each event for each AO
        for event in sorted_events:
            button = inputs.ActionButton(label = "Delete Event", action = actions.DELETE_RECURRING_SELECT_ACTION, value = str(event.id), style = "danger")
            blocks.append(forms.make_header_row(f"{event.event_type} {event.event_day_of_week}s @ {event.event_time}", accessory = button))

        # Divider block
        blocks.append(forms.make_divider())

    # Cancel block
    blocks.append(forms.make_action_button_row([inputs.CANCEL_BUTTON]))

    print(blocks)
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

def edit_recurring_form(team_id, user_id, client, logger, input_data):
    event_id = int(input_data)
    event: vwWeeklyEvents = DbManager.find_records(vwWeeklyEvents, [vwWeeklyEvents.id == event_id])[0]

    aos: list[vwAOsSort] = DbManager.find_records(vwAOsSort, [vwAOsSort.team_id == team_id])
    ao_list = [ao.ao_display_name for ao in aos]

    event_start_time = event.event_time[:2] + ':' + event.event_time[2:]
    if event.event_end_time:
        event_end_time = event.event_end_time[:2] + ':' + event.event_end_time[2:]
    else:
        event_end_time = None

    if event.event_type in ['Bootcamp', 'QSource', 'Custom']:
        initial_type_select = event.event_type
        initial_type_manual = ''
    else:
        initial_type_select = 'Custom'
        initial_type_manual = event.event_type

    selector_input: inputs.ActionSelector = inputs.AO_SELECTOR.with_options(inputs.as_selector_options(ao_list))
    blocks = [
        inputs.EVENT_TYPE_SELECTOR.as_form_field(initial_value = initial_type_select),
        inputs.CUSTOM_EVENT_INPUT.as_form_field(initial_value = initial_type_manual),
        selector_input.as_form_field(initial_value = event.ao_display_name),
        inputs.WEEKDAY_SELECTOR.as_form_field(initial_value = event.event_day_of_week),
        inputs.START_DATE_SELECTOR.as_form_field(),
        inputs.START_TIME_SELECTOR.as_form_field(initial_value = event_start_time),
        inputs.END_TIME_SELECTOR.as_form_field(initial_value = event_end_time),
    ]

    if q_google.is_available(team_id) and authenticate.is_connected(team_id):
        calendars = calendar.get_calendars(team_id)
        options = [ inputs.SelectorOption(name = x.name, value = x.id) for x in calendars]
        input = inputs.GOOGLE_CALENDAR_SELECT.with_options(options)
        input = input.with_label("If this event has a different google calendar, please select it here.  Leave it empty to use the region calendar.")
        blocks.append(input.as_form_field(initial_value = None))
        input = inputs.MAP_URL_INPUT.with_label("If this event has a unique location URL, please enter it here.  Leave it empty to use the same MapURL as the AO")
        blocks.append(input.as_form_field(initial_value=event.map_url))

    blocks += [
        forms.make_action_button_row([
            inputs.make_submit_button(actions.EDIT_RECURRING_EVENT_ACTION),
            inputs.CANCEL_BUTTON
        ]),
        forms.make_header_row("Please wait after hitting Submit, and do not hit it more than once"),
    ]

    try:
        client.views_publish(
            user_id=user_id,
            view={
                "type": "home",
                "blocks": blocks,
                "private_metadata": str(event_id)
            },
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")
        print(e)
