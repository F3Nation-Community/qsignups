from datetime import date

from qsignups.database import DbManager
from qsignups.database.orm.views import vwWeeklyEvents, vwAOsSort
from qsignups.slack import actions, forms, inputs

from qsignups.utilities import list_to_dict

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
        {
        "type": "context",
        "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Please wait after hitting Submit, and do not hit it more than once"
                }
            ]
        }
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
        {
        "type": "context",
        "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Please wait after hitting Submit, and do not hit it more than once"
                }
            ]
        }
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

def edit_single_form(team_id, user_id, client, logger):

    # list of AOs for dropdown
    aos: list[vwAOsSort] = DbManager.find_records(vwAOsSort, [vwAOsSort.team_id == team_id])
    # ao_list = [ao.ao_display_name for ao in aos]
    # ao_id_list = [ao.ao_channel_id for ao in aos]

    # This needs to be a true action block, not an input block
    # ao_selector = inputs.ActionSelector(
    #     label = "Please select an AO to edit:",
    #     action = "edit_event_ao_select",
    #     options = inputs.as_selector_options(ao_list, ao_id_list))

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
            "block_id": "ao_select_block",
            "text": {
                "type": "mrkdwn",
                "text": "Please select an AO to edit:"
            },
            "accessory": {
                "action_id": "edit_event_ao_select",
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

def select_recurring_form_for_edit(team_id, user_id, client, logger):
    
    weekly_events = DbManager.find_records(vwWeeklyEvents, [vwWeeklyEvents.team_id == team_id])

    # Construct view
    # Top of view
    blocks = [{
            "type": "section",
            "text": {"type": "mrkdwn", "text": "Please select a recurring event to edit:"}
        },
        {
            "type": "divider"
        }
    ]

    current_ao = ''
    for event in weekly_events:
        
        if event.ao_display_name != current_ao:
            if current_ao != '':
                blocks.append({"type":"divider"})
                
            blocks.append(forms.make_section_header_row(event.ao_display_name))
            current_ao = event.ao_display_name
        
        blocks.append(
            {
                "type":"section",
                "text":{
                    "type":"mrkdwn",
                    "text":f"{event.event_type} {event.event_day_of_week}s @ {event.event_time}"
                },
                "accessory": {
                    "type":"button",
                    "text": {
                        "type":"plain_text",
                        "text":"Edit Event",
                        "emoji":True
                    },
                    "action_id":actions.SELECT_SLOT_EDIT_RECURRING_EVENT_FORM,
                    "value":f"{event.ao_display_name}|{event.event_day_of_week}|{event.event_type}|{event.event_time}|{event.event_end_time}|{event.ao_channel_id}"
                }
            }
        )

    # Cancel block
    blocks.append({
        "type":"actions",
        "elements":[
            {
                "type":"button",
                "text":{
                    "type":"plain_text",
                    "text":"Cancel",
                    "emoji":True
                },
                "action_id":"cancel_button_select",
                "style":"danger",
                "value":"Cancel"
            }
        ]
    })


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

def select_recurring_form_for_delete(team_id, user_id, client, logger):

    events = DbManager.find_records(vwWeeklyEvents, [ vwWeeklyEvents.team_id == team_id])

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
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type":"mrkdwn",
                        "text":f"{event.event_type} {event.event_day_of_week}s @ {event.event_time}"
                    },
                    "accessory": inputs.ActionButton(label = "Delete Event", action = actions.DELETE_RECURRING_SELECT_ACTION, value = str(event.id), style = "danger").as_form_field()
                }
            )

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
    selected_ao, selected_day, selected_event_type, selected_start_time, selected_end_time, selected_ao_id = str.split(input_data, '|')

    aos: list[vwAOsSort] = DbManager.find_records(vwAOsSort, [vwAOsSort.team_id == team_id])
    ao_list = [ao.ao_display_name for ao in aos]
    
    ao_options = []
    for option in ao_list:
        new_option = {
            "text": {
                "type": "plain_text",
                "text": option,
                "emoji": True
            },
            "value": option
        }
        ao_options.append(new_option)
    selected_ao_index = ao_list.index(selected_ao)

    day_list = [
        'Monday',
        'Tuesday',
        'Wednesday',
        'Thursday',
        'Friday',
        'Saturday',
        'Sunday'
    ]
    day_options = []
    for option in day_list:
        new_option = {
            "text": {
                "type": "plain_text",
                "text": option,
                "emoji": True
            },
            "value": option
        }
        day_options.append(new_option)
    selected_day_index = day_list.index(selected_day)

    event_type_list = ['Bootcamp', 'QSource', 'Custom']
    event_type_options = []
    for option in event_type_list:
        new_option = {
            "text": {
                "type": "plain_text",
                "text": option,
                "emoji": True
            },
            "value": option
        }
        event_type_options.append(new_option)
    try:
        selected_event_type_index = event_type_list.index(selected_event_type)
    except ValueError as e:
        selected_event_type_index = -1

    if selected_end_time is None or selected_end_time == 'None':
        selected_end_time = str(int(selected_start_time[:2]) + 1) + ':' + selected_start_time[2:]

    blocks = [
        {
            "type": "input",
            "block_id": "event_type_select",
            "element": {
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select an event type",
                    "emoji": True
                },
                "options": event_type_options,
                "action_id": "event_type_select_action",
                "initial_option": event_type_options[selected_event_type_index]
            },
            "label": {
                "type": "plain_text",
                "text": "Event Type",
                "emoji": True
            }
        },
        {
            "type": "input",
            "block_id": "event_type_custom",
            "element": {
                "type": "plain_text_input",
                "action_id": "event_type_custom",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Custom Event Name"
                },
                "initial_value": selected_event_type
            },
            "label": {
                "type": "plain_text",
                "text": "If Custom selected, please specify"
            },
            "optional": True
        },
        {
            "type": "input",
            "block_id": "ao_display_name_select",
            "element": {
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select an AO",
                    "emoji": True
                },
                "options": ao_options,
                "action_id": "ao_display_name_select_action",
                "initial_option": ao_options[selected_ao_index]
            },
            "label": {
                "type": "plain_text",
                "text": "AO",
                "emoji": True
            }
        },
        {
            "type": "input",
            "block_id": "event_day_of_week_select",
            "element": {
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select a day",
                    "emoji": True
                },
                "options": day_options,
                "action_id": "event_day_of_week_select_action",
                "initial_option": day_options[selected_day_index]
            },
            "label": {
                "type": "plain_text",
                "text": "Day of Week",
                "emoji": True
            }
        },
        {
            "type": "input",
            "block_id": "event_start_time_select",
            "element": {
                "type": "timepicker",
                "initial_time": selected_start_time[:2] + ':' + selected_start_time[2:],
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select time",
                    "emoji": True
                },
                "action_id": "event_start_time_select"
            },
            "label": {
                "type": "plain_text",
                "text": "Event Start",
                "emoji": True
            }
        },
        {
            "type": "input",
            "block_id": "event_end_time_select",
            "element": {
                "type": "timepicker",
                "initial_time": selected_end_time[:2] + ':' + selected_end_time[2:],
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select time",
                    "emoji": True
                },
                "action_id": "event_end_time_select"
            },
            "label": {
                "type": "plain_text",
                "text": "Event End",
                "emoji": True
            }
        },
        {
            "type": "input",
            "block_id": "add_event_datepicker",
            "element": {
                "type": "datepicker",
                "initial_date": date.today().strftime('%Y-%m-%d'),
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select date",
                    "emoji": True
                },
                "action_id": "add_event_datepicker"
            },
            "label": {
                "type": "plain_text",
                "text": "Start Date",
                "emoji": True
            }
        },
        {
            "type": "actions",
            "block_id": "submit_cancel_buttons",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Submit",
                        "emoji": True
                    },
                    "value": "submit",
                    "action_id": actions.EDIT_RECURRING_EVENT_ACTION,
                    "style": "primary"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Cancel",
                        "emoji": True
                    },
                    "value": "cancel",
                    "action_id": "cancel_button_select",
                    "style": "danger"
                }
            ]
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Please wait after hitting Submit, and do not hit it more than once"
                }
            ]
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": selected_ao_id + '|' + selected_day + '|' + selected_start_time
                }
            ]
        }

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
