import numpy as np
import pandas as pd
import json
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
import json
import streamlit as st
import time
import requests
import base64
scaler = MinMaxScaler()

def cluster_addresses(feature_dataset, threshold=0.9995):
    address = set()
    data = scaler.fit_transform(np.array(feature_dataset[feature_dataset.columns[1:]]))

    voter = feature_dataset["voter"].values.reshape(-1, 1)
    data = np.hstack((voter, data))

    similarity_matrix = cosine_similarity(data[:, 1:])

    similar_rows = []

    assigned_voters = set()

    for i in range(len(similarity_matrix)):
        if data[i, 0] in assigned_voters:
            continue
        similar_row_indices = np.where(similarity_matrix[i] >= threshold)[0]
        if len(similar_row_indices) > 1:
            similar_row_values = [
                tuple(feature_dataset.iloc[j]) for j in similar_row_indices
            ]
            similar_rows.append(similar_row_values)
            assigned_voters.update(data[similar_row_indices, 0])

    similar_rows_json = {}

    for i, row_group in enumerate(similar_rows):
        cluster_group = []
        for row in row_group:
            cluster_group.append(row[0])
            if row[0] not in address:
                address.add(row[0])
        similar_rows_json[f"Cluster Group {i}"] = cluster_group

    similar_rows_json = json.dumps(similar_rows_json)
    encoded_data = base64.b64encode(similar_rows_json.encode()).decode()
    api_url = f'https://api.github.com/repos/G-r-ay/Arbitrum-QA-Dashboard/contents/review_db/{st.session_state.round_id}/cosine_clusters.json'
    github_token = st.secrets["ACCESS_TOKEN"]
    headers = {
        "Authorization": f"Bearer {github_token}"
    }

    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        file_info = response.json()
        payload = {
            "message": "Updated cosine_clusters.json",
            "content": encoded_data,
            "sha": file_info["sha"]
        }

        update_response = requests.put(api_url, json=payload, headers=headers)
        if update_response.status_code == 200:
            print("cosine_clusters.json updated successfully.")
