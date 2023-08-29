from datetime import datetime
from enum import Enum
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import *
from sqlalchemy.types import JSON
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import relationship

BaseClass = declarative_base(mapper=sqlalchemy.orm.mapper)

class QSignupClass:

  def get_id(self):
    return self.id

  def get(self, attr):
    if attr in [c.key for c in self.__table__.columns]:
      return getattr(self, attr)
    return None

  def to_json(self):
    return {
      c.key:  self.get(c.key) for c in self.__table__.columns
    }

  def __repr__(self):
    return str(self.to_json())


class Region(BaseClass, QSignupClass):
  __tablename__ = "qsignups_regions"
  # TODO: Convert all of the ID for Region to id, not team_id
  team_id = Column("team_id", String(100),  primary_key = True)
  id = Column("id", Integer)
  current_week_weinke = Column("current_week_weinke", LONGTEXT)
  next_week_weinke = Column("next_week_weinke", LONGTEXT)
  bot_token = Column("bot_token", String(100))
  signup_reminders = Column("signup_reminders", Integer)
  weekly_weinke_channel = Column("weekly_weinke_channel", String(100))
  workspace_name = Column("workspace_name", String(100))
  current_week_weinke_updated = Column("current_week_weinke_updated", String(100))
  next_week_weinke_updated = Column("next_week_weinke_updated", String(100))
  weekly_ao_reminders = Column("weekly_ao_reminders", Integer)
  google_calendar_id = Column("google_calendar_id", String(100))
  google_auth_data = Column("google_auth_data", JSON)
  timezone = Column("timezone", String(45), default = 'America/New_York')
  created = Column('created', DateTime, default = datetime.utcnow)
  updated = Column('updated', DateTime, default = datetime.utcnow)

  def get_id(self):
    return self.team_id

  def get_id():
    return Region.team_id

class AO(BaseClass, QSignupClass):
  __tablename__ = "qsignups_aos"
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
    return AO.id

class Weekly(BaseClass, QSignupClass):
  __tablename__ = "qsignups_weekly"
  id = Column("id", Integer, primary_key = True)
  ao_channel_id = Column("ao_channel_id", String(255))
  event_day_of_week = Column("event_day_of_week", String(255))
  event_time = Column("event_time", String(45))
  event_end_time = Column("event_end_time", String(255))
  event_type = Column("event_type", String(255))
  team_id = Column("team_id", String(100))
  google_calendar_id = Column("google_calendar_id", String(100))
  created = Column('created', DateTime, default = datetime.utcnow)
  updated = Column('updated', DateTime, default = datetime.utcnow)

  def get_id(self):
    return self.id

  def get_id():
    return Weekly.id

class Master(BaseClass, QSignupClass):
  __tablename__ = "qsignups_master"
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

  def get_id(self):
    return self.id

  def get_id():
    return Master.id

class Feature(BaseClass, QSignupClass):
  __tablename__ = "qsignups_features"
  id = Column("id", Integer, primary_key = True)
  region_id = Column("region_id", Integer)
  feature = Column("feature", String(45))
  enabled = Column("enabled", Boolean)
  created = Column('created', DateTime, default = datetime.utcnow)
  updated = Column('updated', DateTime, default = datetime.utcnow)

  def get_id(self):
    return self.id

  def get_id():
    return Weekly.id

class SignupFeature(str, Enum):
  GOOGLE = 'google'
