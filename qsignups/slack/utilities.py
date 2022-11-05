from qsignups import actions

def make_cancel_button():
  return make_button("Cancel", action_id = actions.CANCEL_BUTTON_ACTION)

def make_button(button_text, action_id):
  return {
      "type":"actions",
      "elements":[
          {
              "type":"button",
              "text":{
                  "type":"plain_text",
                  "text": button_text,
                  "emoji":True
              },
              "action_id": action_id,
              "value": button_text
          }
      ]
  }
