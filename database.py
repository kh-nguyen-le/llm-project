import init
import sys
import pandas as pd
import sqlalchemy

TABLE_NAME = "Cards"

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
  df = df.drop(columns=['card_sets', 'card_images', 'card_prices', 'pend_desc', 'monster_desc', 'linkmarkers', 'banlist_info'])
  df = df.astype({
      'typeline': 'str'
  },
  errors='ignore')
  engine = sqlalchemy.create_engine("sqlite+pysqlite:///:memory:", echo=True)
  metadata_obj = sqlalchemy.MetaData()
  table = sqlalchemy.Table(TABLE_NAME, metadata_obj,
                           sqlalchemy.Column("index", sqlalchemy.Integer, primary_key=True),
                           sqlalchemy.Column("id", sqlalchemy.Integer),
                           sqlalchemy.Column("name", sqlalchemy.String),
                           sqlalchemy.Column('type', sqlalchemy.String),
                           sqlalchemy.Column("humanReadableCardType", sqlalchemy.String),
                           sqlalchemy.Column("frameType", sqlalchemy.String),
                           sqlalchemy.Column("desc", sqlalchemy.String),
                           sqlalchemy.Column("race", sqlalchemy.String),
                           sqlalchemy.Column("archetype", sqlalchemy.String),
                           sqlalchemy.Column("ygoprodeck_url", sqlalchemy.String),
                           sqlalchemy.Column("typeline", sqlalchemy.String),
                           sqlalchemy.Column("atk", sqlalchemy.Integer),
                           sqlalchemy.Column("def", sqlalchemy.Integer),
                           sqlalchemy.Column("level", sqlalchemy.Integer),
                           sqlalchemy.Column("scale", sqlalchemy.Integer),
                           sqlalchemy.Column("linkval", sqlalchemy.Integer),
                           sqlalchemy.Column("attribute", sqlalchemy.String),
                           )
  metadata_obj.create_all(engine)
  df.to_sql(TABLE_NAME, engine, if_exists='replace')
  return engine
