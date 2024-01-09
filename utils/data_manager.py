# ----------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------
import json
import time
import base64
import requests
import pandas as pd
import streamlit as st
from Defense_systems.Recycling import track_recycling
from datetime import datetime, timedelta
from sklearn.preprocessing import LabelEncoder
from Defense_systems.Similarity_Script import cluster_addresses
# ----------------------------------------------------------------------
# Import necessary libraries
# ----------------------------------------------------------------------


access_token = st.secrets["ACCESS_TOKEN"]

headers = {
   'Authorization': f'token {access_token}',
   'Accept': 'application/vnd.github.v3+json'
}
# ----------------------------------------------------------------------
# Set the main color scheme
# ----------------------------------------------------------------------
main_color = ["#087478", "#57EBBE", "#389D96", "#68C5B4","#30B09B"]

# ----------------------------------------------------------------------
# Load data from Gitcoin API and filter by unique contributors
# ----------------------------------------------------------------------
chain_data = pd.read_json("https://grants-stack-indexer.gitcoin.co/data/42161/rounds.json")
chain_data = chain_data[chain_data["uniqueContributors"] > 10].sort_values('roundStartTime',ascending=False)

# ----------------------------------------------------------------------
# Initialize data based on round_id and voting_data
# ----------------------------------------------------------------------

def initialise_data(round_id, voting_data):
#-------------- Load voter data from a Parquet file --------------
    voter_data = pd.read_parquet(f"https://raw.githubusercontent.com/G-r-ay/Arbitrum-QA-Dashboard/main/round_user_info/{round_id}.parquet")

#-------------- Drop unnecessary columns from voting_data --------------
    voting_data.drop(
        [
            'id',
            "transaction",
            "applicationId",
            "roundId",
            "token",
            "amount",
            "amountRoundToken"
        ],
        axis=1,
        inplace=True,
    )

#-------------- Calculate funding counts and other metrics --------------
    funding_counts = voting_data["voter"].value_counts()
    count_by_address_project = (
        voting_data.groupby(["voter", "ProjectTitle"]).size().reset_index(name="count")
    )
    no_grants_funded = count_by_address_project["voter"].value_counts()

    Address_info1 = pd.DataFrame(
        {"voter": funding_counts.index, "Funding_count": funding_counts.values}
    )
    Address_info2 = pd.DataFrame(
        {"voter": no_grants_funded.index, "No_Projects_Funded": no_grants_funded.values}
    )
    Address_info = pd.merge(Address_info1, Address_info2)

    usd_per_voter = voting_data.groupby("voter")["amountUSD"].sum().reset_index()
    Address_info = pd.merge(Address_info, usd_per_voter, on="voter")
    Address_info.rename(columns={"amountUSD": "Total_USD_Funded"}, inplace=True)

    filtered_votes = pd.merge(Address_info, voting_data, how="left", on="voter")

#-------------- Define relevant data points --------------
    data_points = ["voter", "Funding_count", "No_Projects_Funded", 'transaction_date', 'Total_USD_Funded']
    filtered_votes["address"] = filtered_votes["voter"]
    filtered_votes["project_title_sorted"] = filtered_votes["ProjectTitle"].apply(
        lambda x: "-".join(sorted(x.lower().split()))
    )

#-------------- Aggregate data and sort by project title --------------
    df_result = (
        filtered_votes.groupby("address")
        .agg({"voter": "first", "project_title_sorted": "_".join})
        .reset_index()
    )
    df_result = df_result.sort_values(by="project_title_sorted", ascending=False)[
        ["voter", "project_title_sorted"]
    ]

    cut_filtered = filtered_votes[data_points].drop_duplicates(subset=["voter"])

    cultivated_data = pd.merge(cut_filtered, df_result, on="voter")
    cultivated_data["voter"] = cultivated_data["voter"].str.lower()
    voter_data["voter"] = voter_data["voter"].str.lower()
    cultivated_data = pd.merge(cultivated_data, voter_data, on="voter")
    cultivated_data = cultivated_data.fillna(0)
    cultivated_data.sort_values(by="project_title_sorted", inplace=True)
    cultivated_data['last_date'] = cultivated_data['last_date'].astype('int64')
    cultivated_data['first_date'] = cultivated_data['first_date'].astype('int64')
    cultivated_data['transaction_date'] = pd.to_datetime(cultivated_data['transaction_date']).astype('int64') // 10**9

