import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import math
import time
import ast

# --- PAGE CONFIG ---
st.set_page_config(page_title="Tennis Tourney Hub", layout="wide", page_icon="🎾")

# --- INITIALIZE GOOGLE SHEETS CONNECTION ---
# This uses the [connections.gsheets] section from your secrets.toml
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CSS FOR VISIBILITY ---
st.markdown("""
    <style>
    .match-card {
        border-left: 5px solid #2e7d32;
        background-color: #f1f8e9;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 15px;
        min-height: 120px;
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

# --- DATABASE HELPERS ---
def load_full_db():
    """Reads the entire sheet as a DataFrame."""
    try:
        # ttl=0 ensures we always get the freshest data from the sheet
        return conn.read(ttl=0)
    except:
        return pd.DataFrame(columns=["Tournament", "Data"])

def save_tournament(t_name, t_dict):
    """Saves or updates a tournament entry in the Google Sheet."""
    df = load_full_db()
    # Convert dictionary to string for storage in a single cell
    data_str = str(t_dict)
    
    if t_name in df["Tournament"].values:
        df.loc[df["Tournament"] == t_name, "Data"] = data_str
    else:
        new_row = pd.DataFrame([{"Tournament": t_name, "Data": data_str}])
        df = pd.concat([df, new_row], ignore_index=True)
    
    conn.update(data=df)

def generate_bracket(participants):
    """Mathematical elimination logic."""
    shuffled = [str(p).strip() for p in participants if p and str(p).strip() not in ["", "None", "nan"]]
    random.shuffle(shuffled)
    n = len(shuffled)
    if n == 0: return None, 0, 0, False
    
    next_pow_2 = 2**math.ceil(math.log2(n))
    num_byes = next_pow_2 - n
    is_perfect = (n == next_pow_2)
    
    full_slots = shuffled + (["BYE"] * num_byes)
    bracket = []
    for i in range(next_pow_2 // 2):
        bracket.append([full_slots[i], full_slots[next_pow_2 - 1 - i]])
    return bracket, num_byes, next_pow_2, is_perfect

# --- MAIN APP ---
st.title("🎾 Tournament Ograniser")
st.info ("Suggested number of players / Teams : 8, 16, 32, 64....")

# 1. Fetch current database state
db_df = load_full_db()
tournament_names = db_df["Tournament"].unique().tolist()

# 2. Sidebar Management
with st.sidebar:
    st.header("Admin Desk")
    new_t = st.text_input("New Tournament Name")
    if st.button("✨ Create"):
        if new_t and new_t not in tournament_names:
            initial_data = {
                "players": [f"player {i+1}" for i in range(17)],
                "courts": ["Court 1", "Court 2"],
                "bracket": None,
                "gen_info": {},
                "locked": False
            }
            save_tournament(new_t, initial_data)
            st.success(f"Created {new_t}")
            st.rerun()

    selected_t = st.selectbox("Select Tournament", ["-- Select --"] + tournament_names)
    
    if selected_t != "-- Select --":
        st.divider()
        if st.button(f"🗑️ Delete {selected_t}", type="secondary"):
            df_remaining = db_df[db_df["Tournament"] != selected_t]
            conn.update(data=df_remaining)
            st.rerun()

# 3. Tournament Logic
if selected_t != "-- Select --":
    # Load specific tournament data
    row = db_df[db_df["Tournament"] == selected_t].iloc[0]
    # ast.literal_eval is safer than eval() for converting string back to dict
    t_data = ast.literal_eval(row["Data"])
    
    tab1, tab2, tab3 = st.tabs(["⚙️ Setup", "📅 Order of Play", "📊 Bracket"])

    with tab1:
        st.subheader("Configuration")
        is_locked = st.checkbox("🔒 Lock Results", value=t_data.get("locked", False))
        t_data["locked"] = is_locked
        
        c1, c2 = st.columns(2)
        with c1:
            t_data["players"] = st.data_editor(t_data["players"], num_rows="dynamic", key=f"pe_{selected_t}", disabled=is_locked)
        with c2:
            t_data["courts"] = st.data_editor(t_data["courts"], num_rows="dynamic", key=f"ce_{selected_t}", disabled=is_locked)
        
        if st.button("🚀 SAVE & GENERATE", type="primary", use_container_width=True, disabled=is_locked):
            with st.status("Syncing with Google Sheets...") as s:
                bracket, byes, size, perfect = generate_bracket(t_data["players"])
                t_data["bracket"] = bracket
                t_data["gen_info"] = {"byes": byes, "size": size, "perfect": perfect, "total": len([p for p in t_data["players"] if p])}
                save_tournament(selected_t, t_data)
                s.update(label="Saved to Cloud!", state="complete")
            st.balloons()
            st.rerun()

    with tab2:
        if not t_data.get("bracket"):
            st.warning("Generate the tournament first.")
        else:
            info = t_data["gen_info"]
            st.info(f"Bracket: {info.get('size')} slots | Byes: {info.get('byes')}")
            
            active_matches = [m for m in t_data["bracket"] if "BYE" not in m]
            if active_matches:
                cols = st.columns(len(t_data["courts"]))
                for i, match in enumerate(active_matches):
                    c_idx = i % len(t_data["courts"])
                    with cols[c_idx]:
                        st.markdown(f"""<div class='match-card'>
                            <span class='court-header'>📍 {t_data['courts'][c_idx]}</span>
                            <b>{match[0]}</b> vs <b>{match[1]}</b>
                        </div>""", unsafe_allow_html=True)

    with tab3:
        if not t_data.get("bracket"):
            st.warning("Generate the tournament first.")
        else:
            # We must track if data changed to save back to sheets
            changed = False
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
                        
                        if p2 == "BYE":
                            next_round.append(p1)
                        elif "TBD" in [p1, p2]:
                            next_round.append("TBD")
                        else:
                            # Selection logic
                            win = st.selectbox("Winner", ["-", p1, p2], key=f"r{round_idx}m{i}{selected_t}", disabled=is_locked)
                            if win != "-":
                                next_round.append(win)
                            else:
                                next_round.append("TBD")
                
                if len(next_round) > 1:
                    current_round = [next_round[j:j+2] for j in range(0, len(next_round), 2)]
                    round_idx += 1
                else:
                    if next_round[0] not in ["TBD", "-"]:
                        st.success(f"🏆 Champion: {next_round[0]}")
                    break
            
            if st.button("💾 Save Winners to Cloud", disabled=is_locked):
                save_tournament(selected_t, t_data)
                st.toast("Progress Saved!")
