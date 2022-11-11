from sqlalchemy import *
from sqlalchemy.dialects.mysql import LONGTEXT
from datetime import datetime
from . import BaseClass, BaseService

class Region(BaseClass):
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
  created = Column('updated', DateTime, default = datetime.utcnow)

  def get_id(self):
    return self.team_id

  def get_id():
    return Region.team_id

class RegionService(BaseService):
  orm_class = Region
  def __init__(self, session):
    super(__class__, self).__init__(session, __class__.orm_class)
