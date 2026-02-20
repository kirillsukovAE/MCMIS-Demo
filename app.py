import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd

st.set_page_config(page_title="MCMIS Fleet Finder", layout="wide")
st.title("🚛 MCMIS Fleet Finder")

# --- 1. AUTHENTICATION ---
# This uses the secrets you pasted into the Streamlit Cloud dashboard
creds_dict = st.secrets["gcp_service_account"]
credentials = service_account.Credentials.from_service_account_info(creds_dict)
client = bigquery.Client(credentials=credentials, project=creds_dict['project_id'])

TABLE_ID = "mcmis-february.MCMISFEB.Feb"


# --- 1. NEW FUNCTIONS FOR FAVORITES ---

def add_favorite(dot_number):
    query = f"INSERT INTO `mcmis-february.MCMISFEB.favorites` (DOT_NUMBER) VALUES ('{dot_number}')"
    client.query(query).result()
    st.cache_data.clear() # Clear cache so the company disappears from search immediately

def remove_favorite(dot_number):
    query = f"DELETE FROM `mcmis-february.MCMISFEB.favorites` WHERE DOT_NUMBER = '{dot_number}'"
    client.query(query).result()
    st.cache_data.clear()

@st.cache_data(ttl=600)
def get_data(min_v, max_v, states, show_favorites=False):
    # Determine if we are filtering OUT favorites or ONLY showing favorites
    filter_condition = "f.DOT_NUMBER IS NULL" if not show_favorites else "f.DOT_NUMBER IS NOT NULL"
    
    state_clause = ""
    if states:
        state_list = ", ".join([f"'{s}'" for s in states])
        state_clause = f"AND t.PHY_STATE IN ({state_list})"

    query = f"""
        SELECT 
            t.DOT_NUMBER, 
            t.LEGAL_NAME, 
            t.TOTAL_POWER_UNITS, 
            t.PHY_CITY, 
            t.PHY_STATE 
        FROM `{TABLE_ID}` AS t
        LEFT JOIN `mcmis-february.mcmisfeb.favorites` AS f 
            ON CAST(t.DOT_NUMBER AS STRING) = CAST(f.DOT_NUMBER AS STRING)
        WHERE t.TOTAL_POWER_UNITS BETWEEN {min_v} AND {max_v}
        AND {filter_condition}
        {state_clause}
        LIMIT 100
    """
    return client.query(query).to_dataframe()

# --- 3. UI IMPLEMENTATION ---
st.sidebar.header("View Mode")
mode = st.sidebar.radio("Show:", ["New Leads", "My Favorites"])

if st.button("Refresh List"):
    is_fav_view = (mode == "My Favorites")
    df = get_data(fleet_range[0], fleet_range[1], selected_states, show_favorites=is_fav_view)
    
    for index, row in df.iterrows():
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"**{row['LEGAL_NAME']}** ({row['DOT_NUMBER']})")
            st.caption(f"{row['PHY_CITY']}, {row['PHY_STATE']} | Units: {row['TOTAL_POWER_UNITS']}")
        with col2:
            if mode == "New Leads":
                if st.button("⭐ Favorite", key=f"fav_{row['DOT_NUMBER']}"):
                    add_favorite(row['DOT_NUMBER'])
                    st.rerun()
            else:
                if st.button("❌ Unfavorite", key=f"unfav_{row['DOT_NUMBER']}"):
                    remove_favorite(row['DOT_NUMBER'])
                    st.rerun()
        st.divider()


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
