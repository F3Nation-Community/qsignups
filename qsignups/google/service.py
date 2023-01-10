from datetime import datetime, timedelta
import pytz

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

def __google_date_time(region: Region, date, time, timedelta = 0):
  hh = time[0:2]
  mm = time[2:4]

  tzinfo = pytz.timezone(region.timezone)
  naive_dt = datetime(year = date.year, month = date.month, day = date.day, hour = int(hh), minute = int(mm))

  localized_dt = tzinfo.localize(naive_dt)
  return localized_dt.strftime(format = '%Y-%m-%dT%H:%M:%S%z')

def schedule_event(team_id, user, region: Region, event: Master):
  if not event.event_end_time:
    return
  svc = get_calendar_service(team_id)
  if svc:
    body = {
      'summary': 'QSignups Generated Event',
      'description': 'A testing description',
      'start': {
        'dateTime': __google_date_time(region, event.event_date, event.event_time),
        'timeZone': region.timezone
      },
      'end':  {
        'dateTime': __google_date_time(region, event.event_date, event.event_end_time),
        'timeZone': region.timezone
      },
      'attendees': [
        {
          'email': user.email
        }
      ]
    }
    print(f"Submitting {body}")
    x = svc.events().insert(calendarId = region.google_calendar_id, body = body).execute()
    print(x)

