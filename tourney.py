import streamlit as st
import random
import math
import time

# --- PAGE CONFIG ---
st.set_page_config(page_title="Tennis Tourney Hub", layout="wide", page_icon="🎾")

# --- CSS FOR TEXT VISIBILITY & CARDS ---
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
    .match-card b {
        color: #000000 !important;
    }
    .court-header {
        color: #1b5e20 !important;
        font-weight: bold;
        border-bottom: 1px solid #c8e6c9;
        margin-bottom: 10px;
        display: block;
    }
    .bye-card {
        border-left: 5px solid #ffa000;
        background-color: #fff8e1;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
        color: #7f0000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INITIALIZE SESSION STATE ---
if 'tournaments' not in st.session_state:
    st.session_state.tournaments = {}

def generate_bracket(participants):
    # Strict filter to remove empty strings and "None" objects
    shuffled = [str(p).strip() for p in participants if p and str(p).strip() != "" and str(p) != "None"]
    random.shuffle(shuffled)
    n = len(shuffled)
    if n == 0: return None, 0, 0, False
    
    next_pow_2 = 2**math.ceil(math.log2(n))
    num_byes = next_pow_2 - n
    is_perfect = (n == next_pow_2)
    
    full_slots = shuffled + (["BYE"] * num_byes)
    bracket = []
    # Standard tournament seeding/pairing
    for i in range(next_pow_2 // 2):
        bracket.append([full_slots[i], full_slots[next_pow_2 - 1 - i]])
    return bracket, num_byes, next_pow_2, is_perfect

# --- SIDEBAR: MANAGEMENT ---
st.sidebar.title("🎾 Admin Desk")

with st.sidebar.expander("✨ Create Tournament"):
    new_t = st.text_input("Tournament Name")
    if st.button("Add Tournament"):
        if new_t and new_t not in st.session_state.tournaments:
            st.session_state.tournaments[new_t] = {
                "players": [f"player {i+1}" for i in range(17)],
                "courts": ["Court 1", "Court 2"],
                "bracket": None,
                "gen_info": {},
                "locked": False
            }
            st.sidebar.success(f"'{new_t}' added!")
            st.rerun()

selected_t = st.sidebar.selectbox("Active Tournament", ["-- Select --"] + list(st.session_state.tournaments.keys()))

if selected_t != "-- Select --":
    st.sidebar.divider()
    # Lock/Unlock Toggle
    is_locked = st.session_state.tournaments[selected_t].get("locked", False)
    if st.sidebar.checkbox("🔒 Lock Tournament Results", value=is_locked):
        st.session_state.tournaments[selected_t]["locked"] = True
    else:
        st.session_state.tournaments[selected_t]["locked"] = False
    
    # Delete Button
    if st.sidebar.button(f"🗑️ Delete {selected_t}", type="secondary", use_container_width=True):
        del st.session_state.tournaments[selected_t]
        st.sidebar.warning("Tournament deleted.")
        st.rerun()

# --- MAIN INTERFACE ---
if selected_t == "-- Select --":
    st.title("Tennis Tournament Organizer")
    st.info("👈 Use the sidebar to create or select a tournament to begin.")
else:
    t_data = st.session_state.tournaments[selected_t]
    tab1, tab2, tab3 = st.tabs(["⚙️ Setup", "📅 Order of Play", "📊 Tournament Bracket"])

    with tab1:
        st.subheader("Configuration")
        if t_data.get("locked"):
            st.warning("This tournament is LOCKED. Unlock in the sidebar to edit names or courts.")
        
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Participants**")
            t_data["players"] = st.data_editor(t_data["players"], num_rows="dynamic", key=f"p_e_{selected_t}", disabled=t_data["locked"])
        with c2:
            st.write("**Courts**")
            t_data["courts"] = st.data_editor(t_data["courts"], num_rows="dynamic", key=f"c_e_{selected_t}", disabled=t_data["locked"])
        
        if st.button("🚀 GENERATE & RANDOMIZE", type="primary", use_container_width=True, disabled=t_data["locked"]):
            with st.status("Initializing Bracket...", expanded=True) as status:
                st.write("Cleaning player list...")
                time.sleep(0.4)
                st.write("Randomizing pairings...")
                bracket, byes, size, perfect = generate_bracket(t_data["players"])
                t_data["bracket"] = bracket
                t_data["gen_info"] = {
                    "byes": byes, 
                    "size": size, 
                    "perfect": perfect, 
                    "total": len([p for p in t_data["players"] if p and str(p).strip() != ""])
                }
                st.write("Assigning courts...")
                time.sleep(0.4)
                status.update(label="Tournament Successfully Generated!", state="complete", expanded=False)
            
            st.balloons()
            st.success("Check the 'Order of Play' tab for your matches!")
            time.sleep(1)
            st.rerun()

    with tab2:
        if not t_data.get("bracket"):
            st.warning("Please generate the tournament in the Setup tab.")
        else:
            info = t_data["gen_info"]
            if not info.get("perfect"):
                st.warning(f"⚠️ **Note:** {info.get('total')} players isn't a power of 2. Scaled to {info.get('size')} with {info.get('byes')} byes.")
            else:
                st.success(f"✅ **Perfect Bracket:** {info.get('total')} players is a power of 2.")

            active_matches = [m for m in t_data["bracket"] if "BYE" not in m]
            if active_matches:
                st.subheader("Current Court Assignments")
                num_courts = len(t_data["courts"])
                cols = st.columns(num_courts)
                for i, match in enumerate(active_matches):
                    court_idx = i % num_courts
                    with cols[court_idx]:
                        st.markdown(f"""
                        <div class="match-card">
                            <span class="court-header">📍 {t_data['courts'][court_idx]}</span>
                            <b>{match[0]}</b> <br>
                            <span style="font-size:0.8em; color:#666;">vs</span><br> 
                            <b>{match[1]}</b>
                        </div>
                        """, unsafe_allow_html=True)

    with tab3:
        if not t_data.get("bracket"):
            st.warning("Generate the tournament to view the bracket.")
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
                        if p2 == "BYE":
                            next_round.append(p1)
                            st.caption("Bye")
                        elif "TBD" in [p1, p2]:
                            next_round.append("TBD")
                            st.caption("Waiting...")
                        else:
                            # Winners can't be changed if locked
                            win = st.selectbox("Winner", ["-", p1, p2], key=f"r{round_idx}m{i}{selected_t}", disabled=t_data["locked"])
                            next_round.append(win if win != "-" else "TBD")
                st.divider()
                if len(next_round) > 1:
                    current_round = [next_round[j:j+2] for j in range(0, len(next_round), 2)]
                    round_idx += 1
                else:
                    if next_round[0] not in ["TBD", "-"]:
                        st.success(f"🏅 **Tournament Champion: {next_round[0]}**")
                    break
