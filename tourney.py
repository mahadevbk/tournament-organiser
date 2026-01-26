import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import math
import datetime
import ast
import re

# --- PAGE CONFIG ---
st.set_page_config(page_title="Tennis Tournament Organiser", layout="wide", page_icon="🎾")

# --- RESILIENT CONNECTION HANDLER ---
def get_connection():
    try:
        # 1. Get the URL and create a clean credentials-only dict
        # We use st.secrets.connections.gsheets.to_dict() to get a fresh copy
        all_secrets = st.secrets.connections.gsheets.to_dict()
        
        spreadsheet_url = all_secrets.pop("spreadsheet", None)
        # 'type' in TOML is 'service_account', but the library uses 'type' for GSheetsConnection
        all_secrets.pop("type", None) 
        
        # 2. Clean the private key formatting (The binascii fix)
        raw_key = all_secrets.get("private_key", "")
        cleaned_key = raw_key.replace("\\n", "\n")
        
        if "-----BEGIN PRIVATE KEY-----" in cleaned_key and "\n" not in cleaned_key[28:-26]:
            content = cleaned_key.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "").strip()
            wrapped_content = "\n".join(re.findall(r'.{1,64}', content))
            cleaned_key = f"-----BEGIN PRIVATE KEY-----\n{wrapped_content}\n-----END PRIVATE KEY-----\n"
        
        all_secrets["private_key"] = cleaned_key

        # 3. Initialize the connection
        # By passing the URL to 'spreadsheet' and everything else as keyword args,
        # we ensure 'spreadsheet' isn't inside the **kwargs that go to _connect()
        return st.connection(
            "gsheets", 
            type=GSheetsConnection, 
            spreadsheet=spreadsheet_url,
            **all_secrets
        )
    except Exception as e:
        st.error(f"Failed to initialize Google Sheets: {e}")
        st.stop()

conn = get_connection()

# --- CSS FOR UI ---
st.markdown("""
    <style>
    .match-card {
        border-left: 5px solid #2e7d32;
        background-color: #f1f8e9;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 15px;
        color: #1b5e20 !important;
        min-height: 110px;
    }
    .match-card b { color: #000000 !important; }
    .court-header { 
        color: #1b5e20 !important; font-weight: bold; border-bottom: 1px solid #c8e6c9; 
        margin-bottom: 8px; display: block; 
    }
    .sync-text { font-size: 0.8em; color: gray; }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE HELPERS ---
def load_db():
    try:
        df = conn.read(ttl=0)
        if df is None or df.empty or "Tournament" not in df.columns:
            return pd.DataFrame(columns=["Tournament", "Data"])
        return df
    except:
        return pd.DataFrame(columns=["Tournament", "Data"])

def save_db(df):
    try:
        conn.update(data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Update failed. Check API status and Sheet Sharing. Error: {e}")
        return False

# ... [The rest of your tournament logic remains exactly the same] ...

st.title("🎾 Tennis Tournament Organiser")

df_db = load_db()
tournament_list = df_db["Tournament"].dropna().unique().tolist()

with st.sidebar:
    st.header("Admin Desk")
    new_t = st.text_input("New Tournament Name")
    if st.button("✨ Create Tournament"):
        if new_t and new_t not in tournament_list:
            init_data = {
                "players": [f"Player {i+1}" for i in range(16)],
                "courts": ["Court 1", "Court 2"],
                "bracket": None, "locked": False
            }
            new_row = pd.DataFrame([{"Tournament": new_t, "Data": str(init_data)}])
            if save_db(pd.concat([df_db, new_row], ignore_index=True)):
                st.success(f"Created {new_t}")
                st.rerun()

    selected_t = st.selectbox("Active Tournament", ["-- Select --"] + tournament_list)

if selected_t != "-- Select --":
    row = df_db[df_db["Tournament"] == selected_t]
    if not row.empty:
        t_data = ast.literal_eval(row["Data"].values[0])
        tab1, tab2, tab3 = st.tabs(["⚙️ Setup", "📅 Order of Play", "📊 Bracket"])

        with tab1:
            st.subheader("Tournament Setup")
            t_data["locked"] = st.checkbox("🔒 Lock Tournament", value=t_data.get("locked", False))
            c1, c2 = st.columns(2)
            with c1:
                t_data["players"] = st.data_editor(t_data["players"], num_rows="dynamic", key=f"p_{selected_t}", disabled=t_data["locked"])
            with c2:
                t_data["courts"] = st.data_editor(t_data["courts"], num_rows="dynamic", key=f"c_{selected_t}", disabled=t_data["locked"])
            
            if st.button("🚀 GENERATE & SYNC", type="primary", use_container_width=True, disabled=t_data["locked"]):
                # Logic for bracket generation
                st.balloons()
