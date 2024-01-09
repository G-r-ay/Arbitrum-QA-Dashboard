import streamlit as st
from Defense_systems.marker import classify
from datetime import datetime, date, timedelta
from utils.data_manager import get_data,get_round_status,create_temp_directory_for_rounds,block_timestamp

from utils.queryFunctions import get_user_data
@st.cache_data
def fetch():
    voting_data, project_info, round_data = get_data(st.session_state['round_id'])
    round_status,start_time,end_time = get_round_status()
    create_temp_directory_for_rounds(st.session_state.round_id,round_status,voting_data,start_time)
    voting_data = classify(voting_data,round_status)
    voting_data = voting_data.reset_index(drop=True)
    current_date = datetime.now().date()  # Convert to datetime.date

    # Calculate the difference between the current date and the specific day
    time_difference =  end_time - current_date
    # Check if two or more days have passed
    if time_difference >= timedelta(days=2):
        block_timestamp(st.session_state.round_id)
        get_user_data(st.session_state.round_id)
    else:
        print("old round")
    return voting_data, project_info, round_data,round_status,start_time,end_time
