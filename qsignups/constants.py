import os

USE_WEINKES = 'USE_WEINKES'
def use_weinkes() -> bool:
  return os.environ.get(USE_WEINKES)

ADD_EVENT = 'Add an event'
EDIT_EVENT = 'Edit an event'

ADD_AO = 'Add an AO'
EDIT_AO = 'Edit an AO'
DELETE_AO = 'Delete an AO'

DELETE_SINGLE_EVENT = 'Delete a single event'
GENERAL_SETTINGS = 'General settings'
