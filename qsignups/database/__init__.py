from dataclasses import dataclass
from typing import List

import os
import mysql.connector
from sqlalchemy import create_engine, pool
from sqlalchemy.orm import sessionmaker
from contextlib import ContextDecorator

@dataclass
class DatabaseField:
    name: str
    value: object = None

DATABASE_HOST = 'DATABASE_HOST'
ADMIN_DATABASE_USER = 'ADMIN_DATABASE_USER'
ADMIN_DATABASE_PASSWORD = 'ADMIN_DATABASE_PASSWORD'
ADMIN_DATABASE_SCHEMA = 'ADMIN_DATABASE_SCHEMA'

GLOBAL_ENGINE = None
GLOBAL_SESSION = None
def get_session(echo = False):
    if GLOBAL_SESSION:
        return GLOBAL_SESSION

    global GLOBAL_ENGINE
    if not GLOBAL_ENGINE:

        host = os.environ[DATABASE_HOST]
        user = os.environ[ADMIN_DATABASE_USER]
        passwd = os.environ[ADMIN_DATABASE_PASSWORD]
        database = os.environ[ADMIN_DATABASE_SCHEMA]

        db_url = f"mysql+pymysql://{user}:{passwd}@{host}:3306/{database}?charset=utf8mb4"
        GLOBAL_ENGINE = create_engine(
            db_url, echo = echo, poolclass = pool.NullPool, convert_unicode = True)
    return sessionmaker()(bind=GLOBAL_ENGINE)

def close_session(session):
    global GLOBAL_SESSION, GLOBAL_ENGINE
    if GLOBAL_SESSION == session:
        if GLOBAL_ENGINE:
            GLOBAL_ENGINE.close()
            GLOBAL_SESSION = None


class DbManager:
    def get_record(service_class, id):
      session = get_session()
      try:
        return service_class(session).get_record(id)
      finally:
        session.rollback()
        close_session(session)

    def update_record(service_class, id, record):
      session = get_session()
      try:
        return service_class(session).update_record_by_orm(id, record)
      finally:
        session.commit()
        close_session(session)

    def create_record(service_class, record):
      session = get_session()
      try:
        return service_class(session).create_record(record)
      finally:
        session.commit()
        close_session(session)

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
