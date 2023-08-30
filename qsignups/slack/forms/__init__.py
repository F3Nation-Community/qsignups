from slack import inputs

def make_action_button_row(buttons):
  return {
      "type":"actions",
      "elements":[ b.as_form_field() for b in buttons ]
  }

def make_section_header_row(text: str):
  return {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": text
            }
        }

def make_header_row(text: str, accessory: inputs.ActionInput = None):
  j = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": text
        }
      }
  if accessory:
    j["accessory"] = accessory.as_form_field()
  return j

def make_divider():
  return  {
      "type": "divider"
  }

def make_context_row(context):
  return {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": context
                }
            ]
        }
