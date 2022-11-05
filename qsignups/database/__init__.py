import os
import mysql.connector
from contextlib import ContextDecorator

DATABASE_HOST = 'DATABASE_HOST'
ADMIN_DATABASE_USER = 'ADMIN_DATABASE_USER'
ADMIN_DATABASE_PASSWORD = 'ADMIN_DATABASE_PASSWORD'
ADMIN_DATABASE_SCHEMA = 'ADMIN_DATABASE_SCHEMA'

# Construct class for connecting to the db
# Takes team_id as an input, pulls schema name from paxminer.regions
class my_connect(ContextDecorator):
    def __init__(self, team_id):
        self.conn = ''
        self.team_id = team_id
        self.db = ''

    def __enter__(self):
        self.conn = mysql.connector.connect(
            host=os.environ[DATABASE_HOST],
            user=os.environ[ADMIN_DATABASE_USER],
            passwd=os.environ[ADMIN_DATABASE_PASSWORD],
            database=os.environ[ADMIN_DATABASE_SCHEMA]
        )

        # sql_select = f'SELECT schema_name, user, password FROM paxminer.regions WHERE team_id = {self.team_id};'

        # with self.conn.cursor() as mycursor:
        #     mycursor.execute(sql_select)
        #     db, user, password = mycursor.fetchone()
        db = os.environ['ADMIN_DATABASE_SCHEMA']

        self.db = db
        return self

    def __exit__(self, *exc):
        self.conn.close()
        return False
