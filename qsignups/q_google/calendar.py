from datetime import datetime, timedelta
import pytz

from utilities import User
from database.orm import Master, Region, AO
from .authenticate import connect
from . import GoogleCalendar

from googleapiclient.discovery import build

MAX_SCHEDULE_LOOKAHEAD_DAYS = 30

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

def schedule_event(team_id, user: User, region: Region, event: Master, ao: AO):

  svc = get_calendar_service(team_id)
  if svc:
    return __create_event(svc, user, region, event, ao)
  else:
    return None

def __create_event(svc, user: User, region: Region, event: Master, ao: AO):
  if not region.google_calendar_id:
    return None

  if not event.event_end_time:
    return None

  if not event.google_event_id and __is_too_far_in_the_future(region, event):
    return None

  body = {
    'summary': __event_title(user, event, ao),
    'description': __event_description(user, event, ao),
    'start': {
      'dateTime': __google_date_time(region, event.event_date, event.event_time),
      'timeZone': region.timezone
    },
    'end':  {
      'dateTime': __google_date_time(region, event.event_date, event.event_end_time),
      'timeZone': region.timezone
    },
    'attendees': [],
    'reminders': {
      'overrides': [
        {
          'minutes': 1440,
          'method': 'email'
        }
      ],
      'useDefault': False
    }
  }
  if user:
    body['attendees'].append({
      'email': user.email
    })

  if event.google_event_id:
    print("UPDATING", body)
    return svc.events().patch(calendarId = region.google_calendar_id, eventId = event.google_event_id, body = body).execute()
  else:
    print("CREATING", body)
    return svc.events().insert(calendarId = region.google_calendar_id, body = body).execute()

def __is_too_far_in_the_future(region: Region, event: Master) -> bool:
  event_time = __event_date_time(region, event.event_date, event.event_time)
  max_to_schedule = datetime.utcnow() + timedelta(days = MAX_SCHEDULE_LOOKAHEAD_DAYS)
  tzinfo = pytz.timezone(region.timezone)
  return event_time > tzinfo.localize(max_to_schedule)

def __event_title(user: User, event: Master, ao: AO):
  if user:
    return f"{ao.ao_display_name} - Q'd by {user.name}"
  else:
    return f"{ao.ao_display_name} - Needs a Q"

def __event_description(user: User, event: Master, ao: AO):
  parts = [
    f"<strong>{ao.ao_display_name}</strong> {event.event_type}"
  ]
  parts.append(ao.ao_location_subtitle)
  parts.append(f"From {__clock_time(event.event_time)} to {__clock_time(event.event_end_time)}")
  if user:
    parts.append(f"Q'd by {user.name}")
  else:
    parts.append("Why don't you sign up to Q?")
  return f"""<ul>{"".join([f"<li>{x}</li>" for x in parts if x])}"""

def __clock_time(time_string):
  hh = time_string[0:2]
  mm = time_string[2:4]
  return f"{hh}:{mm}"

def __event_date_time(region: Region, date, time_string):
  hh = time_string[0:2]
  mm = time_string[2:4]

  tzinfo = pytz.timezone(region.timezone)
  naive_dt = datetime(year = date.year, month = date.month, day = date.day, hour = int(hh), minute = int(mm))

  return tzinfo.localize(naive_dt)

def __google_date_time(region: Region, date, time_string):
  return __event_date_time(region, date, time_string).strftime(format = '%Y-%m-%dT%H:%M:%S%z')
