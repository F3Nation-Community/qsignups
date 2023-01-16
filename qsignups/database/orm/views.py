from datetime import datetime
from sqlalchemy import *
from qsignups.database.orm import AO
from sqlalchemy.dialects.mysql import LONGTEXT

from . import BaseClass, QSignupClass

class vwWeeklyEvents(BaseClass, QSignupClass):
  __tablename__ = "vw_weekly_events"
  id = Column("id", Integer, primary_key = True)
  ao_channel_id = Column("ao_channel_id", String(255))
  event_day_of_week = Column("event_day_of_week", String(255))
  event_time = Column("event_time", String(45))
  event_end_time = Column("event_end_time", String(255))
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
  current_month_weinke = Column("current_month_weinke", LONGTEXT)
  created = Column('created', DateTime, default = datetime.utcnow)
  updated = Column('updated', DateTime, default = datetime.utcnow)

  def get_id(self):
    return self.id

  def get_id():
    return vwAOsSort.id