#-------------- Encode categorical columns using LabelEncoder --------------
    columns_to_encode = [
        "project_title_sorted",
        "first_from",
        "first_to",
        "last_from",
        "last_to",
    ]
    cultivated_data = cultivated_data.sort_values(by="project_title_sorted")
    encoders = {}
    for col in columns_to_encode:
        encoders[col] = LabelEncoder()
        cultivated_data[col] = encoders[col].fit_transform(cultivated_data[col])

    return cultivated_data.reset_index(drop=True)



def get_data(round_id):
    voting_data = pd.read_json(
        f"https://grants-stack-indexer.gitcoin.co/data/42161/rounds/{round_id}/votes.json"
    )
    project_info = pd.read_json(
        f"https://grants-stack-indexer.gitcoin.co/data/42161/rounds/{round_id}/applications.json"
    )
    round_data = chain_data.loc[lambda df: df["id"] == round_id]
    
    project_info = project_info[project_info["status"] == "APPROVED"]
    project_info["title"] = project_info["metadata"].apply(
        lambda x: x.get("application", {}).get("project", {}).get("title")
    )
    project_mappings = project_info[["projectId", "title"]].dropna().drop_duplicates()
    project_mappings = project_mappings.set_index("projectId").to_dict()["title"]
    mask = voting_data["projectId"].isin(project_mappings.keys())
    voting_data = voting_data[mask]
    voting_data["ProjectTitle"] = voting_data["projectId"].map(project_mappings)
    response = requests.get(f"https://raw.githubusercontent.com/G-r-ay/Arbitrum-QA-Dashboard/main/time_mappings/{round_id}.json")
    loaded_dict = json.loads(response.text)

    loaded_dict = {int(key): value for key, value in loaded_dict.items()}
    voting_data["transaction_date"] = pd.to_datetime(voting_data["blockNumber"].map(loaded_dict)).dt.date
    return voting_data, project_info, round_data

def block_timestamp(round_id):

    github_token = st.secrets["ACCESS_TOKEN"]
    voting_data = pd.read_json(
    f"https://grants-stack-indexer.gitcoin.co/data/42161/rounds/{round_id}/votes.json"
    )

    github_url = f"https://raw.githubusercontent.com/G-r-ay/Arbitrum-QA-Dashboard/main/time_mappings/{round_id}.json"
    response = requests.get(github_url)
    data = json.loads(response.text)

    stored_blocks = set(list(data.keys()))
    current_blocks = set(voting_data['blockNumber'].astype("str").unique())

    unique_to_list2 = list(current_blocks - stored_blocks)
    total_blocks = len(unique_to_list2)
    percentage_done = 0
    count=0

    if total_blocks == 0:
        print("no new blocks")
    else:
        my_bar = st.progress(0, text="Getting BlockTimestamp")
        for block in unique_to_list2:
            my_bar.progress(int(percentage_done), text="Getting BlockTimestamp")
            if count % 5 == 0:
                time.sleep(1)
            params = {
                "module": "block",
                "action": "getblockreward",
                "blockno": block,
                "apikey": st.secrets['ARB_SCAN_KEY']
            }
            response = requests.get("https://api.arbiscan.io/api", params=params)
            dt_object = datetime.utcfromtimestamp(int(response.json()['result']['timeStamp']))
            formatted_date = dt_object.strftime('%Y-%m-%d')

            data[str(block)] = formatted_date
            count+=1
            percentage_done =int((count / total_blocks) * 100)

            percentage_done = (count / total_blocks) * 100

        data = json.dumps(data)
        encoded_data = base64.b64encode(data.encode()).decode()

        api_url = f'https://api.github.com/repos/G-r-ay/Arbitrum-QA-Dashboard/contents/time_mappings/{round_id}.json'
        headers = {
            "Authorization": f"Bearer {github_token}"
        }

        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            file_info = response.json()
            payload = {
                "message": "Updated block-timestamp file",
                "content": encoded_data,
                "sha": file_info["sha"]
            }

            update_response = requests.put(api_url, json=payload, headers=headers)
            if update_response.status_code == 200:
                print("user data updated successfully.")
        my_bar.empty()

