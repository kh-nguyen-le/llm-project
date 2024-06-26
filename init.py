import requests
import dill
import os
import pandas as pd

API_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
DATA_PATH = os.curdir
FILENAME = "cards.pkl"
FILE_PATH = DATA_PATH + FILENAME

def save_card_data() -> bool:
  response = requests.get(API_URL)
  cards = response.json() if response.status_code == 200 else None
  if cards is None: return False
  data = cards['data']
  with open(FILE_PATH, "wb") as file:
    dill.dump(data, file)
  return True

def data_exists() -> bool:
  return True if os.path.isfile(FILE_PATH) else False

def load_dataframe() -> pd.DataFrame:
  if data_exists():
    with open(FILE_PATH, "rb") as file:
      data = dill.load(file)
      df = pd.DataFrame(data)
      return df
  else: 
    return None