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

# --- INITIALIZE CONNECTION ---
# This looks for [connections.gsheets] in your Streamlit Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CSS FOR UI VISIBILITY ---
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
        color: #1b5e20 !important; 
        font-weight: bold; 
        border-bottom: 1px solid #c8e6c9; 
        margin-bottom: 8px;
        display: block; 
    }
    .sync-text { font-size: 0.85em; color: #666; font-style: italic; }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE HELPERS ---
def load_db():
    try:
        df = conn.read(ttl=0)
        # If the sheet is empty or missing columns, create them
        if df.empty or "Tournament" not in df.columns:
            return pd.DataFrame(columns=["Tournament", "Data"])
        return df
    except Exception as e:
        # If we can't even read the sheet, return the structure we need
        return pd.DataFrame(columns=["Tournament", "Data"])

def save_db(df):
    """Writes the entire dataframe back to the Google Sheet."""
    conn.update(data=df)
    st.cache_data.clear()

def generate_bracket(participants):
    """Tournament logic to handle Byes and Randomization."""
    # Strict filter: Remove empty entries, 'None', or 'nan'
    players = [str(p).strip() for p in participants if p and str(p).strip() not in ["", "None", "nan"]]
    random.shuffle(players)
    n = len(players)
    if n == 0: return None, 0, 0, False
    
    # Calculate next power of 2 for bracket size
    next_pow_2 = 2**math.ceil(math.log2(n))
    num_byes = next_pow_2 - n
    full_slots = players + (["BYE"] * num_byes)
    
    bracket = []
    # Seed pairings (1 vs Last, 2 vs 2nd Last, etc.)
    for i in range(next_pow_2 // 2):
        bracket.append([full_slots[i], full_slots[next_pow_2 - 1 - i]])
    return bracket, num_byes, next_pow_2, (n == next_pow_2)

# --- MAIN APP ---
st.title("🎾 Tennis Tournament Organiser")

# Fetch database state
df_db = load_db()
tournament_list = df_db["Tournament"].unique().tolist()

# --- SIDEBAR MANAGEMENT ---
with st.sidebar:
    st.header("Tournament Admin")
    new_t_name = st.text_input("New Tournament Name")
    if st.button("✨ Create New Tournament"):
        if new_t_name and new_t_name not in tournament_list:
            initial_data = {
                "players": [f"Player {i+1}" for i in range(16)],
                "courts": ["Court 1", "Court 2"],
                "bracket": None, "gen_info": {}, "locked": False
            }
            new_row = pd.DataFrame([{"Tournament": new_t_name, "Data": str(initial_data)}])
            save_db(pd.concat([df_db, new_row], ignore_index=True))
            st.success(f"'{new_t_name}' created!")
            st.rerun()

    selected_t = st.selectbox("Active Tournament", ["-- Select --"] + tournament_list)
    
    if selected_t != "-- Select --":
        st.divider()
        if st.button(f"🗑️ Delete {selected_t}", type="secondary", use_container_width=True):
            save_db(df_db[df_db["Tournament"] != selected_t])
            st.rerun()
        
        # Display Sync Status
        now = datetime.datetime.now().strftime("%H:%M:%S")
        st.markdown(f"<p class='sync-text'>Cloud Sync active: {now}</p>", unsafe_allow_html=True)

# --- TOURNAMENT INTERFACE ---
if selected_t == "-- Select --":
    st.info("👈 Please select or create a tournament in the sidebar to begin.")
else:
    # Safely load the tournament dictionary
    raw_val = df_db[df_db["Tournament"] == selected_t]["Data"].values[0]
    t_data = ast.literal_eval(raw_val)
    
    tab1, tab2, tab3 = st.tabs(["⚙️ Setup", "📅 Order of Play", "📊 Bracket Progression"])

    with tab1:
        st.subheader("Tournament Configuration")
        is_locked = st.checkbox("🔒 Lock Results & Setup", value=t_data.get("locked", False))
        t_data["locked"] = is_locked
        
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Player Entry**")
            t_data["players"] = st.data_editor(t_data["players"], num_rows="dynamic", key=f"pe_{selected_t}", disabled=is_locked)
        with c2:
            st.write("**Court Selection**")
            t_data["courts"] = st.data_editor(t_data["courts"], num_rows="dynamic", key=f"ce_{selected_t}", disabled=is_locked)
        
        if st.button("🚀 GENERATE & SYNC BRACKET", type="primary", use_container_width=True, disabled=is_locked):
            with st.status("Writing to Cloud...") as status:
                bracket, byes, size, perfect = generate_bracket(t_data["players"])
                t_data["bracket"] = bracket
                t_data["gen_info"] = {"byes": byes, "size": size, "perfect": perfect, "total": len([p for p in t_data["players"] if p])}
                
                # Update main dataframe and save
                df_db.loc[df_db["Tournament"] == selected_t, "Data"] = str(t_data)
                save_db(df_db)
                status.update(label="Saved to Google Sheets!", state="complete")
            st.balloons()
            st.rerun()

    with tab2:
        if not t_data.get("bracket"):
            st.warning("Generate the tournament in the 'Setup' tab first.")
        else:
            active_matches = [m for m in t_data["bracket"] if "BYE" not in m]
            if active_matches:
                st.subheader("Current Court Assignments")
                num_courts = len(t_data["courts"])
                cols = st.columns(num_courts)
                for i, match in enumerate(active_matches):
                    c_idx = i % num_courts
                    with cols[c_idx]:
                        st.markdown(f"""
                        <div class='match-card'>
                            <span class='court-header'>📍 {t_data['courts'][c_idx]}</span>
                            <b>{match[0]}</b> <br>vs<br> <b>{match[1]}</b>
                        </div>
                        """, unsafe_allow_html=True)

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
                            win = st.selectbox("Winner", ["-", p1, p2], key=f"r{round_idx}m{i}{selected_t}", disabled=is_locked)
                            next_round.append(win if win != "-" else "TBD")
                st.divider()
                if len(next_round) > 1:
                    current_round = [next_round[j:j+2] for j in range(0, len(next_round), 2)]
                    round_idx += 1
                else:
                    if next_round[0] not in ["TBD", "-"]:
                        st.success(f"🏆 Champion: {next_round[0]}")
                    break
            
            if st.button("💾 Save Winner Progress", use_container_width=True, disabled=is_locked):
                df_db.loc[df_db["Tournament"] == selected_t, "Data"] = str(t_data)
                save_db(df_db)
                st.toast("Progress Saved to Cloud!")
