import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd

creds_dict = st.secrets["gcp_service_account"]
credentials = service_account.Credentials.from_service_account_info(creds_dict)
client = bigquery.Client(credentials=credentials, project=creds_dict['project_id'])

# Page setup
st.set_page_config(page_title="MCMIS Fleet Finder", layout="wide")

st.title("🚛 MCMIS Fleet Filter")

# 1. Load Data
@st.cache_data
def load_mcmis_data():
    # Replace 'mcmis_data.csv' with your actual filename
    df = pd.read_csv('mcmis_data.csv', low_memory=False)
    # Clean up column names and ensure vehicle count is a number
    df['TOTAL_POWER_UNITS'] = pd.to_numeric(df['TOTAL_POWER_UNITS'], errors='coerce').fillna(0)
    return df

try:
    df = load_mcmis_data()

    # 2. Sidebar Filters
    st.sidebar.header("Filter Settings")
    
    # Range slider for fleet size
    max_units = int(df['TOTAL_POWER_UNITS'].max())
    fleet_range = st.sidebar.slider(
        "Number of Power Units (Vehicles)",
        0, max_units, (10, 100)
    )

    # State filter
    states = sorted(df['PHY_STATE'].dropna().unique())
    selected_states = st.sidebar.multiselect("Select States", states, default=None)

    # 3. Apply Filters
    filtered = df[
        (df['TOTAL_POWER_UNITS'] >= fleet_range[0]) & 
        (df['TOTAL_POWER_UNITS'] <= fleet_range[1])
    ]
    
    if selected_states:
        filtered = filtered[filtered['PHY_STATE'].isin(selected_states)]

    # 4. Display Results
    st.metric("Companies Found", len(filtered))
    
    # Select columns to display so it's not overwhelming
    display_cols = ['DOT_NUMBER', 'LEGAL_NAME', 'TOTAL_POWER_UNITS', 'PHY_CITY', 'PHY_STATE']
    st.dataframe(filtered[display_cols], use_container_width=True)

except FileNotFoundError:
    st.error("⚠️ **mcmis_data.csv not found.** Please upload your data file to this GitHub repo!")
