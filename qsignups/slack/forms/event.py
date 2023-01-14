from datetime import date
import pandas as pd

from qsignups.database import my_connect, DbManager
from qsignups.database.orm.views import vwWeeklyEvents
from qsignups.slack import actions, forms, inputs

from qsignups.utilities import list_to_dict

def add_single_form(team_id, user_id, client, logger):

    # list of AOs for dropdown
    try:
        with my_connect(team_id) as mydb:
            sql_ao_list = f"SELECT ao_display_name FROM {mydb.db}.qsignups_aos WHERE team_id = '{team_id}' ORDER BY REPLACE(ao_display_name, 'The ', '');"
            ao_list = pd.read_sql(sql_ao_list, mydb.conn)
            ao_list = ao_list['ao_display_name'].values.tolist()
    except Exception as e:
        logger.error(f"Error pulling AO list: {e}")

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
    try:
        with my_connect(team_id) as mydb:
            sql_ao_list = f"SELECT ao_display_name FROM {mydb.db}.qsignups_aos WHERE team_id = '{team_id}' ORDER BY REPLACE(ao_display_name, 'The ', '');"
            ao_list = pd.read_sql(sql_ao_list, mydb.conn)
            ao_list = ao_list['ao_display_name'].values.tolist()
    except Exception as e:
        logger.error(f"Error pulling AO list: {e}")

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
    try:
        with my_connect(team_id) as mydb:
            sql_ao_list = f"SELECT * FROM {mydb.db}.qsignups_aos WHERE team_id = '{team_id}' ORDER BY REPLACE(ao_display_name, 'The ', '');"
            ao_df = pd.read_sql(sql_ao_list, mydb.conn)
    except Exception as e:
        logger.error(f"Error pulling AO list: {e}")

    ao_options = []
    for index, row in ao_df.iterrows():
        new_option = {
            "text": {
                "type": "plain_text",
                "text": row['ao_display_name'],
                "emoji": True
            },
            "value": row['ao_channel_id']
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
    try:
        with my_connect(team_id) as mydb:
            sql_ao_list = f"SELECT * FROM {mydb.db}.qsignups_aos WHERE team_id = '{team_id}' ORDER BY REPLACE(ao_display_name, 'The ', '');"
            ao_df = pd.read_sql(sql_ao_list, mydb.conn)
    except Exception as e:
        logger.error(f"Error pulling AO list: {e}")

    ao_options = []
    for index, row in ao_df.iterrows():
        new_option = {
            "text": {
                "type": "plain_text",
                "text": row['ao_display_name'],
                "emoji": True
            },
            "value": row['ao_channel_id']
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
    results_df = None
    try:
        with my_connect(team_id) as mydb:
            sql_pull = f"""
            SELECT w.*, a.ao_display_name
            FROM {mydb.db}.qsignups_weekly w
            INNER JOIN {mydb.db}.qsignups_aos a
            ON w.ao_channel_id = a.ao_channel_id
                AND w.team_id = a.team_id
            WHERE w.team_id = '{team_id}';
            """
            logger.info(f'Pulling from db, attempting SQL: {sql_pull}')

            results_df = pd.read_sql_query(sql_pull, mydb.conn)
    except Exception as e:
        logger.error(f"Error pulling from schedule_weekly: {e}")

    # Sort results_df
    day_of_week_map = {'Sunday':0, 'Monday':1, 'Tuesday':2, 'Wednesday':3, 'Thursday':4, 'Friday':5, 'Saturday':6}
    results_df['event_day_of_week_num'] = results_df['event_day_of_week'].map(day_of_week_map)
    results_df['ao_display_name_sort'] = results_df['ao_display_name'].str.replace('The ','')
    results_df.sort_values(by=['ao_display_name_sort', 'event_day_of_week_num', 'event_time'], inplace=True)

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

    # Show next x number of events
    for ao in results_df['ao_display_name'].unique():
        # Header block
        blocks.append(forms.make_header_row(ao))

        # Create button blocks for each event for each AO
        for _, row in results_df[results_df['ao_display_name'] == ao].iterrows():
            blocks.append(
                {
                    "type":"section",
                    "text":{
                        "type":"mrkdwn",
                        "text":f"{row['event_type']} {row['event_day_of_week']}s @ {row['event_time']}"
                    },
                    "accessory": {
                        "type":"button",
                        "text": {
                            "type":"plain_text",
                            "text":"Edit Event",
                            "emoji":True
                        },
                        "action_id":"edit_recurring_event_slot_select",
                        "value":f"{row['ao_display_name']}|{row['event_day_of_week']}|{row['event_type']}|{row['event_time']}|{row['event_end_time']}|{row['ao_channel_id']}"
                    }
                }
            )

        # Divider block
        blocks.append({
            "type":"divider"
        })

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
                        "text":f"{event.ao_display_name} {event.event_day_of_week}s @ {event.event_time}"
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
