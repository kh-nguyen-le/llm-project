import init
import sys
import pandas as pd
import sqlalchemy

def create_database():
  if not init.data_exists():
    if init.save_card_data():
      return _create_database()
    else:
      sys.stderr.write("Error calling API")
      exit()
  else:
    return _create_database()

def _create_database():
  df = init.load_dataframe()
  if df is None:
    sys.stderr.write("Error unpickling")
    exit()
  df = df.drop(columns=['card_sets', 'card_images', 'card_prices', 'pend_desc', 'monster_desc', 'scale', 'linkval', 'linkmarkers', 'banlist_info'])
  engine = sqlalchemy.create_engine("sqlite+pysqlite:///:memory:", echo=True)
  df.to_sql('Cards', engine)
  return engine