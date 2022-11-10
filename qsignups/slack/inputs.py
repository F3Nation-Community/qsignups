from typing import List
from dataclasses import dataclass
from qsignups import utilities
from . import actions

@dataclass
class BaseAction:
  label: str
  action: str

  def make_label_field(self, text = None):
    return {
      "type":"plain_text",
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
      "type":"button",
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
  input_type: str
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
class ActionChannelInput(BaseAction):
  placeholder: str
  optional: bool = True

  def get_selected_value(self, input_data):
    if self.input_type == "plain_text_input":
      return utilities.safe_get(input_data, self.action, self.action, "value")
    else:
      return utilities.safe_get(input_data, self.action, self.action, self.input_type)

  def as_form_field(self):
    return {
        "type": "input",
        "block_id": self.action,
        "element": {
          "type": "channels_select",
          "placeholder": self.make_label_field(self.placeholder),
          "action_id": self.action,
        },
        "label": self.make_label_field()
    }

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

  def as_form_field(self, initial_value=None):
    return {
        "type": "input",
        "block_id": self.action,
        "element": {
          "type": "radio_buttons",
          "options": [ b.as_form_field() for b in self.options ],
          "action_id": self.action,
        },
        "label": self.make_label_field()
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

CANCEL_BUTTON: ActionButton = ActionButton(label = 'Cancel', action = actions.CANCEL_BUTTON_ACTION, style = 'danger')

def make_submit_button(action):
  return ActionButton(label = 'Submit', action = action, style = 'primary')

WEINKIE_INPUT = ActionChannelInput(
  action = "weinke_channel_select",
  placeholder = "Select a channel",
  label = "Public channel for posting weekly schedules:"
)

GOOGLE_CALENDAR_INPUT = ActionInput(
  action = "google_calendar_id",
  input_type = "plain_text_input",
  placeholder = "Google Calendar ID",
  label = "To connect to a google calendar, provide the ID",
  optional = True
)

ADD_EVENT: ActionButton = ActionButton(label = 'Add an event', action = "add_event_form")
EDIT_EVENT: ActionButton = ActionButton(label = 'Edit an event', action = "edit_event_form")

ADD_AO: ActionButton = ActionButton(label = 'Add an AO', action = "add_ao_form")
EDIT_AO: ActionButton = ActionButton(label = 'Edit an AO', action = "edit_ao_form")
DELETE_AO: ActionButton = ActionButton(label = 'Delete an AO', action = "delete_ao_form")

DELETE_SINGLE_EVENT: ActionButton = ActionButton(label = 'Delete a single event', action = "delete_single_event_form")
GENERAL_SETTINGS: ActionButton = ActionButton(label = 'General settings', action = "general_settings_form")
