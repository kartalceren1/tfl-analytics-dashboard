import os
import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import altair as alt
import plotly.express as px

st.set_page_config(layout="wide")
st.title("🚇 TfL Analytics Dashboard")
st.markdown(
    """
   Explore London’s transport network in real-time:  
    - Monitor the current status of Tube, Overground, DLR, Elizabeth Line, and Bus routes.  
    - Identify disruptions and service delays instantly.  
    - Visualise all stations on a map with status indicators.  
    - Search for bus routes and check specific route updates.  
    - Plan journeys across the city and view estimated travel times and modes.  

    Use the interactive filters and map features to customize your view.
    """
)
st.markdown("---")

# User session state for selected lines
if "selected_lines" not in st.session_state:
    st.session_state.selected_lines = []

API_KEY = os.getenv("TFL_KEY")

API_BASE = "https://api.tfl.gov.uk"


# Fetch all TfL stations
@st.cache_data(ttl=300)
def fetch_stations(api_key):
    modes = ["tube"]
    stations = []

    for mode in modes:
        url = f"{API_BASE}/StopPoint/Mode/{mode}?app_key={api_key}"
        resp = requests.get(url)

        if resp.status_code != 200:
            continue

        for stop in resp.json().get("stopPoints", []):

            if stop.get("stopType") != "NaptanMetroStation":
                continue

            lat = stop.get("lat")
            lon = stop.get("lon")
            naptan = stop.get("naptanId")

            if lat is None or lon is None or not naptan:
                continue

            stations.append({
                "station_name": stop.get("commonName"),
                "lat": lat,
                "lon": lon,
                "naptanId": naptan,
                "lines": [line["name"] for line in stop.get("lines", [])]
            })

    return pd.DataFrame(stations)


stations_df = fetch_stations(API_KEY)


# Fetch TfL disruptions
@st.cache_data(ttl=300)
def fetch_disruptions():
    try:
        url = f'{API_BASE}/Line/Mode/tube,overground,dlr,river-bus/Status'
        response = requests.get(url)
        data = response.json()
        disruptions = []
        for line in data:
            disruptions.append({
                "line_id": line['id'],
                "line_name": line['name'],
                "status": line['lineStatuses'][0]['statusSeverityDescription']
            })
        return pd.DataFrame(disruptions)
    except:
        return pd.DataFrame(columns=["line_id", "line_name", "status"])


df = fetch_disruptions()


# Fetch bus disruptions
@st.cache_data(ttl=300)
def fetch_bus_disruptions(api_key):
    try:
        url = f"{API_BASE}/Line/Mode/bus/Status?app_key={api_key}"
        data = requests.get(url).json()
        disruptions = []
        for line in data:
            line_statuses = line.get('lineStatuses', [])
            status_desc = line_statuses[0]['statusSeverityDescription'] if line_statuses else "Good Service"
            reason = line_statuses[0].get('reason', '') if line_statuses else ''
            disruptions.append({
                "route_name": line['name'],
                "status": status_desc,
                "reason": reason
            })
        return pd.DataFrame(disruptions)
    except:
        return pd.DataFrame(columns=["route_name", "status", "reason"])


bus_disruptions_df = fetch_bus_disruptions(API_KEY)

# Network summary KPIs
st.subheader("📊 Network Summary")

TUBE_LINES = [
    'Bakerloo', 'Central', 'Circle', 'District',
    'Hammersmith & City', 'Jubilee', 'Metropolitan',
    'Northern', 'Piccadilly', 'Victoria', 'Waterloo & City'
]

tube_stations_df = stations_df[
    stations_df['lines'].apply(
        lambda lines: any(line in TUBE_LINES for line in lines)
    )
]

total_stations = stations_df['naptanId'].nunique()

tube_df = df[df['line_name'].isin(TUBE_LINES)]

disrupted_lines = set(
    tube_df[tube_df['status'] != "Good Service"]["line_name"]
)

stations_with_disruptions = tube_stations_df[
    tube_stations_df['lines'].apply(
        lambda lines: any(line in disrupted_lines for line in lines)
    )
]['station_name'].nunique()

total_lines = len(TUBE_LINES)
total_disrupted_lines = len(disrupted_lines)
percent_disrupted_lines = (
    (total_disrupted_lines / total_lines) * 100 if total_lines else 0
)
percent_good = 100 - percent_disrupted_lines

# KPIs
col1, col2, col3, col4 = st.columns(4)

