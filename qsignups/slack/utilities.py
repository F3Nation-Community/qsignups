from qsignups import actions
from dataclasses import dataclass

@dataclass
class ActionButton:
  text: str
  action: str

CANCEL_BUTTON: ActionButton = ActionButton(text = 'Cancel', action = actions.CANCEL_BUTTON_ACTION)

def make_cancel_button():
  return make_action_buttons([CANCEL_BUTTON])

def make_button(button_text, action_id):
  return make_action_buttons([ActionButton(text = button_text, action = action_id)])

def make_action_buttons(buttons):
  return {
      "type":"actions",
      "elements":[ make_action_button(b) for b in buttons ]
  }

def make_action_button(button: ActionButton):
  return {
              "type":"button",
              "text":{
                  "type":"plain_text",
                  "text": button.text,
                  "emoji":True
              },
              "action_id": button.action,
              "value": button.text
          }
