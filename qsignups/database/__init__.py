from dataclasses import dataclass
from typing import TypeVar, List

import os
import mysql.connector
from sqlalchemy import create_engine, pool, and_
from sqlalchemy.orm import sessionmaker
from contextlib import ContextDecorator

from qsignups.database.orm import BaseClass

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

T = TypeVar('T')
class DbManager:

    def get_record(cls: T, id) -> T:
      session = get_session()
      try:
        return session.query(cls).filter(cls.get_id() == id).first()
      finally:
        session.rollback()
        close_session(session)

    def find_records(cls: T, filters) -> List[T]:
      session = get_session()
      try:
        return session.query(cls).filter(and_(*filters)).all()
      finally:
        session.rollback()
        close_session(session)

    def update_record(cls: T, id, fields):
      session = get_session()
      try:
        session.query(cls).filter(cls.get_id() == id).update(fields, synchronize_session='fetch')
        session.flush()
      finally:
        session.commit()
        close_session(session)

    def create_record(record: BaseClass) -> int:
      session = get_session()
      try:
          session.add(record)
          session.flush()
          return record.get_id()
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
