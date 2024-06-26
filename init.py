import requests
import dill
import os
import pandas as pd

API_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
DATA_PATH = os.curdir
FILENAME = "cards.pkl"

def save_card_data() -> bool:
  response = requests.get(API_URL)
  cards = response.json() if response.status_code == 200 else None
  if cards is None: return False
  data = cards['data']
  with open(DATA_PATH + FILENAME, "wb") as file:
    dill.dump(data, file)
  return True

def load_dataframe() -> pd.DataFrame:
  path = DATA_PATH + FILENAME
  
  if os.path.isfile(path):
    with open(path, "rb") as file:
      data = dill.load(file)
      df = pd.DataFrame(data)
      return df
  else: 
    return None