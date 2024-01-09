# ----------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------
import json
import circlify
import pandas as pd
import networkx as nx
import streamlit as st
from datetime import datetime
import concurrent.futures
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from Defense_systems.marker import classify
from utils.data_manager import chain_data,main_color
from utils.fetcher import fetch
# ----------------------------------------------------------------------
# Constants and Initial Setup
# ----------------------------------------------------------------------

st.set_page_config(
   page_title="Arbitrum Grants Defense Manager", layout="wide", initial_sidebar_state="collapsed",page_icon='https://raw.githubusercontent.com/G-r-ay/Arbitrum-QA-Dashboard/8c4170b70e095caa83fd8c901d171e9df3d8f982/logo.svg'
)

if "round_id" not in st.session_state:
   previous_round_id =None
else:
   previous_round_id = st.session_state.round_id

# ----------------------------------------------------------------------
# Load Data
# ----------------------------------------------------------------------

st.markdown("<h1>Arbitrum QA Dashboard</h1>", unsafe_allow_html=True)

# ----------------------------------------------------------------------
# Cache Functions
# ----------------------------------------------------------------------
@st.cache_data
def network_graph():
   grants = voting_data["ProjectTitle"].unique().tolist()
   users = voting_data["voter"].unique().tolist()
   G = nx.Graph()

   center_node = "center_node"
   G.add_nodes_from(users, size=10, color=main_color[1])
   G.add_nodes_from(grants, size=20, color=main_color[0])
   G.add_node(center_node, size=30, color="#031D44")

   G.add_edges_from([(center_node, grant) for grant in grants])

   valid_edges = voting_data[voting_data["voter"].isin(users) & voting_data["ProjectTitle"].isin(grants)]
   edges = list(zip(valid_edges["voter"], valid_edges["ProjectTitle"]))
   G.add_edges_from(edges)

   pos = nx.spring_layout(G, dim=3, k=0.008)

   node_sizes = [G.nodes[n]["size"] for n in G.nodes]
   node_colors = [G.nodes[n]["color"] for n in G.nodes]

   x, y, z = zip(*[pos[k] for k in G.nodes])
   edge_x, edge_y, edge_z = [], [], []
   for edge in G.edges():
      x0, y0, z0 = pos[edge[0]]
      x1, y1, z1 = pos[edge[1]]
      edge_x.extend([x0, x1, None])
      edge_y.extend([y0, y1, None])
      edge_z.extend([z0, z1, None])
   node_trace = go.Scatter3d(
      x=x,
      y=y,
      z=z,
      mode="markers",
      hoverinfo="text",
      marker=dict(
         size=node_sizes,
         color=node_colors,
         opacity=1,
      ),
   )


   edge_trace = go.Scatter3d(
      x=edge_x,
      y=edge_y,
      z=edge_z,
      line=dict(width=0.3, color="#888"),
      hoverinfo="none",
      mode="lines",
   )

   layout = go.Layout(title="Network of Voters and Grants")

   fig = go.Figure(data=[node_trace, edge_trace], layout=layout)
   fig.update_layout(
      scene=dict(
         aspectmode="auto",
         aspectratio=dict(x=1, y=1, z=1),
         xaxis=dict(
               showgrid=False,
               zeroline=False,
               showticklabels=False,
               title="",
               visible=False,
         ),
         yaxis=dict(
               showgrid=False,
               zeroline=False,
               showticklabels=False,
               title="",
               visible=False,
         ),
         zaxis=dict(
               showgrid=False,
               zeroline=False,
               showticklabels=False,
               title="",
               visible=False,
         ),
      ),
      margin=dict(l=0, r=0, t=60, b=0),
      height=700,
   )

   fig.update_traces(
      textposition="top center",
      hovertext=[node if node != center_node else "" for node in G.nodes],
      showlegend=False,
   )

   return fig



# -------------- Round Time Calculations --------------


# ----------------------------------------------------------------------
# Session State Logic
# ----------------------------------------------------------------------

# -------------- Round Selection --------------

names = chain_data["metadata"].apply(lambda x: x.get("name")).tolist()

