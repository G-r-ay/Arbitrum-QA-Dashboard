# ----------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------
import time
import base64
import datetime
import requests
import pandas as pd
import streamlit as st
from json.decoder import JSONDecodeError
from requests.exceptions import ConnectionError, Timeout

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------
SLEEP_TIME = 0.5
MAX_RETRIES = 3

# ----------------------------------------------------------------------
# Function to get transaction history based on action (txlist or tokentx)
# ----------------------------------------------------------------------
def get_transaction_history(address, api_key, url, action, start_block=0, end_block=99999999):
    params = {
        "module": "account",
        "action": action,
        "address": address,
        "startblock": start_block,
        "endblock": end_block,
        "sort": "asc",
        "apikey": api_key,
    }

    response = requests.get(url, params=params).json()
    return response["result"]

# ----------------------------------------------------------------------
# Function to fetch data for an address
# ----------------------------------------------------------------------
def fetch(address, nested_list, url="", api_key=""):
    reg_hist = get_transaction_history(address, api_key, url, "txlist")
    erc20_hist = get_transaction_history(address, api_key, url, "tokentx")

    txn_count = len(reg_hist)

    reg_age = get_wallet_age(reg_hist)
    erc_age = get_wallet_age(erc20_hist)

    reg_to, reg_from, ratio_reg = 0, 0, 0.000
    erc_to, erc_from, ratio_erc = 0, 0, 0.000

    # Count transactions for regular history
    for transactions in reg_hist:
        if transactions["from"] == address:
            reg_from += 1
        else:
            reg_to += 1

    # Count transactions for ERC-20 history
    for transactions in erc20_hist:
        if transactions["from"] == address:
            erc_from += 1
        else:
            erc_to += 1

    # Calculate ratios
    if reg_from != 0:
        ratio_reg = round(reg_to / reg_from, 3)

    if erc_from != 0:
        ratio_erc = round(erc_to / erc_from, 3)

    # Get additional transaction history details
    trasacting_hist = first_last_info(reg_hist, address)

    # Create a row with all gathered information
    row = [
        address,
        txn_count,
        reg_age,
        erc_age,
        reg_to,
        reg_from,
        erc_to,
        erc_from,
        ratio_reg,
        ratio_erc,
    ] + trasacting_hist
    nested_list.append(row)

# ----------------------------------------------------------------------
# Function to get wallet age based on the transaction history
# ----------------------------------------------------------------------
def get_wallet_age(history):
    if len(history) > 0:
        creation_time = int(history[0]["timeStamp"])
        creation_date = datetime.datetime.fromtimestamp(creation_time).date()
        current_date = datetime.date.today()
        wallet_age = (current_date - creation_date).days
        return wallet_age
    else:
        return 0

# ----------------------------------------------------------------------
# Function to get first and last transaction information
# ----------------------------------------------------------------------
def first_last_info(response, address):
    first_date = response[0]["timeStamp"]
    last_date = response[-1]["timeStamp"]

    first_to = response[0]["to"]
    first_from = response[0]["from"]

    last_to = response[-1]["to"]
    last_from = response[-1]["from"]

    first_out_amount = None
    last_out_amount = None

    for transaction in response:
        if transaction["from"].lower() == address.lower():
            value = int(transaction["value"]) / 10**18  # Convert wei to ether
            if first_out_amount is None:
                first_out_amount = value
            last_out_amount = value

    # Check if the first and last transactions involve 'self'
    if first_to == address:
        first_to = "self"
    if first_from == address:
        first_from = "self"
    if last_to == address:
        last_to = "self"
    if last_from == address:
        last_from = "self"

    first_in_amount = None
    last_in_amount = None

    for transaction in response:
        if transaction["to"].lower() == address.lower():
            value = int(transaction["value"]) / 10**18  # Convert wei to ether
            if first_in_amount is None:
                first_in_amount = value
            last_in_amount = value

    # Return a list with first and last transaction details
    return [
        first_date,
        last_date,
        first_from,
        first_to,
        last_from,
        last_to,
        first_out_amount,
        last_out_amount,
        first_in_amount,
        last_in_amount,
    ]

# ----------------------------------------------------------------------
# Function to get user data for a specific round
# ----------------------------------------------------------------------
def get_user_data(round_id: str):
    chain_id = 42161
    api_key = st.secrets["ARB_SCAN_KEY"]
    url = "https://api.arbiscan.io/api"
    headers = [
        "voter",
        "txn_count",
        "Wallet_Age",
        "Wallet_Age(Erc20)",
        "to_count",
        "from_count",
        "erc_to",
        "erc_from",
        "in-out_ratio",
        "in-out_ratio_erc",
        "first_date",
        "last_date",
        "first_from",
        "first_to",
        "last_from",
        "last_to",
        "first_out_amount",
        "last_out_amount",
        "first_in_amount",
        "last_in_amount",
    ]

    # Read contributors for the specified round
    contributors = set(pd.read_json(
        f"https://grants-stack-indexer.gitcoin.co/data/{chain_id}/rounds/{round_id}/contributors.json"
    )["id"])
    contents = []
    failed_addresses = []
    count = 0
    percentage_done = 0
    stored_contributer_features = pd.read_parquet(f'https://raw.githubusercontent.com/G-r-ay/Arbitrum-QA-Dashboard/main/round_user_info/{round_id}.parquet')
    
    new_addresses = (contributors-set(stored_contributer_features['voter']))
    num_address = len(new_addresses)
    if num_address == 0:
        print("no new contributers")
    else:
        my_bar = st.progress(0, text="Getting Voter data")
        for address in new_addresses:
            my_bar.progress(int(percentage_done), text="Getting Voter data")
            count += 1
            retries = 0
            if count % 5 == 0:
                time.sleep(SLEEP_TIME)
            while retries < MAX_RETRIES:
                try:
                    fetch(address, contents, url, api_key)
                    break
                except (ConnectionError, Timeout, JSONDecodeError, IndexError) as e:
                    print(f"Failed to fetch data for {address}: Error Type {e}")
                    retries += 1
                    if retries >= MAX_RETRIES:
                        failed_addresses.append(address)
                        break
            percentage_done =int((count / num_address) * 100)

            percentage_done = (count / num_address) * 100
        update_df = pd.DataFrame(contents, columns=headers)
        stored_contributer_features = pd.concat([stored_contributer_features,update_df])
        modified_content = stored_contributer_features.to_parquet(index=False)
        modified_content_encoded = base64.b64encode(modified_content).decode()

        api_url = f'https://api.github.com/repos/G-r-ay/Arbitrum-QA-Dashboard/contents/round_user_info/{round_id}.parquet'

        headers = {
            "Authorization": f'Bearer {st.secrets["ACCESS_TOKEN"]}'
        }

        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            file_info = response.json()
            payload = {
                "message": "Update Parquet file",
                "content": modified_content_encoded,
                "sha": file_info["sha"]
            }

            update_response = requests.put(api_url, json=payload, headers=headers)
            if update_response.status_code == 200:
                print("user data parquet updated successfully.")
            else:
                print("Error updating file:", update_response.text)
        my_bar.empty()
