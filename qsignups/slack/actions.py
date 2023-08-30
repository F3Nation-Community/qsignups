from typing import List
from dataclasses import dataclass
import utilities

CANCEL_BUTTON_ACTION = "cancel_button_select"
EDIT_EVENT_ACTION = "submit_edit_event_button"
ADD_RECURRING_EVENT_ACTION = "submit_add_recurring_event_button"
ADD_SINGLE_EVENT_ACTION = "submit_add_single_event_button"
ADD_AO_ACTION = "submit_add_ao_button"
EDIT_AO_ACTION = "submit_edit_ao_button"
MANAGE_SCHEDULE_ACTION = "manage_schedule_button"
EDIT_SETTINGS_ACTION = "submit_general_settings"
REFRESH_ACTION = "refresh_home"
DELETE_RECURRING_SELECT_ACTION = "delete_recurring_event_slot_select"
SELECT_SLOT_EDIT_RECURRING_EVENT_FORM = "edit_recurring_event_slot_select"
EDIT_RECURRING_EVENT_ACTION = "submit_edit_recurring_event"
DELETE_AO_SELECT_ACTION = "delete_ao_select"
DELETE_AO_ACTION = "submit_delete_ao"
EDIT_SINGLE_EVENT_AO_SELECT = "edit_event_ao_select"
EDIT_RECURRING_EVENT_AO_SELECT = "edit_recurring_event_ao_select"
DELETE_RECURRING_EVENT_AO_SELECT = "delete_recurring_event_ao_select"