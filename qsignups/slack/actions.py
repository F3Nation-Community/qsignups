from typing import List
from dataclasses import dataclass
from qsignups import utilities

CANCEL_BUTTON_ACTION = "cancel_button_select"
EDIT_EVENT_ACTION = "submit_edit_event_button"
ADD_EVENT_ACTION = "submit_add_event_button"
ADD_AO_ACTION = "submit_add_ao_button"
EDIT_AO_ACTION = "submit_edit_ao_button"
LOAD_SCHEDULE_FORM_ACTION = "manage_schedule_option_button"
MANAGE_SCHEDULE_ACTION = "manage_schedule_button"
EDIT_SETTINGS_ACTION = "submit_general_settings"
REFRESH_ACTION = "refresh_home"

@dataclass
class ActionButton:
  label: str
  action: str

@dataclass
class ActionInput(ActionButton):
  placeholder: str
  input_type: str
  optional: bool = True

  def get_selected_value(self, input_data):
    return utilities.safe_get(input_data, self.action, self.action, "value")

@dataclass
class ActionChannelInput(ActionButton):
  placeholder: str
  optional: bool = True

  def get_selected_value(self, input_data):
    if self.input_type == "plain_text_input":
      return utilities.safe_get(input_data, self.action, self.action, "value")
    else:
      return utilities.safe_get(input_data, self.action, self.action, self.input_type)

@dataclass
class ActionRadioButton(ActionButton):
  value: object

@dataclass
class ActionRadioButtons(ActionButton):
  options: List[ActionRadioButton]
  def get_selected_value(self, input_data):
    return utilities.safe_get(input_data, self.action, self.action, 'selected_option', 'value')

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

CANCEL_BUTTON: ActionButton = ActionButton(label = 'Cancel', action = CANCEL_BUTTON_ACTION)

def make_submit_button(action):
  return ActionButton(label = 'Submit', action = action)

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
