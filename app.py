import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd

st.set_page_config(page_title="MCMIS Fleet Finder", layout="wide")
st.title("🚛 MCMIS Fleet Filter")

# --- 1. AUTHENTICATION ---
# This uses the secrets you pasted into the Streamlit Cloud dashboard
creds_dict = st.secrets["gcp_service_account"]
credentials = service_account.Credentials.from_service_account_info(creds_dict)
client = bigquery.Client(credentials=credentials, project=creds_dict['project_id'])

# --- 2. DATA LOADING FUNCTION ---
@st.cache_data(ttl=600)
def get_data(min_v, max_v, states):
    # Construct the state filter SQL
    state_filter = ""
    if states:
        state_list = ", ".join([f"'{s}'" for s in states])
        state_filter = f"AND PHY_STATE IN ({state_list})"

    # CHANGE THIS LINE: Put your actual BigQuery Table ID here!
    table_id = "mcmis-february.mcmisfeb.feb"

    query = f"""
        SELECT DOT_NUMBER, LEGAL_NAME, TOTAL_POWER_UNITS, PHY_CITY, PHY_STATE 
        FROM `{table_id}`
        WHERE TOTAL_POWER_UNITS BETWEEN {min_v} AND {max_v}
        {state_filter}
        LIMIT 1000
    """
    return client.query(query).to_dataframe()

# --- 3. SIDEBAR FILTERS ---
st.sidebar.header("Filter Settings")

# Vehicle Range
fleet_range = st.sidebar.slider("Number of Vehicles", 0, 5000, (10, 100))

# States (Manual list for now, or you can query unique states from BQ)
all_states = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY']
selected_states = st.sidebar.multiselect("Select States", all_states)

# --- 4. EXECUTION & DISPLAY ---
if st.button("Find Fleets"):
    with st.spinner("Searching BigQuery..."):
        try:
            df = get_data(fleet_range[0], fleet_range[1], selected_states)
            
            st.metric("Companies Found", len(df))
            st.dataframe(df, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error: {e}")
