# ----------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------
import json
import circlify
import numpy as np
import pandas as pd
import streamlit as st
import plotly.subplots as sp
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from matplotlib.patches import Circle

from utils.data_manager import main_color
from utils.fetcher import fetch

#-------------- Load Voting Data, Project Info, and Round Data --------------
voting_data, project_info, round_data,round_status,start_time,end_time = fetch()
# --------------------------------------------------------------------
# Project Selection
# --------------------------------------------------------------------
option = st.selectbox(
    label="Select Project",
    options=voting_data["ProjectTitle"].unique(),
    key="projectbox",
)
project_data = voting_data.loc[
    voting_data["ProjectTitle"] == st.session_state.projectbox
]


# -------------- Threats DataFrame for Threat Analysis --------------
threats_df = project_data[
    project_data["Threat Type"].isin(["Script Bot", "Recycler", "Reoccuring Threat"])
]


# -------------- Data Processing for Specific Round ID --------------
votes_over_time = (
    project_data.groupby("transaction_date")
    .agg(unique_votes=("voter", "count"), total_amount_donated=("amountUSD", "sum"))
    .reset_index()
)

votes_over_time["transaction_date"] = pd.to_datetime(
    votes_over_time["transaction_date"]
)
votes_over_time.set_index("transaction_date", inplace=True)
votes_over_time = votes_over_time.reindex(
    pd.date_range(
        start=votes_over_time.index.min(), end=votes_over_time.index.max(), freq="D"
    ),
    fill_value=0,
)
votes_over_time["total_amount_donated"] = votes_over_time[
    "total_amount_donated"
].round(2)

# -------------- Assign data for plotting --------------
x_project = votes_over_time.index
y2_line_reg = votes_over_time["unique_votes"]
y1_bar_reg = votes_over_time["total_amount_donated"]

# -------------- Threats Data Processing --------------
votes_over_time2 = (
    threats_df.groupby("transaction_date")
    .agg(unique_votes=("voter", "count"), total_amount_donated=("amountUSD", "sum"))
    .reset_index()
)
votes_over_time2["transaction_date"] = pd.to_datetime(votes_over_time2["transaction_date"])
votes_over_time2.set_index('transaction_date', inplace=True)

# Create date range
date_range = pd.date_range(start=voting_data['transaction_date'].min(), end=voting_data['transaction_date'].max())

# Reindex and fill missing values
votes_over_time2 = votes_over_time2.reindex(date_range, fill_value=0)

votes_over_time2["total_amount_donated"] = votes_over_time2[
    "total_amount_donated"
].round(2)
y2_line_th = votes_over_time2["unique_votes"]
y1_bar_th = votes_over_time2["total_amount_donated"]


# -------------- Extract Relevant Data for Analysis --------------
voter_data = project_data[["voter", "Threat Type"]].drop_duplicates(subset="voter")
filtered_df = voter_data[voter_data["Threat Type"].isin(["Script Bot", "Recycler", "Reoccuring Threat"])]
no_voters = len(project_data["voter"].unique())
amount_recieved = project_data["amountUSD"].sum()
General_data = (
    project_data.groupby("voter")
    .agg({"amountUSD": "sum"})
    .reset_index()
    .round({"amountUSD": 2})
    .sort_values(by="amountUSD")
)
total_threats = len(filtered_df)
num_normal = no_voters - total_threats
norm_ratio = round(num_normal / no_voters * 10)
threat_ratio = round(total_threats / no_voters * 10)

# --------------------------------------------------------------------
# Threat Analysis
# --------------------------------------------------------------------
num_threats = len(filtered_df["voter"].unique())
amount_recieved_t = threats_df["amountUSD"].sum()
General_data = (
    project_data.groupby("voter")
    .agg({"amountUSD": "sum"})
    .reset_index()
    .round({"amountUSD": 2})
    .sort_values(by="amountUSD", ascending=False)
)
threat_counts = filtered_df["Threat Type"].value_counts()

# -------------- Threats Ratios --------------

if total_threats != 0:
    sybil_ratio = int(threat_counts.get("Script Bot", 0) / total_threats * 10)
    farmer_bots_ratio = int(threat_counts.get("Recycler", 0) / total_threats * 10)
    seeders_ratio = int(threat_counts.get("Reoccuring Threat", 0) / total_threats * 10)
else:
    sybil_ratio = 0
    farmer_bots_ratio = 0
    seeders_ratio = 0


# -------------- Threat Analysis --------------

threat_counts = threats_df["Threat Type"].value_counts()
sub_labels = ["Script Bot", "Recycler", "Reoccuring Threat"]
sub_values = [threat_counts.get(threat, 0) for threat in sub_labels]


# ---------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)
# ---------------------------------------------------------------------

# ----------------------------------------------------------------------
# General and Threats Tabs
# ----------------------------------------------------------------------
General, Threats = st.tabs(["General", "Threats"])

