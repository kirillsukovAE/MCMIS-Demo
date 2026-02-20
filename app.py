import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd

# Initialize session state for your data
if 'fleets' not in st.session_state:
    st.session_state.fleets = None

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
    # Ensure we insert a clean string without spaces
    clean_dot = str(dot_number).strip()
    query = f"INSERT INTO `mcmis-february.MCMISFEB.favorites` (DOT_NUMBER) VALUES ('{clean_dot}')"
    client.query(query).result()
    st.cache_data.clear()

def remove_favorite(dot_number):
    clean_dot = str(dot_number).strip()
    query = f"DELETE FROM `mcmis-february.MCMISFEB.favorites` WHERE TRIM(DOT_NUMBER) = '{clean_dot}'"
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
            t.POWER_UNITS, 
            t.PHY_CITY, 
            t.PHY_STATE 
        FROM `{TABLE_ID}` AS t
        LEFT JOIN `mcmis-february.MCMISFEB.favorites` AS f 
            ON TRIM(CAST(t.DOT_NUMBER AS STRING)) = TRIM(CAST(f.DOT_NUMBER AS STRING))
        WHERE t.POWER_UNITS BETWEEN {min_v} AND {max_v}
        AND {filter_condition}
        {state_clause}
        LIMIT 100
    """
    return client.query(query).to_dataframe()

if st.checkbox("Debug: Show Favorites Table"):
    fav_check = client.query("SELECT * FROM `mcmis-february.MCMISFEB.favorites`").to_dataframe()
    st.write(fav_check)

# --- 3. SIDEBAR FILTERS ---
st.sidebar.header("Filter Settings")

# Vehicle Range
fleet_range = st.sidebar.slider("Number of Vehicles", 0, 5000, (10, 100))

# States (Manual list for now, or you can query unique states from BQ)
all_states = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY']
selected_states = st.sidebar.multiselect("Select States", all_states)


# --- 3. UI IMPLEMENTATION ---
st.sidebar.header("View Mode")
mode = st.sidebar.radio("Show:", ["New Leads", "My Favorites"])

# A. Initialize state trackers for immediate UI feedback
if 'just_favorited' not in st.session_state:
    st.session_state.just_favorited = set()
if 'just_unfavorited' not in st.session_state:
    st.session_state.just_unfavorited = set()

# B. Handle Mode Switching
if "last_mode" not in st.session_state:
    st.session_state.last_mode = mode

if st.session_state.last_mode != mode:
    st.session_state.fleets = None 
    st.session_state.last_mode = mode
    # Clear the temporary toggles when moving between main tabs
    st.session_state.just_favorited = set()
    st.session_state.just_unfavorited = set()
    st.rerun()

# 1. Action Trigger
if st.button("Find Fleets / Refresh List"):
    # Clear temporary toggles on a fresh database pull
    st.session_state.just_favorited = set()
    st.session_state.just_unfavorited = set()
    
    is_fav_view = (mode == "My Favorites")
    with st.spinner("Fetching data..."):
        st.session_state.fleets = get_data(
            fleet_range[0], 
            fleet_range[1], 
            selected_states, 
            show_favorites=is_fav_view
        )

# 2. Persistent Display Loop
if st.session_state.fleets is not None:
    df = st.session_state.fleets
    
    if df.empty:
        st.info(f"No results found in {mode}.")
    else:
        st.metric(f"Companies in {mode}", len(df))
        
        for index, row in df.iterrows():
            dot = str(row['DOT_NUMBER']).strip()
            col1, col2 = st.columns([4, 1])
            
            # Logic to determine if we should show Favorite or Unfavorite button
            # This checks the DB source AND the local "just changed" memory
            is_fav = (mode == "My Favorites" or dot in st.session_state.just_favorited)
            if dot in st.session_state.just_unfavorited:
                is_fav = False

            with col1:
                st.write(f"**{row['LEGAL_NAME']}** ({dot})")
                st.caption(f"{row['PHY_CITY']}, {row['PHY_STATE']} | Units: {row['POWER_UNITS']}")
            
            with col2:
                if is_fav:
                    if st.button("❌ Unfavorite", key=f"unfav_{dot}"):
                        remove_favorite(dot)
                        st.session_state.just_unfavorited.add(dot)
                        if dot in st.session_state.just_favorited:
                            st.session_state.just_favorited.remove(dot)
                        st.rerun()
                else:
                    if st.button("⭐ Favorite", key=f"fav_{dot}"):
                        add_favorite(dot)
                        st.session_state.just_favorited.add(dot)
                        if dot in st.session_state.just_unfavorited:
                            st.session_state.just_unfavorited.remove(dot)
                        st.rerun()
            st.divider()
