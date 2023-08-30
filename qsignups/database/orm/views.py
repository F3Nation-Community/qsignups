from datetime import datetime
from sqlalchemy import *
from database.orm import AO
from sqlalchemy.dialects.mysql import LONGTEXT

from . import BaseClass, QSignupClass

class vwWeeklyEvents(BaseClass, QSignupClass):
  __tablename__ = "vw_weekly_events"
  id = Column("id", Integer, primary_key = True)
  ao_channel_id = Column("ao_channel_id", String(255))
  event_day_of_week = Column("event_day_of_week", String(255))
  event_time = Column("event_time", String(45))
  event_end_time = Column("event_end_time", String(255))
  event_type = Column("event_type", String(255))
  team_id = Column("team_id", String(100))
  ao_display_name = Column("ao_display_name", String(255))
  created = Column('created', DateTime, default = datetime.utcnow)
  updated = Column('updated', DateTime, default = datetime.utcnow)

  def get_id(self):
    return self.id

  def get_id():
    return vwWeeklyEvents.id
  
class vwAOsSort(BaseClass, QSignupClass):
  __tablename__ = "vw_aos_sort"
  id = Column("id", Integer, primary_key = True)
  team_id = Column("team_id", String(100))
  ao_channel_id = Column("ao_channel_id", String(255))
  ao_display_name = Column("ao_display_name", String(255))
  ao_location_subtitle = Column("ao_location_subtitle", String(255))
  current_month_weinke = Column("current_month_weinke", LONGTEXT)
  created = Column('created', DateTime, default = datetime.utcnow)
  updated = Column('updated', DateTime, default = datetime.utcnow)

  def get_id(self):
    return self.id

  def get_id():
    return vwAOsSort.id
  
class vwMasterEvents(BaseClass, QSignupClass):
  __tablename__ = "vw_master_events"
  id = Column("id", Integer, primary_key = True)
  ao_channel_id = Column("ao_channel_id", String(255))
  event_date = Column("event_date", Date)
  event_time = Column("event_time", String(255))
  event_end_time = Column("event_end_time", String(255))
  event_day_of_week = Column("event_day_of_week", String(255))
  event_type = Column("event_type", String(255))
  event_special = Column("event_special", String(255))
  event_recurring = Column("event_recurring", Integer)
  q_pax_id = Column("q_pax_id", String(255))
  q_pax_name = Column("q_pax_name", String(255))
  team_id = Column("team_id", String(100))
  google_event_id = Column("google_event_id", String(45))
  created = Column('created', DateTime, default = datetime.utcnow)
  updated = Column('updated', DateTime, default = datetime.utcnow)
  ao_display_name = Column("ao_display_name", String(255))
  ao_location_subtitle = Column("ao_location_subtitle", String(255))

  def get_id(self):
    return self.id

  def get_id():
    return vwMasterEvents.id