def create_temp_directory_for_rounds(round_id,round_status,voting_data,start_time):
    if round_status == 'Active':
        file_names = ['cosine_clusters.json','recycle_clusters.json']
        commit_messages = ["Create cosine_clusters.json", "Create recycle_clusters.json"]
        file_contents = ['{"Cluster Group 0" : []}' ,'{"Cluster Group 0" : []}']
        for file_name, file_content, commit_message in zip(file_names, file_contents, commit_messages):
            file_url = f'https://api.github.com/repos/G-r-ay/Arbitrum-QA-Dashboard/contents/review_db/{round_id}/{file_name}'
            file_response = requests.get(file_url, headers=headers)

            # If the file does not exist, GitHub API will return a 404 status code
            if file_response.status_code == 404:
                # The API URL for creating a file
                url = file_url

                # The content of the file (Base64 encoded)
                content = base64.b64encode(file_content.encode('utf-8')).decode('utf-8')

                # The request payload
                payload = json.dumps({
                    'message': commit_message,
                    'content': content
                })

                # Make the request to create the file
                response = requests.put(url, data=payload, headers=headers)

                # Check the response
                if response.status_code == 201:
                    print(f'File {file_name} created successfully')
                else:
                    print(f'Failed to create file {file_name}:', response.json())
            else:
                print(f'File {file_name} already exists.')
        cluster_addresses(initialise_data(st.session_state.round_id,voting_data))
        track_recycling(voting_data['grantAddress'].unique(),str(start_time),voting_data['voter'])
    else:
        print("Concluded")

def delete_after_review(round_id,round_status):
    if round_status != 'Active':
        headers = {
           'Authorization': f'token {access_token}',
           'Accept': 'application/vnd.github.v3+json'}
        url = f'https://api.github.com/repos/G-r-ay/Arbitrum-QA-Dashboard/contents/review_db/{round_id}'
        response = requests.get(url, headers=headers)

        # Check if the folder exists and has files
        if response.status_code == 200:
            files = response.json()

            # Loop through the files and delete them
            for file in files:
                file_path = file['path']
                file_sha = file['sha']
                delete_url = f'https://api.github.com/repos/G-r-ay/Arbitrum-QA-Dashboard/contents/{file_path}'
                
                # Payload with the SHA reference of the file and commit message
                payload = json.dumps({
                    'message': f'Delete {file_path}',
                    'sha': file_sha
                })

                # Send the DELETE request
                delete_response = requests.delete(delete_url, data=payload, headers=headers)

                # Check the response
                if delete_response.status_code == 200:
                    print(f'{file_path} deleted successfully')
                else:
                    print(f'Failed to delete {file_path}:', delete_response.json())

        else:
            print('Folder does not exist or is empty:', response.json())
    else:
        restart = {}
        restart = json.dumps(restart)
        encoded_data = base64.b64encode(restart.encode()).decode()
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
                print("recycle_clusters.json restarted successfully.")
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
                print("cosine_clusters.json restarted successfully.")
               st.success('Database Successfully Updated!', icon="✅")
def get_round_status():
    today_date = datetime.now().date()
    start_time = datetime.utcfromtimestamp(
    chain_data.loc[chain_data["id"] == st.session_state.round_id]["roundStartTime"].item()
    ).date()
    end_time = datetime.utcfromtimestamp(
    chain_data.loc[chain_data["id"] == st.session_state.round_id]["roundEndTime"].item()
    ).date()

    round_status = "Active" if end_time >= today_date else "Concluded"

    return round_status,start_time,end_time

