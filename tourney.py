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

# --- THE ULTIMATE KEY FIX (RETAINED) ---
if "connections" in st.secrets and "gsheets" in st.secrets.connections:
    raw_key = st.secrets.connections.gsheets.private_key
    cleaned_key = raw_key.replace("\\n", "\n")
    if "-----BEGIN PRIVATE KEY-----" in cleaned_key and "\n" not in cleaned_key[28:-26]:
        header = "-----BEGIN PRIVATE KEY-----\n"
        footer = "\n-----END PRIVATE KEY-----"
        content = cleaned_key.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "").strip()
        wrapped_content = "\n".join(re.findall(r'.{1,64}', content))
        cleaned_key = f"{header}{wrapped_content}{footer}\n"
    try:
        st.secrets.connections.gsheets["private_key"] = cleaned_key
    except:
        pass

# --- INITIALIZE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CSS FOR UI ---
st.markdown("""
    <style>
    .match-card {
        border-left: 5px solid #2e7d32; background-color: #f1f8e9;
        padding: 15px; border-radius: 5px; margin-bottom: 15px;
        color: #1b5e20 !important; min-height: 110px;
    }
    .match-card b { color: #000000 !important; }
    .court-header { 
        color: #1b5e20 !important; font-weight: bold; border-bottom: 1px solid #c8e6c9; 
        margin-bottom: 8px; display: block; 
    }
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
        st.error(f"Sync Error: {e}")
        return False

def generate_bracket(participants):
    players = [str(p).strip() for p in participants if p and str(p).strip() not in ["", "None", "nan"]]
    random.shuffle(players)
    n = len(players)
    if n == 0: return None
    next_pow_2 = 2**math.ceil(math.log2(n))
    full_slots = players + (["BYE"] * (next_pow_2 - n))
    bracket = []
    for i in range(next_pow_2 // 2):
        bracket.append([full_slots[i], full_slots[next_pow_2 - 1 - i]])
    return bracket

# --- MAIN APP ---
st.title("🎾 Tennis Tournament Organiser")

df_db = load_db()
tournament_list = df_db["Tournament"].dropna().unique().tolist()

with st.sidebar:
    st.header("Admin Desk")
    new_t = st.text_input("New Tournament Name")
    if st.button("✨ Create Tournament"):
        if new_t and new_t not in tournament_list:
            init_data = {"players": [f"Player {i+1}" for i in range(8)], "courts": ["Court 1"], "bracket": None, "winners": {}, "locked": False}
            new_row = pd.DataFrame([{"Tournament": new_t, "Data": str(init_data)}])
            if save_db(pd.concat([df_db, new_row], ignore_index=True)):
                st.rerun()

    selected_t = st.selectbox("Active Tournament", ["-- Select --"] + tournament_list)
    
    # --- DELETE OPTION (RESTORED) ---
    if selected_t != "-- Select --":
        st.divider()
        if st.button(f"🗑️ Delete {selected_t}", type="secondary"):
            updated_df = df_db[df_db["Tournament"] != selected_t]
            if save_db(updated_df):
                st.rerun()

if selected_t != "-- Select --":
    row = df_db[df_db["Tournament"] == selected_t]
    if not row.empty:
        t_data = ast.literal_eval(row["Data"].values[0])
        # Ensure winners dict exists
        if "winners" not in t_data: t_data["winners"] = {}
        
        tab1, tab2, tab3 = st.tabs(["⚙️ Setup", "📅 Order of Play", "📊 Bracket"])

        with tab1:
            st.subheader("Tournament Setup")
            t_data["locked"] = st.checkbox("🔒 Lock Tournament", value=t_data.get("locked", False))
            c1, c2 = st.columns(2)
            with c1: t_data["players"] = st.data_editor(t_data["players"], num_rows="dynamic", key=f"p_{selected_t}", disabled=t_data["locked"])
            with c2: t_data["courts"] = st.data_editor(t_data["courts"], num_rows="dynamic", key=f"c_{selected_t}", disabled=t_data["locked"])
            
            if st.button("🚀 GENERATE & SYNC", type="primary", use_container_width=True, disabled=t_data["locked"]):
                t_data["bracket"] = generate_bracket(t_data["players"])
                t_data["winners"] = {} # Reset winners for new bracket
                df_db.loc[df_db["Tournament"] == selected_t, "Data"] = str(t_data)
                if save_db(df_db):
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
            else:
                st.info("No bracket generated yet.")

        with tab3:
            if t_data.get("bracket"):
                # --- INTERACTIVE BRACKET LOGIC (RESTORED) ---
                current_round = t_data["bracket"]
                round_num = 1
                
                while len(current_round) >= 1:
                    st.subheader(f"Round {round_num}")
                    cols = st.columns(len(current_round))
                    next_round_players = []
                    
                    for i, match in enumerate(current_round):
                        with cols[i]:
                            p1, p2 = match[0], match[1]
                            
                            if p2 == "BYE":
                                st.success(f"⏩ {p1} advances")
                                next_round_players.append(p1)
                            elif p1 == "TBD" or p2 == "TBD":
                                st.info("Waiting for previous round...")
                                next_round_players.append("TBD")
                            else:
                                key = f"r{round_num}_m{i}_{selected_t}"
                                # Load saved winner if exists
                                default_idx = 0
                                if key in t_data["winners"]:
                                    default_idx = [None, p1, p2].index(t_data["winners"][key])
                                
                                winner = st.selectbox(f"{p1} vs {p2}", [None, p1, p2], index=default_idx, key=key, disabled=t_data["locked"])
                                t_data["winners"][key] = winner
                                next_round_players.append(winner if winner else "TBD")
                    
                    if len(next_round_players) > 1:
                        # Pair up winners for the next round
                        current_round = [next_round_players[j:j+2] for j in range(0, len(next_round_players), 2)]
                        round_num += 1
                        st.divider()
                    else:
                        st.divider()
                        if next_round_players[0] != "TBD":
                            st.balloons()
                            st.success(f"🏆 Tournament Champion: **{next_round_players[0]}**")
                        break
                
                if st.button("💾 Save Winner Progress", use_container_width=True):
                    df_db.loc[df_db["Tournament"] == selected_t, "Data"] = str(t_data)
                    save_db(df_db)
                    st.toast("Progress Saved to Cloud!")
