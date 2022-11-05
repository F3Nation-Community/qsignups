from qsignups.slack import actions

def make_cancel_button():
  return make_action_button(actions.CANCEL_BUTTON)

def make_cancel_button_row():
  return make_action_button_row([actions.CANCEL_BUTTON])

def make_submit_button(action):
  return make_action_button(actions.ActionButton(label = "Submit", action = action))

def make_action_button_row(buttons):
  return {
      "type":"actions",
      "elements":[ make_action_button(b) for b in buttons ]
  }

def make_action_button(button: actions.ActionButton):
  return {
            "type":"button",
            "text": make_text_field(button.label),
            "action_id": button.action,
            "value": button.label
        }

def make_text_field(label: str):
  return {
      "type":"plain_text",
      "text": label,
      "emoji":True
  }

def make_channel_field(input: actions.ActionChannelInput):
  return {
      "type": "input",
      "block_id": input.action,
      "element": {
        "type": "channels_select",
        "placeholder": make_text_field(input.placeholder),
        "action_id": input.action,
      },
      "label": {
          "type": "plain_text",
          "text": input.label,
          "emoji": True
      }
  }
def make_input_field(input: actions.ActionInput, initial_value: str = ''):
  return {
      "type": "input",
      "block_id": input.action,
      "element": {
        "type": "plain_text_input",
        "placeholder": make_text_field(input.placeholder),
        "action_id": input.action,
        "initial_value": initial_value or '',
      },
      "optional": input.optional,
      "label": {
          "type": "plain_text",
          "text": input.label,
          "emoji": True
      }
  }

def make_radio_button_input(input: actions.ActionRadioButtons):
  return {
      "type": "input",
      "block_id": input.action,
      "element": {
        "type": "radio_buttons",
        "options": [ make_radio_button(b) for b in input.options ],
        "action_id": input.action,
      },
      "label": {
          "type": "plain_text",
          "text": input.label,
          "emoji": True
      }
  }

def make_radio_button(input: actions.ActionRadioButton):
  return {
    "text": make_text_field(input.label),
    "value": input.value
  }
