import pytz
from typing import List
from dataclasses import dataclass
import utilities
from . import actions

@dataclass
class BaseAction:
  label: str
  action: str

  def make_label_field(self, text = None):
    return {
      "type": "plain_text",
      "text": text or self.label,
      "emoji":True
    }

  def as_form_field(self, initial_value = None):
    raise Exception("Not Implemented")

@dataclass
class ActionButton(BaseAction):
  style: str = None
  value: str = None
  confirm: object = None

  def as_form_field(self, initial_value = None):
    j = {
      "type": "button",
      "text": self.make_label_field(),
      "action_id": self.action,
      "value": self.value or self.label
    }
    if self.style:
      j['style'] = self.style
    if self.confirm:
      j['confirm'] = self.confirm
    return j

@dataclass
class ActionInput(BaseAction):
  placeholder: str
  optional: bool = True

  def get_selected_value(self, input_data):
    return utilities.safe_get(input_data, self.action, self.action, "value")

  def as_form_field(self, initial_value = None):
    return {
        "type": "input",
        "block_id": self.action,
        "element": {
          "type": "plain_text_input",
          "placeholder": self.make_label_field(self.placeholder),
          "action_id": self.action,
          "initial_value": initial_value or '',
        },
        "optional": self.optional,
        "label": self.make_label_field()
    }

@dataclass
class ActionDateSelect(BaseAction):

  def as_form_field(self, initial_value = None):
    j = {
        "type": "input",
        "block_id": self.action,
        "element": {
            "type": "datepicker",
            "placeholder": self.make_label_field(),
            "action_id": self.action
        },
        "label": self.make_label_field()
    }
    if initial_value:
      j["element"]["initial_date"] = initial_value

    return j

  def get_selected_value(self, input_data):
    return utilities.safe_get(input_data, self.action, self.action, "selected_date")

@dataclass
class ActionTimeSelect(BaseAction):
  optional: bool = True
  placeholder: str = None

  def as_form_field(self, initial_value = None):
    j = {
          "type": "input",
          "block_id": self.action,
          "element": {
              "type": "timepicker",
              "placeholder": self.make_label_field(self.placeholder),
              "action_id": self.action
          },
          "label": {
              "type": "plain_text",
              "text": self.label,
              "emoji": True
          }
      }
    if initial_value:
      j["element"]["initial_time"] = initial_value
    return j

  def get_selected_value(self, input_data):
    return utilities.safe_get(input_data, self.action, self.action, "selected_time")

@dataclass
class ActionChannelInput(BaseAction):
  placeholder: str
  optional: bool = True

  def get_selected_value(self, input_data):
    return utilities.safe_get(input_data, self.action, self.action, "selected_channel")

  def as_form_field(self, initial_value = None):
    j = {
        "type": "input",
        "block_id": self.action,
        "element": {
          "type": "channels_select",
          "placeholder": self.make_label_field(self.placeholder),
          "action_id": self.action,
        },
        "label": self.make_label_field()
    }
    if initial_value:
      j['element']['initial_channel'] = initial_value
    return j

@dataclass
class ActionRadioButton(BaseAction):
  value: object

  def as_form_field(self, initial_value=None):
    return {
      "text": self.make_label_field(),
      "value": self.value
    }

@dataclass
class ActionRadioButtons(BaseAction):
  options: List[ActionRadioButton]

  def get_selected_value(self, input_data):
    return utilities.safe_get(input_data, self.action, self.action, 'selected_option', 'value')

  def as_form_field(self, initial_value = None):
    j = {
        "type": "input",
        "block_id": self.action,
        "element": {
          "type": "radio_buttons",
          "options": [ b.as_form_field() for b in self.options ],
          "action_id": self.action,
        },
        "label": self.make_label_field()
    }
    if initial_value:
      if isinstance(initial_value,BaseAction):
        j['element']['initial_option'] = initial_value.as_form_field()
      else:
        j['element']['initial_option'] = initial_value
    return j

@dataclass
class SelectorOption:
  name: str
  value: str

def as_selector_options(names: List[str], values: List[str] = []) -> List[SelectorOption]:
  if values==[]:
    selectors = [SelectorOption(name = x, value = x) for x in names]
  else:
    selectors = [SelectorOption(name = x, value = y) for x, y in zip(names, values)]
  return selectors

@dataclass
class ActionSelector(BaseAction):
  options: List[SelectorOption]

  def with_options(self, options: List[SelectorOption]):
    return ActionSelector(self.label, self.action, options)

  def as_form_field(self, initial_value: str = None):
    if not self.options:
      self.options = as_selector_options(["Default"])

    option_elements = [self.__make_option(o) for o in self.options]
    j = {
          "type": "input",
          "block_id": self.action,
          "element": {
              "type": "static_select",
              "placeholder": self.make_label_field(),
              "options": option_elements,
              "action_id": self.action
          },
          "label": self.make_label_field()
      }
    if initial_value:
      initial_option = next((x for x in option_elements if x["value"] == initial_value), None )
      if initial_option:
        j['element']['initial_option'] = initial_option
    return j

  def get_selected_value(self, input_data):
    return utilities.safe_get(input_data, self.action, self.action, 'selected_option', 'value')

  def __make_option(self, option: SelectorOption):
    return  {
              "text": {
                  "type": "plain_text",
                  "text": option.name,
                  "emoji": True
              },
              "value": option.value
            }

