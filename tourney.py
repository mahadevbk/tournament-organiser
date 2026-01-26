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
# --- RESILIENT CONNECTION HANDLER ---
def get_connection():
    """
    Creates a connection by cleaning the private key and removing 
    conflicting keyword arguments.
    """
    try:
        # Create a mutable copy
        creds = dict(st.secrets.connections.gsheets)
        
        # 1. Clean the private key
        raw_key = creds.get("private_key", "")
        cleaned_key = raw_key.replace("\\n", "\n")
        
        if "-----BEGIN PRIVATE KEY-----" in cleaned_key and "\n" not in cleaned_key[28:-26]:
            content = cleaned_key.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "").strip()
            wrapped_content = "\n".join(re.findall(r'.{1,64}', content))
            cleaned_key = f"-----BEGIN PRIVATE KEY-----\n{wrapped_content}\n-----END PRIVATE KEY-----\n"
        
        creds["private_key"] = cleaned_key
        
        # 2. REMOVE CONFLICTING KEYS
        # We delete these because they are already defined in the st.connection call
        creds.pop("type", None)
        creds.pop("spreadsheet", None)
        
        # 3. Initialize
        return st.connection(
            "gsheets", 
            type=GSheetsConnection, 
            spreadsheet=st.secrets.connections.gsheets.spreadsheet, # Pass this explicitly
            **creds
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
        st.error(f"Update failed. Ensure you enabled the Google Sheets API and shared the sheet. Error: {e}")
        return False

def generate_bracket(participants):
    players = [str(p).strip() for p in participants if p and str(p).strip() not in ["", "None", "nan"]]
    random.shuffle(players)
    n = len(players)
    if n == 0: return None, 0, 0, False
    
    next_pow_2 = 2**math.ceil(math.log2(n))
    num_byes = next_pow_2 - n
    full_slots = players + (["BYE"] * num_byes)
    
    bracket = []
    for i in range(next_pow_2 // 2):
        bracket.append([full_slots[i], full_slots[next_pow_2 - 1 - i]])
    return bracket, num_byes, next_pow_2, (n == next_pow_2)

# --- MAIN APP ---
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
        st.divider()
        if st.button(f"🗑️ Delete {selected_t}", type="secondary"):
            save_db(df_db[df_db["Tournament"] != selected_t])
            st.rerun()

if selected_t != "-- Select --":
    row = df_db[df_db["Tournament"] == selected_t]
    if not row.empty:
        try:
            t_data = ast.literal_eval(row["Data"].values[0])
        except:
            st.error("Data in spreadsheet is corrupted.")
            st.stop()
        
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
                bracket, byes, size, perf = generate_bracket(t_data["players"])
                t_data["bracket"] = bracket
                t_data["gen_info"] = {"byes": byes, "size": size, "perfect": perf, "total": len(t_data["players"])}
                
                df_db.loc[df_db["Tournament"] == selected_t, "Data"] = str(t_data)
                save_db(df_db)
                st.balloons()
                st.rerun()

        with tab2:
            if t_data.get("bracket"):
                active = [m for m in t_data["bracket"] if "BYE" not in m]
                cols = st.columns(len(t_data["courts"]))
                for i, match in enumerate(active):
                    c_idx = i % len(t_data["courts"])
                    with cols[c_idx]:
                        st.markdown(f"<div class='match-card'><span class='court-header'>📍 {t_data['courts'][c_idx]}</span><b>{match[0]}</b> vs <b>{match[1]}</b></div>", unsafe_allow_html=True)

        with tab3:
            if t_data.get("bracket"):
                st.write("Tournament Bracket Pairings:")
                st.json(t_data["bracket"]) # Displaying the raw bracket for progression tracking
                
                if st.button("💾 Save Progress", disabled=t_data["locked"]):
                    df_db.loc[df_db["Tournament"] == selected_t, "Data"] = str(t_data)
                    save_db(df_db)
                    st.toast("Saved!")
