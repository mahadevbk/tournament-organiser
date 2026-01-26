import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import math
import ast
import re

# --- PAGE CONFIG ---
st.set_page_config(page_title="Tennis Tournament Organiser", layout="wide", page_icon="🎾")

# --- THE ULTIMATE KEY FIX ---
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

# --- CUSTOM THEME CSS ---
st.markdown(f"""
    <style>
    /* Main Background & Font */
    .stApp {{
        background-color: #001e5c;
        font-family: 'sans serif';
    }}
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 24px;
        background-color: #022e85;
        padding: 10px 20px;
        border-radius: 10px;
    }}

    .stTabs [data-baseweb="tab"] {{
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px;
        color: #ffffff;
        font-weight: 600;
    }}

    .stTabs [aria-selected="true"] {{
        background-color: #001e5c !important;
        border-bottom: 2px solid #4ade80 !important;
    }}

    /* Match Cards (Glassmorphism) */
    .match-card {{
        background: rgba(2, 46, 133, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        transition: transform 0.2s;
    }}
    
    .match-card:hover {{
        transform: translateY(-3px);
        border: 1px solid #4ade80;
    }}

    .court-header {{ 
        color: #4ade80 !important; 
        font-size: 0.8em;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 10px;
        display: block; 
    }}

    .player-name {{
        color: #ffffff;
        font-size: 1.1em;
        font-weight: 500;
    }}

    .vs-text {{
        color: rgba(255,255,255,0.4);
        margin: 0 10px;
        font-style: italic;
    }}

    /* Buttons */
    .stButton>button {{
        border-radius: 8px;
        font-weight: 600;
    }}
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
    st.header("Tournament Management")
    new_t = st.text_input("Name")
    if st.button("✨ Create New"):
        if new_t and new_t not in tournament_list:
            init_data = {"players": [f"Player {i+1}" for i in range(8)], "courts": ["Court 1"], "bracket": None, "winners": {}, "locked": False}
            new_row = pd.DataFrame([{"Tournament": new_t, "Data": str(init_data)}])
            if save_db(pd.concat([df_db, new_row], ignore_index=True)):
                st.rerun()

    selected_t = st.selectbox("Select Active", ["-- Select --"] + tournament_list)
    
    if selected_t != "-- Select --":
        st.divider()
        if st.button(f"🗑️ Delete Tournament", type="secondary", use_container_width=True):
            updated_df = df_db[df_db["Tournament"] != selected_t]
            if save_db(updated_df):
                st.rerun()

if selected_t != "-- Select --":
    row = df_db[df_db["Tournament"] == selected_t]
    if not row.empty:
        t_data = ast.literal_eval(row["Data"].values[0])
        if "winners" not in t_data: t_data["winners"] = {}
        
        tab1, tab2, tab3 = st.tabs(["⚙️ SETUP", "📅 ORDER OF PLAY", "📊 BRACKET TREE"])

        with tab1:
            st.markdown("### Configure Participants & Courts")
            t_data["locked"] = st.toggle("🔒 Lock Tournament Data", value=t_data.get("locked", False))
            
            c1, c2 = st.columns(2)
            with c1: 
                st.write("Players")
                t_data["players"] = st.data_editor(t_data["players"], num_rows="dynamic", key=f"p_{selected_t}", disabled=t_data["locked"], use_container_width=True)
            with c2: 
                st.write("Courts")
                t_data["courts"] = st.data_editor(t_data["courts"], num_rows="dynamic", key=f"c_{selected_t}", disabled=t_data["locked"], use_container_width=True)
            
            if st.button("🚀 RANDOMIZE & GENERATE BRACKET", type="primary", use_container_width=True, disabled=t_data["locked"]):
                t_data["bracket"] = generate_bracket(t_data["players"])
                t_data["winners"] = {}
                df_db.loc[df_db["Tournament"] == selected_t, "Data"] = str(t_data)
                if save_db(df_db):
                    st.balloons()
                    st.rerun()

        with tab2:
            if t_data.get("bracket"):
                active = [m for m in t_data["bracket"] if "BYE" not in m]
                if not active:
                    st.info("All matches in this round contain BYEs.")
                else:
                    cols = st.columns(len(t_data["courts"]))
                    for i, match in enumerate(active):
                        c_idx = i % len(t_data["courts"])
                        with cols[c_idx]:
                            st.markdown(f"""
                                <div class='match-card'>
                                    <span class='court-header'>📍 {t_data['courts'][c_idx]}</span>
                                    <span class='player-name'>{match[0]}</span>
                                    <span class='vs-text'>vs</span>
                                    <span class='player-name'>{match[1]}</span>
                                </div>
                            """, unsafe_allow_html=True)
            else:
                st.info("Please generate the bracket in the Setup tab.")

        with tab3:
            if t_data.get("bracket"):
                current_round = t_data["bracket"]
                round_num = 1
                
                while len(current_round) >= 1:
                    st.markdown(f"#### Round {round_num}")
                    cols = st.columns(len(current_round))
                    next_round_players = []
                    
                    for i, match in enumerate(current_round):
                        with cols[i]:
                            p1, p2 = match[0], match[1]
                            
                            if p2 == "BYE":
                                st.markdown(f"✅ **{p1}** (BYE)")
                                next_round_players.append(p1)
                            elif p1 == "TBD" or p2 == "TBD":
                                st.caption("Waiting for results...")
                                next_round_players.append("TBD")
                            else:
                                key = f"r{round_num}_m{i}_{selected_t}"
                                default_idx = 0
                                if key in t_data["winners"]:
                                    try: default_idx = [None, p1, p2].index(t_data["winners"][key])
                                    except: default_idx = 0
                                
                                winner = st.selectbox(f"Winner:", [None, p1, p2], index=default_idx, key=key, disabled=t_data["locked"], label_visibility="collapsed")
                                t_data["winners"][key] = winner
                                next_round_players.append(winner if winner else "TBD")
                                st.markdown(f"**{p1}** vs **{p2}**")
                    
                    if len(next_round_players) > 1:
                        current_round = [next_round_players[j:j+2] for j in range(0, len(next_round_players), 2)]
                        round_num += 1
                        st.divider()
                    else:
                        st.divider()
                        if next_round_players[0] != "TBD" and next_round_players[0] is not None:
                            st.success(f"🏆 **Champion: {next_round_players[0]}**")
                        break
                
                if st.button("💾 SAVE PROGRESS", use_container_width=True):
                    df_db.loc[df_db["Tournament"] == selected_t, "Data"] = str(t_data)
                    save_db(df_db)
                    st.toast("Cloud Synced!")
