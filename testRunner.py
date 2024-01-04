import pandas as pd

def read_check(addresses,data):
  data_frame = pd.read_csv(data)
  here = []
  for address in data['Address']:
    if address in addresses:
      here.append(address)
    else:
      continue

  return here
