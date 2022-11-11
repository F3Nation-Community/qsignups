class slButton:
    def __init__(self, text: str, action_id: str, value: str, style: str = "default") -> None:
        self.text = text
        self.action_id = action_id
        self.value = value
        self.style = style
        
    def to_json(self) -> dict:
        output_dict = {
            "type":"actions",
            "elements":[
                {
                    "type":"button",
                    "text":{
                        "type":"plain_text",
                        "text":self.text,
                        "emoji":True
                    },
                    "action_id":self.action_id,
                    "value":self.value
                }
            ]
        }
        
        if self.style != "default":
            output_dict["elements"][0]["style"] = self.style
        
        return output_dict
    
class slText:
    def __init__(self, text: str, text_type: str = "mrkdwn") -> None:
        self.text = text
        self.text_type = text_type
        
    def to_json(self) -> dict:
        output_dict = {
            "type":"section",
            "text":[
                {
                    "type":self.text_type,
                    "text":self.text
                }
            ]
        }
        
        return output_dict
    
class slTimepicker:
    def __init__(self, name: str, label_text: str, placeholder_text: str, initial_time: str) -> None:
        self.label_text = label_text
        self.placeholder_text = placeholder_text
        self.initial_time = initial_time
        self.name = name
        
    def to_json(self) -> dict:
        output_dict = {
            "type": "input",
            "block_id": f"slbtn|{self.name}",
            "element": {
                "type": "timepicker",
                "initial_time": self.initial_time,
                "placeholder": {
                    "type": "plain_text",
                    "text": self.placeholder_text,
                    "emoji": True
                },
                "action_id": "slbtn_name"
            },
            "label": {
                "type": "plain|{self.name}",
                "text": self.label_text,
                "emoji": True
            }
        }
        
        return output_dict
    
class slTextInput:
    def __init__(self, name: str, label_text: str, placeholder_text: str, initial_value: str, optional: bool = False) -> None:
        self.label_text = label_text
        self.placeholder_text = placeholder_text
        self.initial_value = initial_value
        self.optional = optional
        self.name = name
        
    def to_json(self) -> dict:
        output_dict = {
            "type": "input",
            "block_id": f"slinp|{self.name}",
            "element": {
                "type": "plain_text_input",
                "initial_value": self.initial_value,
                "placeholder": {
                    "type": "plain_text",
                    "text": self.placeholder_text,
                    "emoji": True
                },
                "action_id": f"slinp|{self.name}"
            },
            "label": {
                "type": "plain_text",
                "text": self.label_text,
                "emoji": True
            },
            "optional": self.optional
        }
        
        return output_dict
    
class slDropdownInput:
    def __init__(self, name: str, label_text: str, placeholder_text: str, options_list: list, initial_option_index: int) -> None:
        self.label_text = label_text
        self.placeholder_text = placeholder_text
        self.options_list = options_list
        self.initial_option_index = initial_option_index
        self.name = name
        
    def to_json(self) -> dict:
        options = []
        for option in self.options_list:
            new_option = {
                "text": {
                    "type": "plain_text",
                    "text": option,
                    "emoji": True
                },
                "value": option
            }
            options.append(new_option)
        
        output_dict = {
            "type": "input",
            "block_id": f"slddi|{self.name}",
            "element": {
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": self.placeholder_text,
                    "emoji": True
                },
                "action_id": f"slddi|{self.name}",
                "options": options,
                "initial_option": options[self.initial_option_index]
            },
            "label": {
                "type": "plain_text",
                "text": self.label_text,
                "emoji": True
            }
        }
        
        return output_dict
    
class slDatepicker:
    def __init__(self, name: str, label_text: str, placeholder_text: str, initial_date: str) -> None:
        self.label_text = label_text
        self.placeholder_text = placeholder_text
        self.initial_date = initial_date
        self.name = name
        
    def to_json(self) -> dict:
        
        output_dict = {
            "type": "input",
            "block_id": f"sldtp|{self.name}",
            "element": {
                "type": "datepicker",
                "placeholder": {
                    "type": "plain_text",
                    "text": self.placeholder_text,
                    "emoji": True
                },
                "action_id": f"sldtp|{self.name}",
                "initial_date": self.initial_date
            },
            "label": {
                "type": "plain_text",
                "text": self.label_text,
                "emoji": True
            }
        }
        
        return output_dict
    
class slRadioButtonInput:
    def __init__(self, name: str, label_text: str, options_dict: dict, initial_option_index: int) -> None:
        self.label_text = label_text
        self.options_dict = options_dict
        self.initial_option_index = initial_option_index
        self.name = name
        
    def to_json(self) -> dict:
        options = []
        for option in self.options_dict.items():
            new_option = {
                "text": {
                    "type": "plain_text",
                    "text": option[0],
                    "emoji": True
                },
                "value": option[1]
            }
            options.append(new_option)
        
        output_dict = {
            "type": "input",
            "block_id": f"slrbi|{self.name}",
            "element": {
                "type": "radio_buttons",
                "action_id": f"slrbi|{self.name}",
                "options": options,
                "initial_option": options[self.initial_option_index]
            },
            "label": {
                "type": "plain_text",
                "text": self.label_text,
                "emoji": True
            }
        }
        
        return output_dict
    
class slChannelSelect:
    def __init__(self, name: str, label_text: str, placeholder_text: str, initial_channel: str) -> None:
        self.label_text = label_text
        self.initial_channel = initial_channel
        self.placeholder_text = placeholder_text
        self.name = name
        
    def to_json(self) -> dict:
        
        output_dict = {
            "type": "input",
            "block_id": f"slchn|{self.name}",
            "element": {
                "type": "channels_select",
                "action_id": f"slchn|{self.name}",
                "placeholder": {
                    "type": "plain_text",
                    "text": self.placeholder_text,
                    "emoji": True
                },
                "initial_channel": self.initial_channel
            },
            "label": {
                "type": "plain_text",
                "text": self.label_text,
                "emoji": True
            }
        }
        
        return output_dict
    
btn1 = slButton("Hello, world!", "runthis", "money")
btn1.to_json()

txt1 = slText("Hello, world!")
txt1.to_json()

txtinp1 = slTextInput("field1", "Enter something here!", "Example Text", "Example Text", False)
txtinp1.to_json()

ddi = slDropdownInput("DayOptions", "Pick a Day of the Week:", "Day of the Week", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], 2)
ddi.to_json()

dtp = slDatepicker("StartDate", "Pick a start date:", "Date", "2022-10-22")
dtp.to_json()

rbi = slRadioButtonInput("q_reminder_enable", "Enable Q Reminders?", {'Enable Q reminders': 'enable', 'Disable Q reminders': 'disable'}, 0)
rbi.to_json()

chn = slChannelSelect("weinke_channel_select", "Public channel for posting weekly schedules:", "Select a channel", "ao-forge")
chn.to_json()
