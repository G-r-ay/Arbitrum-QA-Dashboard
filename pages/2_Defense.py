# --------------------------------------------------------------------
# Import necessary libraries
# --------------------------------------------------------------------
import urllib
import json
from io import StringIO
import streamlit as st
import plotly.graph_objects as go
import itertools
import pandas as pd
import requests
from datetime import datetime,timedelta
import plotly.express as px
from utils.fetcher import fetch
from utils.data_manager import main_color, delete_after_review, manage_df, check_under_review


# --------------------------------------------------------------------
# Load Voting Data, Project Info, and Round Data
# --------------------------------------------------------------------
voting_data, project_info, round_data, round_status, start_time, end_time = fetch()
voting_data["transaction_date"] = pd.to_datetime(voting_data["transaction_date"])
threats_df =  voting_data[voting_data['Threat Type'] != 'Normal']
threats_df_unique =  voting_data[voting_data['Threat Type'] != 'Normal'].drop_duplicates(subset='voter')
if not threats_df.empty:
    total_detections = len(threats_df['voter'].unique())
    number_under_review = check_under_review(st.session_state.round_id)
    sybil_donations_sum = threats_df["amountUSD"].sum()

    # --------------------------------------------------------------------
    # Sample data for line chart
    # --------------------------------------------------------------------
    threat_counts = threats_df["Threat Type"].value_counts()
    threat_categories = ["Script Bot", "Recycler", "Reoccuring Threat"]

    # --------------------------------------------------------------------
    # Title and introductory text
    # --------------------------------------------------------------------
    st.title("Defense Page🛡️")
    st.write("""
    🚀 Welcome to the Defense Page! 🛡️

    Hey there, brave warriors of the digital frontier! Today, we're going to put on our superhero capes and fight off any digital villains that dare to threaten our beautiful platform. 🦸‍♀️🦸‍♂️

    Remember, every address we review is like uncovering a new secret ingredient in our defense recipe. And just like cooking, sometimes it takes a lot of stirring (aka 'reviewing') to get everything right. 🥗

    And remember, every update we make to our database is like adding another brick to our digital castle wall. So, let's keep building, one database entry at a time! 🏰

    So, are you ready to join the fight? Let's protect our platform, one threat at a time! 💪
    """)

    # --------------------------------------------------------------------
    # Line chart and metrics section
    # --------------------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    metrics, bar = st.columns([25, 75])

    # -------------- Line chart Plot --------------
    with bar:
        with st.container():
            threats_per_project = threats_df.groupby('ProjectTitle').size().reset_index(name='threats')
            threats_per_project['ProjectTitle'] = [project[:15] for project in threats_per_project['ProjectTitle']]

            color_cycle = itertools.cycle(main_color)

            # Create a list of colors for the bars, repeating as necessary
            bar_colors = [next(color_cycle) for _ in range(len(threats_per_project))]
            trace = go.Bar(x=threats_per_project['ProjectTitle'], y=threats_per_project['threats'],marker=dict(color=bar_colors))
            layout = go.Layout(title='Threat Distribution Across Projects')
            data = [trace]
            st.plotly_chart(dict(data=data, layout=layout), use_container_width=True)

    metrics.markdown("<br>", unsafe_allow_html=True)
    metrics.metric(label="Total Detections", value="{:}".format(total_detections))
    metrics.metric(label="Threat Donations Sum (USD)", value="{:}".format(sybil_donations_sum.round(2)))
    metrics.metric(label="Addresses Being Reviewed", value="{:}".format(number_under_review))
    metrics.metric(label="Database Amount for Recurring Threats", value="{:,}".format(threat_counts.get("Reoccurring Threat", 0)))

    # --------------------------------------------------------------------
    # Radar and filled line chart section
    # --------------------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    line, radar = st.columns([65, 35])

    # -------------- Radar chart Plot --------------
    with radar:
        threat_types = threats_df_unique['Threat Type'].value_counts().reset_index()
        threat_types.columns = ['Threat Type', 'Count']

        # Create the pie chart
        trace = go.Pie(labels=threat_types['Threat Type'], values=threat_types['Count'], textinfo='label+percent',marker=dict(colors=main_color))
        layout = go.Layout(title='Types of Threats Detected')
        data = [trace]
        st.plotly_chart(dict(data=data, layout=layout), use_container_width=True)

    # -------------- Filled line chart Plot --------------
    votes_over_time = (
        threats_df.groupby("transaction_date")
        .agg(unique_votes=("voter", "count"), total_amount_donated=("amountUSD", "sum"))
        .reset_index()
    )
    votes_over_time["transaction_date"] = pd.to_datetime(votes_over_time["transaction_date"])
    votes_over_time.set_index('transaction_date', inplace=True)

    # Create date range
    date_range = pd.date_range(start=voting_data['transaction_date'].min(), end=voting_data['transaction_date'].max())

    # Reindex and fill missing values
    votes_over_time = votes_over_time.reindex(date_range, fill_value=0)
    votes_over_time["total_amount_donated"] = votes_over_time["total_amount_donated"].round(2)

    with line:
        fig = go.Figure(data=go.Scatter(
        x=votes_over_time.index,
        y=votes_over_time["unique_votes"],
        mode='lines+markers',
        name='Threats',
        hovertemplate="<b>%{y}</b>",
        ))

        fig.update_layout(
        title='Frequency of Threat Votes Over Time',
        xaxis_title='Date',
        yaxis_title='Threats',
        )

        # Fill the area under the line
        fig.update_traces(fill='tozeroy', line=dict(color=main_color[1]))

        st.plotly_chart(fig, use_container_width=True)

    # --------------------------------------------------------------------
    # Download button for Review data
    # --------------------------------------------------------------------
    current_date = datetime.now().date()
    time_difference =  end_time - current_date
    # Check if two or more days have passed
    if time_difference >= timedelta(days=2):
    review_complete = st.checkbox('Review Complete')
    exit_df = threats_df.drop_duplicates(subset='voter')[['voter','Threat Type']].to_csv(index=False)
    if review_complete:
        uploaded_file = st.file_uploader("Upload Reviewed File")
        submit_detected,submit_reviewed  = st.columns(2)
        if submit_detected.button('Submit All Detected Threats'):
            manage_df()
            delete_after_review(st.session_state.round_id, round_status)
        if uploaded_file is not None:
            bytes_data = uploaded_file.getvalue()
            stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
            string_data = stringio.read()
            dataframe = pd.read_csv(uploaded_file)
            st.dataframe(dataframe)
            
            if submit_reviewed.button('Submit Reviewed File'):
                manage_df(dataframe, False)
                delete_after_review(st.session_state.round_id, round_status)
    else:
        if round_status == 'Active':
            st.download_button(
                label="Download Threats Active Report",
                data=exit_df,
                file_name=f"{st.session_state.round_id}-{datetime.now().date()} threats.csv",
                key="download_button1"
            )
        else:
            st.download_button(
                label="Download Threats Report",
                data=exit_df,
                file_name=f"{st.session_state.round_id} threats.csv",
                key="download_button1"
            )
else:
    st.write("Round is all safe🛡️")
