import os

USE_WEINKES = 'USE_WEINKES'
def use_weinkes() -> bool:
  return os.environ.get(USE_WEINKES)

SCHEDULE_CREATE_LENGTH_DAYS = 365
