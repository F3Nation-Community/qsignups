
from typing import List
from . import my_connect, DatabaseField, insert_clause, select_clause, update_clause

def get_region(logger, team_id, fields: List[DatabaseField] = []):
  try:
      with my_connect(team_id) as mydb:
          regions_sql = f"SELECT {select_clause(fields)} FROM {mydb.db}.qsignups_regions WHERE team_id = '{team_id}';"
          mycursor = mydb.conn.cursor()
          mycursor.execute(regions_sql)
          regions = mycursor.fetchone()
          return regions
  except Exception as e:
      logger.error(f"Error pulling region info: {e}")
      print(e)

def add_region(logger, team_id, fields: List[DatabaseField]):
  try:
      inserts = insert_clause(fields + [DatabaseField(name = 'team_id', value = team_id)])
      with my_connect(team_id) as mydb:
        sql_insert = f"INSERT INTO {mydb.db}.qsignups_regions {inserts};"
        mycursor = mydb.conn.cursor()
        mycursor.execute(sql_insert)
        mycursor.execute("COMMIT;")
  except Exception as e:
      logger.error(f"Error creating region info: {e}")
      print(e)

def update_region(logger, team_id, fields: List[DatabaseField]):
  try:
      with my_connect(team_id) as mydb:
        sql_update = f"UPDATE {mydb.db}.qsignups_regions SET {update_clause(fields)} WHERE team_id = '{team_id}';"
        mycursor = mydb.conn.cursor()
        mycursor.execute(sql_update)
        mycursor.execute("COMMIT;")
  except Exception as e:
      logger.error(f"Error creating region info: {e}")
      print(e)