if "round_index" not in st.session_state:
   st.session_state["round_index"] = 0

option = st.selectbox(
   "Select a Round", names, index=st.session_state.round_index, key="roundbox"
)
st.session_state.round_id = chain_data.loc[
   chain_data["metadata"].apply(lambda x: x.get("name")) == st.session_state.roundbox,
   "id"].iloc[0]
if previous_round_id != st.session_state.round_id:
   st.cache_data.clear()
   print("cleared cache")
voting_data, project_info, round_data,round_status,start_time,end_time = fetch()
st.session_state.round_index = names.index(st.session_state.roundbox)





# -------------- Data Retrieval --------------

voter_data = classify(voting_data.drop_duplicates(subset="voter").reset_index(drop=True),round_status)
filtered_df = voter_data[voter_data["Threat Type"].isin(["Script Bot", "Recycler", "Reoccuring Threat"])]

# -------------- Data Processing --------------
votes_over_time = (
   voting_data.groupby("transaction_date")
   .agg(
         unique_votes=("voter", "count"),
         total_amount_donated=("amountUSD", "sum"),
   )
   .reset_index()
)

votes_over_time['transaction_date'] = pd.to_datetime(votes_over_time['transaction_date'])
votes_over_time.set_index('transaction_date', inplace=True)

# Step 3: Create date range
date_range = pd.date_range(start=votes_over_time.index.min(), end=votes_over_time.index.max())

# Step 4: Reindex and fill missing values
votes_over_time = votes_over_time.reindex(date_range, fill_value=0)


votes_over_time["total_amount_donated"] = votes_over_time["total_amount_donated"].round(2)
average_voters_per_day = int(votes_over_time["unique_votes"].mean())

# -------------- Pie Chart Data --------------
pie_labels = ["Normal", "Threats"]
pie_values = [len(voter_data) - len(filtered_df), len(filtered_df)]


# ----------------------------------------------------------------------
# UI Elements
# ----------------------------------------------------------------------

# -------------- Extracting Values --------------
round_name = round_data["metadata"].item()["name"]
round_info = round_data["metadata"].item().get("eligibility", {}).get("description", "")
num_voters = round_data["uniqueContributors"].item()
total_amount_donated = round(round_data["amountUSD"].item(), 2)
matching_cap = round_data["matchAmountUSD"].item()

# -------------- Grouping and Calculations --------------
grouped = voting_data.groupby("ProjectTitle")["amountUSD"].sum().sort_values(ascending=False)
projects = [project[:15] for project in grouped.index]
amounts = [round(amount, 2) for amount in grouped.values]

# -------------- Table DataFrame --------------
table_df = voting_data.groupby("ProjectTitle").agg({"amountUSD": "sum", "voter": "count"}).reset_index().round({"amountUSD": 2}).sort_values('voter',ascending=False)

# -------------- Counting Unique Voters --------------
project_votes = voting_data.groupby("ProjectTitle")["voter"].nunique().reset_index()
circle_data = [{"id": row["ProjectTitle"][:15], "datum": row["voter"]} for index, row in project_votes.iterrows()]

# -------------- Markdown for Displaying Round Information --------------
st.write(round_info, unsafe_allow_html=True)
round_summary = f"<p style='margin-bottom:5px'><strong>📅 Start Date:</strong> {start_time}</p>" \
              f"<p style='margin-bottom:5px'><strong>📅 End Date:</strong> {end_time}</p>" \
              f"<p style='margin-bottom:5px'><strong>🔍 Status:</strong> {round_status}</p>"

st.markdown(round_summary, unsafe_allow_html=True)

# ----------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)
# ----------------------------------------------------------------------