def manage_df(dataframe = '', Full=True):
    """
        if Full is False
        DataFrmae should only have one column called Threats
    """
    try:
        if Full:
            db = pd.read_parquet(f"https://raw.githubusercontent.com/G-r-ay/Arbitrum-QA-Dashboard/main/main_db.parquet")
            db['entry_status'] = 'Old'
            recycling_response = requests.get(f"https://raw.githubusercontent.com/G-r-ay/Arbitrum-QA-Dashboard/main/review_db/{st.session_state.round_id}/recycle_clusters.json")
            recycling_cluster_dict = json.loads(recycling_response.text)
            recycling_address = [item.upper() for sublist in recycling_cluster_dict.values() for item in (sublist if isinstance(sublist, list) else [sublist])]

            cosine_response = requests.get(f"https://raw.githubusercontent.com/G-r-ay/Arbitrum-QA-Dashboard/main/review_db/{st.session_state.round_id}/cosine_clusters.json")
            cosine_cluster_dict = json.loads(cosine_response.text)
            cosine_cluster_address = [item.upper() for sublist in cosine_cluster_dict.values() for item in (sublist if isinstance(sublist, list) else [sublist])]

            recycling_df = pd.DataFrame({'address':recycling_address})
            recycling_df['Threat Type'] = 'Recycler'
            cosine_cluster_df = pd.DataFrame({'address':cosine_cluster_address})
            cosine_cluster_df['Threat Type'] = 'Script Bot'
            recycling_df['entry_status'] = 'New'
            cosine_cluster_df['entry_status'] = 'New'
            db = pd.concat([db,recycling_df,cosine_cluster_df])
            db = db.drop_duplicates()
            modified_content = db.to_parquet(index=False)
            modified_content_encoded = base64.b64encode(modified_content).decode()

            api_url = f'https://api.github.com/repos/G-r-ay/Arbitrum-QA-Dashboard/contents/main_db.parquet'

            headers = {
                "Authorization": f"Bearer {st.secrets['ACCESS_TOKEN']}"
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
        else:
            db = pd.read_parquet(f"https://raw.githubusercontent.com/G-r-ay/Arbitrum-QA-Dashboard/main/main_db.parquet")
            db['entry_status'] = 'Old'
            dataframe['entry_status'] = 'New'
            db = pd.concat([db,dataframe])
            db = db.drop_duplicates()
            modified_content = db.to_parquet(index=False)
            modified_content_encoded = base64.b64encode(modified_content).decode()
            api_url = f'https://api.github.com/repos/G-r-ay/Arbitrum-QA-Dashboard/contents/main_db.parquet'

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
    except json.JSONDecodeError as e:
        st.warning(f"No Addresses Under Review Check database for updates", icon="⚠️")

@st.cache_data
def check_under_review(round_id):
        db =pd.read_parquet("https://raw.githubusercontent.com/G-r-ay/Arbitrum-QA-Dashboard/main/main_db.parquet")['address']
        file_names = ['cosine_clusters.json','recycle_clusters.json']
        for file_name in file_names:
            file_url = f'https://api.github.com/repos/G-r-ay/Arbitrum-QA-Dashboard/contents/review_db/{round_id}/{file_name}'
            file_response = requests.get(file_url, headers=headers)
            if file_response.status_code == 404:
                return 0
            else:
                cosine_response = requests.get(f"https://raw.githubusercontent.com/G-r-ay/Arbitrum-QA-Dashboard/main/review_db/{st.session_state.round_id}/cosine_clusters.json")
                cosine_cluster_dict = json.loads(cosine_response.text)
                cosine_list = [item.upper() for sublist in cosine_cluster_dict.values() for item in (sublist if isinstance(sublist, list) else [sublist])]

                recycling_response = requests.get(f"https://raw.githubusercontent.com/G-r-ay/Arbitrum-QA-Dashboard/main/review_db/{st.session_state.round_id}/recycle_clusters.json")
                recycling_cluster_dict = json.loads(recycling_response.text)
                recycling_list = [item.upper() for sublist in recycling_cluster_dict.values() for item in (sublist if isinstance(sublist, list) else [sublist])]
                full_list = cosine_list + recycling_list
                filtered_list = [name for name in full_list if name.upper() not in db.str.upper().to_list()]
                return len(filtered_list)

