import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base

from qsignups.database import DbManager

BaseClass = declarative_base(mapper=sqlalchemy.orm.mapper)

class QSignupClass:
  def get(self, attr):
    if attr in [c.key for c in self.__table__.columns]:
      return getattr(self, attr)
    return None

  def to_json(self):
    return {
      c.key:  self.get(c.key) for c in self.__table__.columns
    }

  def __repr__(self):
    return str(self.to_json())

class BaseService:
  __session = None
  __orm_class = None

  def __init__(self, session, orm_cls):
    self.__session = session
    self.__orm_class = orm_cls

  @property
  def session(self):
    return self.__session

  @property
  def orm_class(self):
    return self.__orm_class

  def get_record(self, id):
    return self.session.query(self.orm_class).filter(self.orm_class.get_id() == id).first()

  def create_record(self, orm_object):
    self.session.add(orm_object)
    self.session.flush()
    return orm_object.id

  def update_record(self, id, values):
    response = self.session.query(self.orm_class).filter(self.orm_class.get_id() == id).update(values, synchronize_session='fetch')
    self.session.flush()
    return response

  def update_record_by_orm(self, record_id, orm_object):
    """This method updates a record using an ORM Object. It only updates not null values. If you wish to set a null/empty value for a column then use update_record() method instead."""
    if record_id:
      values_to_update = {}
      for col in  orm_object.__table__.columns:
        if orm_object.get(col.name) is not None:
          values_to_update[col.name] = orm_object.get(col.name)
      return self.update_record(record_id, values_to_update)
    else:
      raise Exception("id is not present in the object.")


