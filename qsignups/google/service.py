from googleapiclient.discovery import build

from .authenticate import connect

def get_calendar_service(team_id):
  creds = connect(team_id)
  if creds:
    service = build('calendar', 'v3', credentials=creds)
    return service
  else:
    return None