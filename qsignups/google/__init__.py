import os
from dataclasses import dataclass

@dataclass
class GoogleCalendar:
  name: str
  id: str

  def __str__(self) -> str:
    return self.name

def is_enabled():
  return os.environ.get("GOOGLE_CLIENT_ID")