col1.metric("Tube Stations", total_stations)
col2.metric("Stations Affected", stations_with_disruptions)
col3.metric("Tube Lines", total_lines)
col4.metric(
    "Lines Disrupted",
    total_disrupted_lines,
    f"{percent_disrupted_lines:.1f}%"
)


st.markdown("---")

# Line & Status Filters
st.subheader("🎛️ Filter Lines and Status")

line_options = sorted(df['line_name'].unique())

selected_lines = st.multiselect(
    "Choose specific lines to monitor (leave empty to include all):",
    options=line_options,
    default=st.session_state.selected_lines,
    key="lines_focus"
)
st.session_state.selected_lines = selected_lines

status_options = df['status'].unique()
status_filter = st.multiselect(
    "Select status types to display:",
    options=status_options,
    default=status_options,
    key="status_focus"
)

# Apply filters
filtered_df = df[
    (df['line_name'].isin(selected_lines) if selected_lines else True) &
    (df['status'].isin(status_filter))
    ]

st.markdown("---")

# Selected Line Status
st.subheader("🚦 Selected Line Status")
if selected_lines:

    for line in selected_lines:
        row = df[df['line_name'] == line].iloc[0]
        status = row['status']

        if status == "Good Service":
            st.success(f"✅ {line}: {status}")
        elif status in ["Minor Delays", "Service Closed"]:
            st.warning(f"⚠️ {line}: {status}")
        else:
            st.error(f"🚨 {line}: {status}")

st.markdown("---")

# Notifications
st.subheader("🚨 Disruption Alerts")

disruptions = filtered_df[filtered_df['status'] != "Good Service"]

if not disruptions.empty:
    for row in disruptions.itertuples():
        st.warning(f"⚠️ {row.line_name}: {row.status}")
else:
    st.success("✅ All selected lines are running with Good Service.")
st.markdown("---")

# Bus Table
st.subheader("🚌 Bus Disruptions")
st.text("Search for a specific bus route:")
route_input = st.text_input("Route Number", key="route_search")
if route_input:
    route_df = bus_disruptions_df[bus_disruptions_df['route_name'].str.contains(route_input, case=False)]
    if not route_df.empty:
        st.dataframe(route_df[['route_name', 'status', 'reason']].reset_index(drop=True))
    else:
        st.info("No bus routes found matching your search.")


def color_status(val):
    if val == "Good Service":
        return "background-color: #d4edda; color: #155724;"
    elif val == "Minor Delays":
        return "background-color: #fff3cd; color: #856404;"
    elif val == "Severe Delays":
        return "background-color: #f8d7da; color: #721c24;"
    elif val == "Part Closure":
        return "background-color: #FFA500; color: #000000;"
    else:
        return ""


st.dataframe(
    bus_disruptions_df[['route_name', 'status', 'reason']].sort_values("route_name")
    .reset_index(drop=True)
    .style.applymap(color_status, subset=['status'])
)

st.markdown("---")

# Current Disruption Summary

st.subheader("🛑 Current Disruption Summary (Tube, DLR & River Bus)")

status_summary = df.groupby('status')['line_name'].count().reset_index()
status_summary.columns = ['Status', 'Number of Lines']

color_scale = alt.Scale(
    domain=["Good Service", "Minor Delays", "Severe Delays", "Part Closure","Service Closed"],
    range=["green", "orange", "red", "darkred", "purple"]
)

# Create chart
chart = alt.Chart(status_summary).mark_bar().encode(
    x='Status',
    y='Number of Lines',
    color=alt.Color('Status', scale=color_scale),
    tooltip=['Status', 'Number of Lines']
).properties(
    width=700,
    height=400
)

st.altair_chart(chart)

# Disruption by Mode

st.subheader("📊 Disruption by Transport Mode")

tube_lines = ['Bakerloo', 'Central', 'Circle', 'District', 'Hammersmith & City', 'Jubilee',
              'Metropolitan', 'Northern', 'Piccadilly', 'Victoria', 'Waterloo & City']

df['mode'] = df['line_name'].apply(lambda x: 'Tube' if x in tube_lines else 'Other')

# Count disruptions per mode
mode_counts = df.groupby('mode')['status'].apply(lambda x: (x != 'Good Service').sum()).reset_index()
mode_counts.columns = ['Mode', 'Disrupted Lines']

# Plot pie chart
fig = px.pie(mode_counts, names='Mode', values='Disrupted Lines',
             color='Mode',
             color_discrete_map={'Tube': '#1f77b4', 'Other': '#ff7f0e'},
             hole=0.3,
             title="Disrupted Lines by Transport Mode")

