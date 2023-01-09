from googleapiclient.discovery import build

from qsignups.database.orm import Master, Region
from .authenticate import connect
from . import GoogleCalendar

def __to_calendar(j) -> GoogleCalendar:
  return GoogleCalendar(
    name = j['summary'],
    id = j['id'])

def get_calendars(team_id):
  svc = get_calendar_service(team_id)
  if svc:
    calendarList = svc.calendarList().list().execute()
    if calendarList:
      cals = calendarList['items']
      return [ __to_calendar(x) for x in cals ]
  return []

def get_calendar_service(team_id):
  creds = connect(team_id)
  if creds:
    service = build('calendar', 'v3', credentials=creds)
    return service
  else:
    return None

def schedule_event(team_id, region: Region, event: Master):
  svc = get_calendar_service(team_id)
  if svc:
    body = {
      'summary': 'QSignups Generated Event',
      'start': event.event_date
    }
    svc.events.insert(calendarId = region.google_calendar_id, body = body)
