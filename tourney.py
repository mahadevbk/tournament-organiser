import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import math
import time
import ast

# --- PAGE CONFIG ---
st.set_page_config(page_title="Tennis Tourney Hub", layout="wide", page_icon="🎾")

# --- INITIALIZE CONNECTION ---
# This looks for [connections.gsheets] in your Streamlit Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CSS FOR UI ---
st.markdown("""
    <style>
    .match-card {
        border-left: 5px solid #2e7d32;
        background-color: #f1f8e9;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 15px;
        min-height: 100px;
        color: #1b5e20 !important;
    }
    .match-card b { color: #000000 !important; }
    .court-header { 
        color: #1b5e20 !important; 
        font-weight: bold; 
        border-bottom: 1px solid #c8e6c9; 
        margin-bottom: 10px;
        display: block; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE LOGIC ---
def load_db():
    try:
        # ttl=0 ensures we don't look at cached/old versions of the sheet
        return conn.read(ttl=0)
    except Exception:
        return pd.DataFrame(columns=["Tournament", "Data"])

def save_db(df):
    # This sends the entire dataframe back to Google Sheets
    conn.update(data=df)
    st.cache_data.clear()

def generate_bracket(participants):
    # Strict filter: no empty strings, no 'None', no 'nan'
    shuffled = [str(p).strip() for p in participants if p and str(p).strip() not in ["", "None", "nan", "None"]]
    random.shuffle(shuffled)
    n = len(shuffled)
    if n == 0: return None, 0, 0, False
    
    next_pow_2 = 2**math.ceil(math.log2(n))
    num_byes = next_pow_2 - n
    full_slots = shuffled + (["BYE"] * num_byes)
    
    bracket = []
    for i in range(next_pow_2 // 2):
        bracket.append([full_slots[i], full_slots[next_pow_2 - 1 - i]])
    return bracket, num_byes, next_pow_2, (n == next_pow_2)

# --- MAIN INTERFACE ---
st.title("🎾 Tennis Persistent Hub")

# Load data from the sheet immediately
df_db = load_db()
tournament_list = df_db["Tournament"].unique().tolist()

with st.sidebar:
    st.header("Admin Desk")
    new_t_name = st.text_input("New Tournament Name")
    if st.button("✨ Create New"):
        if new_t_name and new_t_name not in tournament_list:
            new_data = {
                "players": [f"player {i+1}" for i in range(17)],
                "courts": ["Court 1", "Court 2"],
                "bracket": None, "gen_info": {}, "locked": False
            }
            new_row = pd.DataFrame([{"Tournament": new_t_name, "Data": str(new_data)}])
            df_updated = pd.concat([df_db, new_row], ignore_index=True)
            save_db(df_updated)
            st.rerun()

    selected_t = st.selectbox("Select Tournament", ["-- Select --"] + tournament_list)
    
    if selected_t != "-- Select --":
        st.divider()
        if st.button(f"🗑️ Delete {selected_t}", type="secondary"):
            df_updated = df_db[df_db["Tournament"] != selected_t]
            save_db(df_updated)
            st.rerun()

if selected_t != "-- Select --":
    # Extract the dictionary string and convert it back to a Python object
    raw_str = df_db[df_db["Tournament"] == selected_t]["Data"].values[0]
    t_data = ast.literal_eval(raw_str)
    
    tab1, tab2, tab3 = st.tabs(["⚙️ Setup", "📅 Order of Play", "📊 Bracket"])

    with tab1:
        st.subheader("Tournament Setup")
        t_data["locked"] = st.checkbox("🔒 Lock Results & Setup", value=t_data.get("locked", False))
        
        c1, c2 = st.columns(2)
        with c1:
            t_data["players"] = st.data_editor(t_data["players"], num_rows="dynamic", key=f"p_{selected_t}", disabled=t_data["locked"])
        with c2:
            t_data["courts"] = st.data_editor(t_data["courts"], num_rows="dynamic", key=f"c_{selected_t}", disabled=t_data["locked"])
        
        if st.button("🚀 GENERATE & SYNC", type="primary", use_container_width=True, disabled=t_data["locked"]):
            with st.status("Writing to Google Sheets...") as s:
                bracket, byes, size, perfect = generate_bracket(t_data["players"])
                t_data["bracket"] = bracket
                t_data["gen_info"] = {"byes": byes, "size": size, "perfect": perfect, "total": len([p for p in t_data["players"] if p])}
                
                # Update the main dataframe and save
                df_db.loc[df_db["Tournament"] == selected_t, "Data"] = str(t_data)
                save_db(df_db)
                s.update(label="Cloud Sync Complete!", state="complete")
            st.balloons()
            st.rerun()

    with tab2:
        if not t_data.get("bracket"):
            st.warning("Please generate the bracket in Setup.")
        else:
            info = t_data["gen_info"]
            if not info.get("perfect"):
                st.warning(f"⚠️ **Power of 2 Check:** Scale to {info.get('size')} with {info.get('byes')} byes.")
            
            active_matches = [m for m in t_data["bracket"] if "BYE" not in m]
            if active_matches:
                cols = st.columns(len(t_data["courts"]))
                for i, match in enumerate(active_matches):
                    c_idx = i % len(t_data["courts"])
                    with cols[c_idx]:
                        st.markdown(f"<div class='match-card'><span class='court-header'>📍 {t_data['courts'][c_idx]}</span><b>{match[0]}</b> vs <b>{match[1]}</b></div>", unsafe_allow_html=True)

    with tab3:
        if not t_data.get("bracket"):
            st.warning("Generate the tournament first.")
        else:
            current_round = t_data["bracket"]
            round_idx = 1
            while len(current_round) >= 1:
                st.subheader(f"Round {round_idx}")
                cols = st.columns(len(current_round))
                next_round = []
                for i, match in enumerate(current_round):
                    with cols[i]:
                        p1, p2 = match[0], match[1]
                        st.write(f"**{p1}** vs **{p2}**")
                        if p2 == "BYE": next_round.append(p1)
                        elif "TBD" in [p1, p2]: next_round.append("TBD")
                        else:
                            win = st.selectbox("Winner", ["-", p1, p2], key=f"r{round_idx}m{i}{selected_t}", disabled=t_data["locked"])
                            next_round.append(win if win != "-" else "TBD")
                st.divider()
                if len(next_round) > 1:
                    current_round = [next_round[j:j+2] for j in range(0, len(next_round), 2)]
                    round_idx += 1
                else:
                    if next_round[0] not in ["TBD", "-"]:
                        st.success(f"🏆 Champion: {next_round[0]}")
                    break
            
            if st.button("💾 Save Progress to Cloud", disabled=t_data["locked"]):
                df_db.loc[df_db["Tournament"] == selected_t, "Data"] = str(t_data)
                save_db(df_db)
                st.toast("Saved!")
