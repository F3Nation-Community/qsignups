from database import DbManager
from database.orm import AO
from database.orm.views import vwAOsSort

import q_google
from q_google import calendar, authenticate
from slack import actions, forms, inputs

def make_ao_selector(team_id, user_id, client, logger, label, action):
    # list of AOs for dropdown
    aos: list[vwAOsSort] = DbManager.find_records(vwAOsSort, [vwAOsSort.team_id == team_id])
    ao_list = [ao.ao_display_name for ao in aos]
    ao_id_list = [ao.ao_channel_id for ao in aos]

    blocks = [inputs.SectionBlock(
        label=label,
        action=action,
        element=inputs.SelectorElement(
            placeholder="Select an AO",
            options=inputs.as_selector_options(ao_list, ao_id_list)
        )
    ).as_form_field()]

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

def edit_form(team_id, user_id, client, logger, body):

    ao_channel_id, ao_display_name = inputs.SECTION_SELECTOR.get_selected_value(input_data=body, text_too=True)

    aos: [vwAOsSort] = DbManager.find_records(vwAOsSort, [vwAOsSort.ao_channel_id == ao_channel_id])
    if not aos or len(aos) != 1:
        print(f"Unable to find the AO for {ao_channel_id}")
        return False
    ao: vwAOsSort = aos[0]

    blocks = [
        forms.make_header_row(f"*Edit AO:*\n*{ao_display_name}*\n{ao_channel_id}"),
        inputs.AO_TITLE_INPUT.as_form_field(initial_value = ao_display_name),
        inputs.AO_SUBTITLE_INPUT.as_form_field(initial_value = ao.ao_location_subtitle),
    ]
    if q_google.is_available(team_id) and authenticate.is_connected(team_id):
        calendars = calendar.get_calendars(team_id)
        options = [ inputs.SelectorOption(name = x.name, value = x.id) for x in calendars]
        input = inputs.GOOGLE_CALENDAR_SELECT.with_options(options)
        blocks.append(input.as_form_field(ao.google_calendar_id))

    blocks.append(forms.make_action_button_row([
        inputs.make_submit_button(actions.EDIT_AO_ACTION),
        inputs.CANCEL_BUTTON
    ]))

    try:
        client.views_publish(
            user_id=user_id,
            view={
                "type": "home",
                "blocks": blocks,
                "private_metadata": ao_channel_id
            }
        )
        return True
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")
        print(e)
        return False

def add_form(team_id, user_id, client, logger):
    logger.info('gather input data')
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Select an AO channel:*"
      }
        },
        {
            "type": "input",
            "block_id": "add_ao_channel_select",
            "element": {
                "type": "channels_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select a channel",
                    "emoji": True
                },
                "action_id": "add_ao_channel_select"
            },
            "label": {
                "type": "plain_text",
                "text": "Channel associated with AO",
                "emoji": True
            }
        },
        {
            "type": "input",
            "block_id": "ao_display_name",
            "element": {
                "type": "plain_text_input",
                "action_id": "ao_display_name",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Weasel's Ridge"
                }
            },
            "label": {
                "type": "plain_text",
                "text": "AO Title"
            }
        },
        {
            "type": "input",
            "block_id": "ao_location_subtitle",
            "element": {
                "type": "plain_text_input",
                "multiline": True,
                "action_id": "ao_location_subtitle",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Oompa Loompa Kingdom"
                }
            },
            "label": {
                "type": "plain_text",
                "text": "Location (township, park, etc.)"
            }
        }
    ]

    blocks.append(forms.make_action_button_row([
        inputs.make_submit_button(actions.ADD_AO_ACTION),
        inputs.CANCEL_BUTTON,
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

def delete_form(team_id, user_id, client, logger):

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
            "block_id": actions.DELETE_AO_SELECT_ACTION,
            "text": {
                "type": "mrkdwn",
                "text": "Please select an AO to delete:"
            },
            "accessory": {
                "action_id": actions.DELETE_AO_SELECT_ACTION,
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

def pull_aos(team_id):
    aos: list[AO] = DbManager.find_records(AO, [AO.team_id == team_id])
    aos_list, aos_sort = {}, {}
    for index, ao in enumerate(aos):
        aos_list[index] = ao.ao_display_name
        aos_sort[index] = ao.ao_display_name.replace('The ', '')

    aos_sort = dict(sorted(aos_sort.items(), key=lambda x:x[1]))
    return([aos_list[i] for i in aos_sort.keys()])
