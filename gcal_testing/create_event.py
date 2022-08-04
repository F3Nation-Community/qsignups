from datetime import datetime, timedelta, date
from cal_setup import get_calendar_service
from pytz import timezone

import mysql.connector
from decouple import config, UndefinedValueError
import pandas as pd

# Configure mysql db
db_config = {
    "host":"f3stlouis.cac36jsyb5ss.us-east-2.rds.amazonaws.com",
    "user":config('DATABASE_USER'), 
    "password":config('DATABASE_WRITE_PASSWORD'),
    "database":config('DATABASE_SCHEMA') 
}

def main():
    # creates one hour event tomorrow 10 AM IST
    service = get_calendar_service()

    # SQL pull
    sql_pull = f"""
    SELECT *
    FROM schedule_master
    WHERE ao_channel_id = 'C025566LELF'
        AND event_date > DATE('{date.today()}')
        AND event_date <= DATE('{date.today() + timedelta(weeks=5)}');
    """
    with mysql.connector.connect(**db_config) as mydb:
        results_df = pd.read_sql_query(sql_pull, mydb, parse_dates=['event_date'])

    for index, row in results_df.iterrows():
        d = row['event_date']
        h = int(row['event_time'][:2])
        m = int(row['event_time'][2:])
        start = datetime(d.year, d.month, d.day, h, m).isoformat()
        end = (datetime(d.year, d.month, d.day, h, m)+timedelta(minutes=45)).isoformat()

        if row['q_pax_name'] is None:
            pax_label = 'OPEN!'
        else:
            pax_label = row['q_pax_name']

        event_label = f"{row['event_type']}: {pax_label}"

        event_result = service.events().insert(calendarId="stbei2pmic0i0emhat0ts39ql0@group.calendar.google.com",
            body={
                "summary": event_label,
                "description": 'Regularly scheduled beatdown',
                "start": {"dateTime": start, "timeZone": 'US/Central'},
                "end": {"dateTime": end, "timeZone": 'US/Central'},
            }
        ).execute()

        print("created event")
        print("id: ", event_result['id'])
        print("summary: ", event_result['summary'])
        print("starts at: ", event_result['start']['dateTime'])
        print("ends at: ", event_result['end']['dateTime'])

if __name__ == '__main__':
   main()

# tz = timezone('US/Central')

# d = datetime.now().date()
# tomorrow = tz.localize(datetime(d.year, d.month, d.day, 10)+timedelta(days=1))
# start = tomorrow.isoformat()
# end = (tomorrow + timedelta(hours=1)).isoformat()

# from datetime import datetime, timedelta
# from pytz import timezone
# import pytz
# utc = pytz.utc
# utc.zone

# eastern = timezone('US/Central')
# eastern.zone

# fmt = '%Y-%m-%d %H:%M:%S %Z%z'

# loc_dt = eastern.localize(datetime(2002, 10, 27, 6, 0, 0))
# print(loc_dt.strftime(fmt))
# loc_dt.isoformat()