# -------------- Temporal Graph and Metrics Display --------------
# -------------- Linechart --------------
temporal_graph, metrics = st.columns([70, 30], gap="medium")
with temporal_graph:
   with st.container():
      # -------------- Linechart Plot --------------
      fig = go.Figure()
      fig.update_layout(
         title="Donations and Vote Trends Over Time",
         legend=dict(
               orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5
         ),
      )
      fig.add_trace(
         go.Bar(
               x=votes_over_time.index,
               y=votes_over_time["total_amount_donated"],
               name="Amount_Donated",
               hovertemplate="<b>%{y}</b>",
               marker=dict(color=main_color[0]),
         )
      )
      fig.add_trace(
         go.Scatter(
               x=votes_over_time.index,
               y=votes_over_time["unique_votes"],
               mode="lines+markers",
               name="Vote Count",
               hovertemplate="<b>%{y}</b>",
               line=dict(color=main_color[1]),
               line_shape="spline",
         )
      )

      st.plotly_chart(fig, use_container_width=True)

# -------------- Metrics --------------
with metrics:
   with st.container():
      # -------------- Metrics Display --------------
      st.metric(label="Voter Participation", value=num_voters, delta_color="normal")
      st.metric(
         label="Contributions Received", value="${:,.2f}".format(total_amount_donated)
      )
      st.metric(label="Match Funding Pool", value="${:,.2f}".format(matching_cap))
      st.metric(label="Average Daily Participation", value=average_voters_per_day)

# ----------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)
# ----------------------------------------------------------------------
# -------------- Project Popularity Bubbles --------------
treemap, donation_bar = st.columns([50, 50])
with st.container():
# -------------- Project Popularity Bubbles Chart --------------
   with treemap:
      project_voter_count = voting_data.groupby('ProjectTitle')['voter'].count().reset_index()

      custom_color_scale = ['#087856', '#085178', '#087478', '#087830', '#082E5B']
      import plotly.express as px
      fig = px.treemap(project_voter_count, 
                     path=['ProjectTitle'], # Define the hierarchy
                     values='voter', # Define the size of the boxes
                     title='Voter Count by Project Title',
                     hover_data={'voter': True, 'ProjectTitle': False},
                     color_continuous_scale='Blues' # Customize hover data
                     )

      # Update layout to control the appearance of the treemap
      fig.update_layout(
         # # Set the background color to white
         margin=dict(l=0, r=0, t=100, b=0), # Remove the margins around the plot
         coloraxis_showscale=False, # Hide the color scale
      )

      # Customize hover template to only show the number of voters and label properly formatted
      fig.update_traces(hovertemplate='%{label}<br>Number of Voters: %{value}')
      st.plotly_chart(fig, use_container_width=True)

# -------------- Top Projects by Amount Donated Chart --------------
   with donation_bar:
      fig_bar = go.Figure()

      fig_bar.add_trace(
         go.Bar(
               x=amounts,
               y=projects,
               orientation="h",
               name="Amount Donated",
               marker=dict(color=main_color[-1]),
               hovertemplate='%{y}<br>Amount: %{x}'
         )
      )

      fig_bar.update_layout(
         title="Donation Distribution Across Projects",
         xaxis_title="Amount (USD)",
         yaxis_title="Projects",
         yaxis_autorange="reversed",
      )
      st.plotly_chart(fig_bar, use_container_width=True)

# ----------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)
# ----------------------------------------------------------------------

with st.container():
# -------------- Network Graph Chart --------------
   st.plotly_chart(network_graph(), use_container_width=True)

with st.container():
# -------------- Pie and Bar Charts --------------
   table, pie = st.columns([70, 30], gap="medium")

   with table:
# -------------- Top Projects Table --------------
      st.subheader("Leading Projects by Participation")
      st.dataframe(table_df,hide_index=True,use_container_width=True)

   with pie:
# -------------- Voter Type Proportions Pie Chart --------------
      with st.container():
         fig_pie = go.Figure(
               data=[
                  go.Pie(
                     labels=pie_labels,
                     values=pie_values,
                     hole=0.55,
                     marker=dict(
                           colors=main_color, line=dict(color="black", width=0.1)
                     ),
                  )
               ]
         )
         fig_pie.update_layout(
               title="Distribution of Voter Types",
               legend=dict(
                  orientation="h",
                  yanchor="bottom",
                  y=-0.25,
                  xanchor="center",
                  x=0.5,
               ),
         )
         st.plotly_chart(fig_pie, use_container_width=True)
   st.markdown("<br>", unsafe_allow_html=True)

# ----------------------------------------------------------------------
