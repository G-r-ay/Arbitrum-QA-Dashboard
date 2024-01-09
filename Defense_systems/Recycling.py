import requests
import time
import streamlit as st
import json
import time
import base64
from datetime import datetime

def track_recycling(grantAddresses,start_date,voter_addresses):

    recycled_addresses = {}
    count = 0
    for address in grantAddresses:
        count += 1
        if count % 5 == 0:
            time.sleep(1)
        params = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": 0,
            "endblock": 99999999,
            "sort": "asc",
            "apikey": st.secrets["ARB_SCAN_KEY"],
        }

        response = requests.get("https://api.arbiscan.io/api", params=params).json()["result"]
        inspect_point = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
        filtered_transactions = [transaction for transaction in response if int(transaction["timeStamp"]) >= inspect_point]

        unique_addresses_in_transactions = set()
        for transaction in filtered_transactions:
            unique_addresses_in_transactions.add(transaction["to"])

        recycled = list(set(voter_addresses) & unique_addresses_in_transactions)

        recycled_addresses[address] = recycled
    recycled_addresses = json.dumps(recycled_addresses,indent=2)
    encoded_data = base64.b64encode(recycled_addresses.encode()).decode()
    api_url = f'https://api.github.com/repos/G-r-ay/Arbitrum-QA-Dashboard/contents/review_db/{st.session_state.round_id}/recycle_clusters.json'
    github_token = st.secrets["ACCESS_TOKEN"]
    headers = {
        "Authorization": f"Bearer {github_token}"
    }

    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        file_info = response.json()
        payload = {
            "message": "Updated recycle_clusters.json",
            "content": encoded_data,
            "sha": file_info["sha"]
        }

        update_response = requests.put(api_url, json=payload, headers=headers)
        if update_response.status_code == 200:
            print("recycle_clusters.json updated successfully.")