with General:
# ----------------------------------------------------------------------
# General Metrics
# ----------------------------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label="Total Voters", value=no_voters)
    col2.metric(
        label="Voter Ratio",
        value="{}:{}".format(norm_ratio, threat_ratio),
    )
    col3.metric(label="Total Donations (USD)", value="${:,.2f}".format(amount_recieved))
    col4.metric(label="Avg Donation per Voter (USD)", value="${:,.2f}".format(amount_recieved/len(project_data['voter'].unique())))

# ----------------------------------------------------------------------
# Project Activity Overview Chart
# ----------------------------------------------------------------------
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=x_project,
            y=y1_bar_reg,
            name="Amount Donated (USD)",
            hovertemplate="<b>%{y}</b>",
            marker=dict(color=main_color[0]),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x_project,
            y=y2_line_reg,
            mode="lines+markers",
            name="Vote Count",
            hovertemplate="<b>%{y}</b>",
            line=dict(color=main_color[1]),
            line_shape="linear",
        )
    )
    fig.update_layout(
        title="Project Activity Overview",
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5
        ),
    )
    st.plotly_chart(fig, use_container_width=True)

# ----------------------------------------------------------------------
# Top Contributors Table
# ----------------------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    table, circles_col = st.columns([70, 30])
    with table:
        st.subheader("Leading Contributors")
        st.dataframe(General_data, use_container_width=True, hide_index=True)

# ----------------------------------------------------------------------
# Voter Distribution Circle Packing
# ----------------------------------------------------------------------
    with circles_col:
        st.subheader("Voter Type Distribution")
        df = project_data["Threat Type"].value_counts().sort_values(ascending=True)
        circles = circlify.circlify(
            data=df.values.tolist(),
            show_enclosure=False,
            target_enclosure=circlify.Circle(x=0, y=0, r=2),
        )
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(alpha=0))
        fig.set_facecolor("None")
        ax.axis("off")
        lim = max(
            max(
                abs(circle.x) + circle.r,
                abs(circle.y) + circle.r,
            )
            for circle in circles
        )
        plt.xlim(-lim, lim)
        plt.ylim(-lim, lim)
        labels = df.index.tolist()
        colors = [main_color[0], main_color[1], main_color[2], main_color[3]]
        for circle, label, color in zip(circles, labels, colors):
            x, y, r = circle
            ax.add_patch(Circle((x, y), r, alpha=0.9, linewidth=2, color=color))
            count = df[label]
            plt.annotate(f"{label}: {count}", (x, y), va="center", ha="center",color = 'white')
        st.pyplot(fig)

# ----------------------------------------------------------------------
# Voting Status Sphere Chart
# ----------------------------------------------------------------------
    filtered_df = voter_data[voter_data["Threat Type"] != "Normal"]
    num_threats = len(filtered_df)
    num_non_threats = len(project_data) - num_threats
    theta_threats = np.random.uniform(0, 2 * np.pi, num_threats)
    phi_threats = np.random.uniform(0, np.pi, num_threats)
    theta_non_threats = np.random.uniform(0, 2 * np.pi, num_non_threats)
    phi_non_threats = np.random.uniform(0, np.pi, num_non_threats)
    x_threats = np.sin(theta_threats) * np.cos(phi_threats)
    y_threats = np.sin(theta_threats) * np.sin(phi_threats)
    z_threats = np.cos(theta_threats)
    x_non_threats = np.sin(theta_non_threats) * np.cos(phi_non_threats)
    y_non_threats = np.sin(theta_non_threats) * np.sin(phi_non_threats)
    z_non_threats = np.cos(theta_non_threats)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter3d(
            x=[0],
            y=[0],
            z=[0],
            mode="markers+lines",
            line=dict(width=1, color="black"),
            marker=dict(size=10, color="#DAF3FB"),
            text = voting_data['ProjectTitle'][0],
            hoverinfo="text",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter3d(
            x=x_threats,
            y=y_threats,
            z=z_threats,
            mode="markers",
            marker=dict(size=3, color=main_color[1], line=dict(width=1, color="black")),
            name="Threat",
            text=filtered_df["voter"],
            hoverinfo="text",
        )
    )
    fig.add_trace(
        go.Scatter3d(
            x=x_non_threats,
            y=y_non_threats,
            z=z_non_threats,
            mode="markers",
            marker=dict(size=3, color=main_color[0], line=dict(width=1, color="black")),
            name="Non-Threat",
            text=project_data[project_data["Threat Type"] == "Normal"]["voter"],
            hoverinfo="text",
        )
    )
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
        margin=dict(l=0, r=0, t=60, b=20),
        title="Voter Type Distribution: Threats and Non-Threats",
    )
    fig.update_layout(showlegend=True, legend=dict(x=0.427, y=0, orientation="h"))
    fig.update_layout(height=450)
    start_view_angle = dict(eye=dict(x=1, y=1, z=0.4))
    fig.update_layout(margin=dict(l=0, r=0, t=60, b=20))
    fig.update_layout(scene_camera=start_view_angle)
    fig.update_layout(title="Voting Status Sphere: Sybil vs. Non-Sybil")
    st.plotly_chart(fig, use_container_width=True)