st.plotly_chart(fig, use_container_width=True)

# Map Visualisation
st.subheader("🗺️ TfL Stations Status Map")
STATUS_COLOR = {
    "Good Service": "green",
    "Minor Delays": "orange",
    "Severe Delays": "red",
    "Part Closure": "darkred"
}

london_map = folium.Map(location=[51.5074, -0.1278], zoom_start=11, tiles="CartoDB positron")
cluster = MarkerCluster().add_to(london_map)

for _, station in stations_df.iterrows():
    lines_here = station['lines']
    if not lines_here:
        continue
    worst_status = "Good Service"
    for line in lines_here:
        line_row = df[df['line_name'] == line]
        if not line_row.empty:
            line_status = line_row['status'].values[0]
            if line_status == "Severe Delays" or (worst_status != "Severe Delays" and line_status != "Good Service"):
                worst_status = line_status
    color = STATUS_COLOR.get(worst_status, "gray")
    radius = 5 + len(lines_here)
    popup_html = f"<b>{station['station_name']}</b><br><b>Lines:</b><br>"
    for line in lines_here:
        line_row = df[df['line_name'] == line]
        status = line_row['status'].values[0] if not line_row.empty else "Unknown"
        popup_html += f"{line}: {status}<br>"
    folium.CircleMarker(
        location=[station["lat"], station["lon"]],
        radius=radius,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.7,
        popup=folium.Popup(popup_html, max_width=250)
    ).add_to(cluster)

st_folium(london_map, width=1000, height=700)
st.markdown("---")

# Journey Planner
st.subheader("🛤️ Journey Planner")
station_names = stations_df[stations_df['naptanId'].notna()]['station_name'].drop_duplicates().sort_values().tolist()
start_input = st.selectbox("Start Station", options=station_names, key="start_station")
end_input = st.selectbox("End Station", options=station_names, key="end_station")


def get_naptan(station_name):
    match = stations_df[stations_df['station_name'].str.lower() == station_name.lower()]
    if not match.empty:
        return match.iloc[0]['naptanId']
    return None


def format_time(ts_str):
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime("%H:%M")
    except:
        return ts_str


ICON = {
    "Walking": "🚶",
    "Bus": "🚌",
    "Tube": "🚇",
    "Dlr": "🚈",
    "Overground": "🚆",
    "Elizabeth-line": "🚆"
}

if start_input and end_input:
    start_naptan = get_naptan(start_input)
    end_naptan = get_naptan(end_input)

    if start_naptan == end_naptan:
        st.info("Start and end stations are the same.")
    else:
        try:
            journey_url = f"{API_BASE}/Journey/JourneyResults/{start_naptan}/to/{end_naptan}?app_key={API_KEY}"
            resp = requests.get(journey_url, timeout=10)
            if resp.status_code == 200:
                journeys = resp.json().get("journeys", [])
                if journeys:
                    for i, journey in enumerate(journeys):
                        duration = journey.get("duration", "Unknown")
                        st.markdown(f"### Option {i + 1}: {duration} mins")
                        mode_times = {}
                        for leg in journey.get("legs", []):
                            mode = leg.get("mode", {}).get("name", "Unknown").capitalize()
                            line_name = leg.get("line", {}).get("name", "")
                            display_name = f"{mode} {line_name}" if line_name else mode
                            dep = format_time(leg.get("departureTime", ""))
                            arr = format_time(leg.get("arrivalTime", ""))
                            disruption = leg.get("disruption", [])
                            disruption_text = f" ⚠️ {disruption[0].get('description', '')}" if disruption else ""
                            icon = ICON.get(mode, "")
                            st.markdown(f"- {icon} **{display_name}**: {dep} → {arr}{disruption_text}")
                            try:
                                dep_dt = datetime.fromisoformat(leg.get("departureTime"))
                                arr_dt = datetime.fromisoformat(leg.get("arrivalTime"))
                                minutes = int((arr_dt - dep_dt).total_seconds() / 60)
                                mode_times[mode] = mode_times.get(mode, 0) + minutes
                            except:
                                pass
                        summary_text = " | ".join([f"{ICON.get(m, '')} {m}: {t} min" for m, t in mode_times.items()])
                        if summary_text:
                            st.markdown(f"**Mode summary:** {summary_text}")
                        st.markdown("---")
                else:
                    st.info("No journeys found for these stations.")
            else:
                st.error("Error fetching journey data from TfL API.")
        except Exception as e:
            st.error(f"API request failed: {e}")
