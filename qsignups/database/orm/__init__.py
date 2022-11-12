from datetime import datetime
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import *
from sqlalchemy.dialects.mysql import LONGTEXT

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
  current_week_weinke = Column("current_week_weinke", LONGTEXT)
  next_week_weinke = Column("next_week_weinke", LONGTEXT)
  team_id = Column("team_id", String(100),  primary_key = True)
  bot_token = Column("bot_token", String(100))
  signup_reminders = Column("signup_reminders", Integer)
  weekly_weinke_channel = Column("weekly_weinke_channel", String(100))
  workspace_name = Column("workspace_name", String(100))
  current_week_weinke_updated = Column("current_week_weinke_updated", String(100))
  next_week_weinke_updated = Column("next_week_weinke_updated", String(100))
  weekly_ao_reminders = Column("weekly_ao_reminders", Integer)
  google_calendar_id = Column("google_calendar_id", String(45))
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
  current_month_weinke = Column("current_month_weinke", LONGTEXT)
  created = Column('created', DateTime, default = datetime.utcnow)
  updated = Column('updated', DateTime, default = datetime.utcnow)

  def get_id(self):
    return self.team_id

  def get_id():
    return AO.team_id
