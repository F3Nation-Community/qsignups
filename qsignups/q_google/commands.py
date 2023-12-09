from dataclasses import dataclass
from typing import List
from . import authenticate, calendar

@dataclass
class GoogleResponse:
  success: bool
  message: str
  context: object = None

class GoogleCommand:
  def __init__(self, action, team_id):
    self.action = action
    self.team_id = team_id

  def execute(self, context, respond) -> GoogleResponse:
    msg = f"Command {self.action} is not implemented"
    if respond:
      respond(msg)
    return GoogleResponse(success = False, message = msg)

class ListCommand(GoogleCommand):
  def execute(self, context, respond):
    calendars = calendar.get_calendars(self.team_id)
    entries = [x['summary'] for x in calendars['items']]
    response = GoogleResponse(
      success = True,
      message = "Your calendars: \n" + "\n".join(entries),
      context = calendars)
    if respond:
      respond(response.message)
    return response

class ConnectedCommand(GoogleCommand):
  def execute(self, context, respond):
    connected = authenticate.is_connected(self.team_id)
    response = GoogleResponse(
      success = True,
      message = "Connected" if connected else "Not Connected",
      context = connected
      )
    if respond:
      respond(response.message)
    return response

class ConnectCommand(GoogleCommand):
  def execute(self, context, respond):
    if authenticate.connect(self.team_id):
      response = GoogleResponse(success = True, message = "Connected")
    else:
      response = GoogleResponse(success = False, message = "Unable to connect")
    if respond:
      respond(response.message)
    return response

class DisconnectCommand(GoogleCommand):
  def execute(self, context, respond):
    if authenticate.disconnect(self.team_id):
      response = GoogleResponse(success = True, message = "Disconnected")
    else:
      response = GoogleResponse(success = False, message = "Unable to disconnect")
    if respond:
      respond(response.message)
    return response

CONNECT_COMMAND = "connect"
DISCONNECT_COMMAND = "disconnect"
LIST_COMMAND = "list"
CONNECTED_COMMAND = "connected"

COMMAND_CLASSES = {
  CONNECTED_COMMAND: ConnectedCommand,
  DISCONNECT_COMMAND: DisconnectCommand,
  CONNECT_COMMAND: ConnectCommand,
  LIST_COMMAND: ListCommand,
}

def get_command(action, team_id):
  if COMMAND_CLASSES.get(action):
    return COMMAND_CLASSES[action](action, team_id)
  else:
    return GoogleCommand(action, team_id)

def execute_command(action, team_id, context = None, respond = None) -> GoogleResponse:
  return get_command(action, team_id).execute(context, respond)
