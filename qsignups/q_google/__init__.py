import os
from dataclasses import dataclass
from database.orm import SignupFeature, helper

@dataclass
class GoogleCalendar:
  name: str
  id: str

  def __str__(self) -> str:
    return self.name

def is_available(team_id):
  if os.environ.get("GOOGLE_CLIENT_ID"):
    return helper.feature_enabled(team_id, SignupFeature.GOOGLE)
  else:
    return False