Q_REMINDER_ENABLED = ActionRadioButton(label = "Enable Q reminders", action = None, value = "enabled")
Q_REMINDER_DISABLED = ActionRadioButton(label = "Disable Q reminders", action = None, value = "disabled")
Q_REMINDER_RADIO = ActionRadioButtons(
  action = "q_reminder_enable",
  label = "Enable Q Reminders?",
  options = [ Q_REMINDER_ENABLED, Q_REMINDER_DISABLED ]
)

AO_REMINDER_ENABLED = ActionRadioButton(label = "Enable AO reminders", action = None, value = "enabled")
AO_REMINDER_DISABLED = ActionRadioButton(label = "Disable AO reminders", action = None, value = "disabled")
AO_REMINDER_RADIO = ActionRadioButtons(
  action = "ao_reminder_enable",
  label = "Enable AO Reminders?",
  options = [ AO_REMINDER_ENABLED, AO_REMINDER_DISABLED ]
)

EVENT_TYPE_RECURRING = ActionRadioButton(label = "Recurring event", action = None, value = "recurring")
EVENT_TYPE_SINGLE = ActionRadioButton(label = "Single event", action = None, value = "single")
EVENT_TYPE_RADIO = ActionRadioButtons(
  action = "add_event_recurring_select_action",
  label = "Is this a recurring or single event?",
  options = [ EVENT_TYPE_RECURRING, EVENT_TYPE_SINGLE ]
)

CANCEL_BUTTON: ActionButton = ActionButton(label = 'Cancel', action = actions.CANCEL_BUTTON_ACTION, style = 'danger')

def make_submit_button(action):
  return ActionButton(label = 'Submit', action = action, style = 'primary')

WEINKIE_INPUT = ActionChannelInput(
  action = "weinke_channel_select",
  placeholder = "Select a channel",
  label = "Public channel for posting weekly schedules:"
)

GOOGLE_CALENDAR_SELECT: ActionSelector = ActionSelector(
  action = 'google_calendar_select',
  label = 'Select your Google Calendar',
  options = as_selector_options([]))

GOOGLE_CONNECT: ActionButton = ActionButton(label = 'Connect Google Calendar', action = "connect_google_calendar", style = 'primary')
GOOGLE_DISCONNECT: ActionButton = ActionButton(label = 'Disonnect Google Calendar', action = "disconnect_google_calendar", style = 'danger')

ADD_SINGLE_EVENT_FORM: ActionButton = ActionButton(label = 'Add a single event', action = "add_single_event_form")
EDIT_SINGLE_EVENT_FORM: ActionButton = ActionButton(label = 'Edit a single event', action = "edit_single_event_form")
DELETE_SINGLE_EVENT_FORM: ActionButton = ActionButton(label = 'Delete a single event', action = "delete_single_event_form")

ADD_RECURRING_EVENT_FORM: ActionButton = ActionButton(label = 'Add a recurring event', action = "add_recurring_event_form")
EDIT_RECURRING_EVENT_FORM: ActionButton = ActionButton(label = 'Edit a recurring event', action = "edit_recurring_event_form")
SELECT_RECURRING_EVENT_FORM: ActionButton = ActionButton(label = 'Edit a recurring event', action = "edit_recurring_event_form")
DELETE_RECURRING_EVENT_FORM: ActionButton = ActionButton(label = 'Delete a recurring event', action = "delete_recurring_event_form")

ADD_AO_FORM: ActionButton = ActionButton(label = 'Add an AO', action = "add_ao_form")
EDIT_AO_FORM: ActionButton = ActionButton(label = 'Edit an AO', action = "edit_ao_form")
DELETE_AO_FORM: ActionButton = ActionButton(label = 'Delete an AO', action = "delete_ao_form")

GENERAL_SETTINGS: ActionButton = ActionButton(label = 'General settings', action = "general_settings_form")

WEEKDAY_SELECTOR = ActionSelector(
  label = "Day of Week",
  action = "event_day_of_week_select_action",
  options = as_selector_options([
            'Monday',
            'Tuesday',
            'Wednesday',
            'Thursday',
            'Friday',
            'Saturday',
            'Sunday'
        ]))

START_DATE_SELECTOR = ActionDateSelect(label = "Select Start Date", action = "add_event_datepicker")
EVENT_DATE_SELECTOR = ActionDateSelect(label = "Select Event Date", action = "add_event_datepicker")
START_TIME_SELECTOR = ActionTimeSelect(label = "Select Start Time", action = "event_start_time_select", optional = True)
END_TIME_SELECTOR = ActionTimeSelect(label = "Select End Time", action = "event_end_time_select", optional = True)

EVENT_TYPE_SELECTOR = ActionSelector(
  label = "Select an event type",
  action = "event_type_select_action",
  options = as_selector_options(['Bootcamp', 'QSource', 'Custom']))

