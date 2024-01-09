import numpy as np
import pandas as pd
import requests
import streamlit as st
import json
import requests

@st.cache_data
def classify(voting_data,round_status):
    if round_status == 'Active':
        cosine_response = requests.get(f"https://raw.githubusercontent.com/G-r-ay/Arbitrum-QA-Dashboard/main/review_db/{st.session_state.round_id}/cosine_clusters.json")
        cosine_cluster_dict = json.loads(cosine_response.text)
        cosine_mask = voting_data['voter'].str.upper().isin([item.upper() for sublist in cosine_cluster_dict.values() for item in (sublist if isinstance(sublist, list) else [sublist])])

        recycling_response = requests.get(f"https://raw.githubusercontent.com/G-r-ay/Arbitrum-QA-Dashboard/main/review_db/{st.session_state.round_id}/recycle_clusters.json")
        recycling_cluster_dict = json.loads(recycling_response.text)
        recycling_mask = voting_data['voter'].str.upper().isin([item.upper() for sublist in recycling_cluster_dict.values() for item in (sublist if isinstance(sublist, list) else [sublist])])

        db =pd.read_parquet("https://raw.githubusercontent.com/G-r-ay/Arbitrum-QA-Dashboard/main/main_db.parquet")
        
        db = db[db['entry_status'] == 'Old']
        db_addresses = db['address'].str.upper().to_list()
        Reoccuring_mask = voting_data['voter'].str.upper().isin(db_addresses)
        voting_data['Threat Type'] = 'Normal'
        
        voting_data['Threat Type'] = np.where(cosine_mask, 'Script Bot', voting_data['Threat Type'])
        voting_data['Threat Type'] = np.where(recycling_mask, 'Recycler', voting_data['Threat Type'])
        voting_data['Threat Type'] = np.where(Reoccuring_mask, 'Reoccuring Threat', voting_data['Threat Type'])
        return voting_data
    else:
        db =pd.read_parquet("https://raw.githubusercontent.com/G-r-ay/Arbitrum-QA-Dashboard/main/main_db.parquet")
        threat_dict = dict(zip(db['address'], db['Threat Type']))
        voting_data['Threat Type'] = voting_data['voter'].map(threat_dict).fillna('Normal')
        return voting_data