# ----------------------------------------------------------------------
# Threats Tab
# ----------------------------------------------------------------------
with Threats:
    if num_threats > 0:
        main_color = ["#165469", "#26738C", "#348EAC", "#3F9EBB"]
        script_bot_percentage = int((threat_counts.get("Script Bot", 0)/num_threats) *100)
        recycle_ratio = int((threat_counts.get("Recycler", 0)/num_threats) *100)
        Reoccuring_ratio = int((threat_counts.get("Reoccuring Threat", 0)/num_threats) *100)
    # ----------------------------------------------------------------------
    # Metrics Section
    # ----------------------------------------------------------------------
        with st.container():
            temporal_graph, metrics = st.columns([75, 25])

    #-------------- Metrics Sub-section --------------

            with metrics:
                st.markdown("<br>", unsafe_allow_html=True)
                with st.container():
                    st.metric(label="Detected Threats", value=num_threats)
                with st.container():
                    st.metric(
                        label="Threat Distribution",
                        value="{}:{}:{}".format(
                            sybil_ratio, farmer_bots_ratio, seeders_ratio
                        ),
                    )
                with st.container():
                    st.metric(
                        label="Total Donations (USD)",
                        value="${:,.2f}".format(amount_recieved_t),
                    )
                with st.container():
                    st.metric(label="Avg Donation per Voter (USD)", value="${:,.2f}".format(amount_recieved_t/len(threats_df['voter'].unique())))

    # ----------------------------------------------------------------------
    # Chart Section
    # ----------------------------------------------------------------------
            with temporal_graph:
                fig = go.Figure()
                fig.add_trace(
                    go.Bar(
                        x=x_project,
                        y=y2_line_th,
                        hovertemplate="<b>%{y}</b>",
                        name="Amount Donated (USD)",
                        marker=dict(color=main_color[0]),
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=x_project,
                        y=y2_line_th,
                        mode="lines+markers",
                        name="Vote Counts",
                        hovertemplate="<b>%{y}</b>",
                        line=dict(color=main_color[-1]),
                        line_shape="spline",
                    )
                )
                fig.update_layout(
                    title="Activity Trends for Threat Projects",
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.25,
                        xanchor="center",
                        x=0.5,
                    ),
                )
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

    # ----------------------------------------------------------------------
    # Detection Method and Proportions Section
    # ----------------------------------------------------------------------
        with st.container():
            detection_method, Proportions_subplot = st.columns([25, 75])

    #-------------- Detection Method Sub-section --------------
            with detection_method:
                fig = go.Figure(
                    go.Bar(
                        x=['Script Bot', 'Recyclers', 'DataBase'],
                        y=[script_bot_percentage, recycle_ratio, Reoccuring_ratio],
                        orientation="v",
                        marker=dict(color=main_color[1])
                    )
                )
                
                fig.update_layout(
                    title="Triggered Detection Methods",
                    yaxis_title="Values",
                    xaxis_title="Methods",
                )
                fig.update_traces(hovertemplate='%{x}<br>Amount: %{y}', hoverinfo='skip')
                st.plotly_chart(fig, use_container_width=True)

    #-------------- Proportions Sub-section --------------
        with Proportions_subplot:
            # Create Pie Chart
            pie,bar = st.columns(2)
            with pie:
                pie_fig = go.Figure(
                    data=[
                        go.Pie(
                            labels=sub_labels,
                            values=sub_values,
                            hole=0.55,
                            hoverlabel=dict(namelength=0),
                            marker=dict(colors=main_color, line=dict(color=main_color[-1])),
                        )
                    ]
                )
                pie_fig.update_layout(
                    title_text="Voter Type Allocation (Quantity)",
                    legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.25,
                    xanchor="center",
                    x=0.5,
                ),
                )
                st.plotly_chart(pie_fig, use_container_width=True)

            # Create Bar Chart
            with bar:
                bar_fig = go.Figure()
                bar_fig.add_trace(
                    go.Bar(
                        x=sub_values,
                        y=sub_labels,
                        orientation="h",
                        marker=dict(color=main_color),
                        hovertemplate='%{y}<br>Amount: %{x}'
                    )
                )
                
                bar_fig.update_layout(
                    title_text="Voter Type Allocation (Amount)",
                    xaxis_title="Amount",
                    yaxis_title="Voter Type",
                )
                st.plotly_chart(bar_fig, use_container_width=True)

    else:
        st.write("""
        ### 🌐 Project Security Status ✅
        
        **All Clear!** 🎉
        
        No threats detected. This project is safe and within the rules. Keep up the great work! 👏
        """)
