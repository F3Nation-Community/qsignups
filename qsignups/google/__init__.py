import os

def is_enabled():
  return os.environ.get("GOOGLE_CLIENT_ID")
