# Helper methods for common Db access
from dataclasses import dataclass
from datetime import datetime

from qsignups.database import DbManager
from qsignups.database.orm import Master, AO

def find_ao(team_id, ao_channel_id = None, ao_display_name = None) -> AO:
  aos = []
  if ao_display_name:
    aos = DbManager.find_records(AO, [
        AO.team_id == team_id,
        AO.ao_display_name == ao_display_name
    ])
  elif ao_channel_id:
    aos = DbManager.find_records(AO, [
        AO.team_id == team_id,
        AO.ao_channel_id == ao_channel_id
    ])

  if len(aos) != 1:
    return None
  else:
    return aos[0]

@dataclass
class MasterEventAndAO:
  ao: AO
  event: Master

def find_master_event(team_id, selected_dt, ao_display_name = None, ao_channel_id = None) -> MasterEventAndAO:

  ao: AO = find_ao(team_id, ao_channel_id = ao_channel_id, ao_display_name = ao_display_name)
  if not ao:
    print(f"MASTER_LOOKUP_ERROR: {team_id}/{ao_display_name} could not find an AO")
    return None

  selected_date_db = datetime.date(selected_dt).strftime('%Y-%m-%d')
  selected_time_db = datetime.time(selected_dt).strftime('%H%M')

  masters = DbManager.find_records(Master, {
      Master.ao_channel_id == ao.ao_channel_id,
      Master.event_date == selected_date_db,
      Master.event_time == selected_time_db
  })
  if len(masters) == 1:
    return MasterEventAndAO(ao = ao, event = masters[0])
  else:
    print(f"MASTER_LOOKUP_ERROR: {ao_display_name}/{selected_date_db}/{selected_time_db} found {len(masters)} Masters")
    return None