CUSTOM_EVENT_INPUT = ActionInput(
  label = "Custom Event Name",
  action = "event_type_custom",
  placeholder = "If custom is selected, specify a name",
  optional = True)

AO_SELECTOR = ActionSelector(
  label = "Select an AO",
  action = "ao_display_name_select_action",
  options = [])

TIMEZONE_SELECT = ActionSelector(
  label = "Select your Timezone",
  action = "timezone_select_action",
  options = as_selector_options([
    'America/New_York',
    'America/Detroit',
    'America/Chicago',
    'America/Indiana/Indianapolis',
    'America/Indiana/Knox',
    'America/Denver',
    'America/Phoenix',
    'America/Los_Angeles',
    'Pacific/Honolulu',
  ])
)

@dataclass
class BaseBlock:
  label: str
  action: str
  label_style: str = "plain_text"

  def make_label_field(self, text = None):
    if self.label_style == "plain_text":
      return {
        "type": "plain_text",
        "text": text or self.label,
        "emoji":True
      }
    elif self.label_style == "mrkdwn":
      return {
        "type": "mrkdwn",
        "text": text or self.label
      }

  def as_form_field(self, initial_value = None):
    raise Exception("Not Implemented")

@dataclass
class BaseElement():
  placeholder: str = None
  initial: str = None
  
  def make_placeholder_field(self):
    return {
      "placeholder": {
        "type": "plain_text",
        "text": self.placeholder,
        "emoji": True
      }
    }
  
  def get_selected_value():
    return "Not yet implemented"

@dataclass
class InputBlock(BaseBlock):
  optional: bool = True
  element: BaseElement = None

  def get_selected_value(self, input_data):
    # return utilities.safe_get(input_data, self.action, self.action, "value")
    return self.element.get_selected_value(input_data, self.action)

  def as_form_field(self):
    block = {
      "type": "input",
      "block_id": self.action,
      "optional": self.optional,
      "label": self.make_label_field()
    }
    block.update({"element": self.element.as_form_field(action=self.action)})
    return block
    
@dataclass
class SectionBlock(BaseBlock):
  element: BaseElement = None

  def get_selected_value(self, input_data, **kwargs):
    # return utilities.safe_get(input_data, self.action, self.action, "value")
    return self.element.get_selected_value(input_data, **kwargs)

  def as_form_field(self):
    block = {
      "type": "section",
      "block_id": self.action,
      "text": self.make_label_field()
    }
    block.update({"accessory": self.element.as_form_field(action=self.action)})
    return block

@dataclass
class ButtonElement(BaseAction):
  style: str = None
  value: str = None
  confirm: object = None

  def as_form_field(self):
    j = {
      "type": "button",
      "text": self.make_label_field(),
      "action_id": self.action,
      "value": self.value or self.label
    }
    if self.style:
      j['style'] = self.style
    if self.confirm:
      j['confirm'] = self.confirm
    return j

@dataclass
class SelectorElement(BaseElement):
  options: List[SelectorOption] = None

  # def with_options(self, options: List[SelectorOption]):
  #   return SelectorElement(self.label, self.action, options)

  def as_form_field(self, action: str, initial_value: str = None):
    if not self.options:
      self.options = as_selector_options(["Default"])

    option_elements = [self.__make_option(o) for o in self.options]
    j = {
        "type": "static_select",
        "options": option_elements,
        "action_id": action
    }
    if self.placeholder:
      j.update(self.make_placeholder_field())
    
    initial_option = None
    if initial_value:
      initial_option = next((x for x in option_elements if x["value"] == initial_value), None )
      if initial_option:
        j['initial_option'] = initial_option
    return j

  def get_selected_value(self, input_data, text_too: bool = False):
    if text_too:
      return utilities.safe_get(input_data['actions'][0], 'selected_option', 'value'), utilities.safe_get(input_data['actions'][0], 'selected_option', 'text', 'text')
    else:
      return utilities.safe_get(input_data['actions'][0], 'selected_option', 'value')

  def __make_option(self, option: SelectorOption):
    return  {
              "text": {
                  "type": "plain_text",
                  "text": option.name,
                  "emoji": True
              },
              "value": option.value
            }

SECTION_SELECTOR = SectionBlock(
  label = "temp",
  action = "temp",
  element = SelectorElement()
)
 
# options = as_selector_options(['brent', 'evan'], ['35', '32'])
# selector = SelectorElement(options=options, placeholder="Please select a name")

# block = InputBlock(label='This is a different one', action='different_action')
# block.as_form_field(selector)

# block = InputBlock(
#   label="Hello, world!",
#   action="cool_action",
#   element=SelectorElement(
#     placeholder="Please select a name",
#     options=as_selector_options(['brent', 'evan'], ['35', '32'])
#   )
# )
# block.as_form_field()

# block2 = SectionBlock(
#   label="*Hello, world!*",
#   label_style="mrkdwn",
#   action="cool_action",
#   element=SelectorElement(
#     placeholder="Please select a name",
#     options=as_selector_options(['brent', 'evan'], ['35', '32'])
#   )
# )
# block2.as_form_field()
