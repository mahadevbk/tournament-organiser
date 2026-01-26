import streamlit as st
import random
import math

# --- PAGE CONFIG ---
st.set_page_config(page_title="Tennis Tourney Pro", layout="wide", page_icon="🎾")

# --- SESSION STATE INITIALIZATION ---
if 'tournaments' not in st.session_state:
    st.session_state.tournaments = {}

def generate_bracket(participants):
    """Creates a mathematically sound elimination bracket."""
    shuffled = [p for p in participants if str(p).strip() != ""]
    random.shuffle(shuffled)
    n = len(shuffled)
    if n < 2: return None, 0
    
    # Calculate next power of 2 (e.g., 20 players -> 32 slot bracket)
    next_pow_2 = 2**math.ceil(math.log2(n))
    num_byes = next_pow_2 - n
    
    # We create the full list of slots (Players + Byes)
    # We "seed" them so Byes are paired with the highest ranked players (first in list)
    full_slots = shuffled + (["BYE"] * num_byes)
    bracket = []
    
    # Pair them: 1 vs 32, 2 vs 31, etc.
    for i in range(next_pow_2 // 2):
        bracket.append([full_slots[i], full_slots[next_pow_2 - 1 - i]])
        
    return bracket, num_byes

# --- SIDEBAR ---
st.sidebar.title("🎾 Tournament Desk")
with st.sidebar.expander("➕ Create New Tournament"):
    new_name = st.text_input("Tournament Name", placeholder="e.g., Club Champs")
    if st.button("Add"):
        if new_name and new_name not in st.session_state.tournaments:
            st.session_state.tournaments[new_name] = {
                "players": [f"Player {i+1}" for i in range(20)],
                "courts": ["Court 1", "Court 2"],
                "bracket": None,
                "bye_count": 0
            }
            st.rerun()

st.sidebar.divider()
selected_t = st.sidebar.selectbox("Select Tournament", ["-- Select --"] + list(st.session_state.tournaments.keys()))

# --- MAIN CONTENT ---
if selected_t == "-- Select --":
    st.title("Tennis Tournament Organizer")
    st.info("Start by creating or selecting a tournament in the sidebar.")
    
else:
    t_data = st.session_state.tournaments[selected_t]
    st.title(f"🏆 {selected_t}")
    
    tab1, tab2, tab3 = st.tabs(["⚙️ Setup", "📅 Order of Play", "📊 Tournament Bracket"])

    # --- TAB 1: SETUP ---
    with tab1:
        st.subheader("Edit Participants & Courts")
        col_p, col_c = st.columns(2)
        with col_p:
            st.write("**Players**")
            t_data["players"] = st.data_editor(t_data["players"], num_rows="dynamic", key=f"pe_{selected_t}", use_container_width=True)
        with col_c:
            st.write("**Courts**")
            t_data["courts"] = st.data_editor(t_data["courts"], num_rows="dynamic", key=f"ce_{selected_t}", use_container_width=True)
        
        if st.button("🚀 Generate & Randomize", type="primary", use_container_width=True):
            t_data["bracket"], t_data["bye_count"] = generate_bracket(t_data["players"])
            st.success("Bracket and Schedule generated!")
            st.rerun()

    # --- TAB 2: ORDER OF PLAY ---
    with tab2:
        if not t_data["bracket"]:
            st.warning("Please generate a bracket in the Setup tab.")
        else:
            st.header("📅 Court Schedule")
            
            # Filter matches that are actually playable (not Byes)
            playable_matches = [m for m in t_data["bracket"] if "BYE" not in m]
            bye_players = [m[0] if m[1] == "BYE" else m[1] for m in t_data["bracket"] if "BYE" in m]

            if playable_matches:
                # Display matches and assign them to courts
                for i, match in enumerate(playable_matches):
                    court_name = t_data["courts"][i % len(t_data["courts"])]
                    with st.container():
                        c1, c2, c3 = st.columns([1, 4, 2])
                        c1.metric("Match", i+1)
                        c2.subheader(f"{match[0]} vs {match[1]}")
                        c3.info(f"📍 {court_name}")
                        st.divider()
            
            if bye_players:
                with st.expander("Players with Round 1 Byes"):
                    st.write(", ".join(bye_players))
                    st.caption("These players advance automatically to the next round to maintain tournament structure.")

    # --- TAB 3: VISUAL BRACKET ---
    with tab3:
        if not t_data["bracket"]:
            st.warning("Please generate a bracket first.")
        else:
            st.header("Tournament Progression")
            
            current_round = t_data["bracket"]
            round_idx = 1
            
            while len(current_round) >= 1:
                # Labeling
                if len(current_round) == 1: r_label = "Final"
                elif len(current_round) == 2: r_label = "Semi-Finals"
                elif len(current_round) == 4: r_label = "Quarter-Finals"
                else: r_label = f"Round {round_idx}"
                
                st.subheader(f"📍 {r_label}")
                cols = st.columns(len(current_round))
                next_round_players = []
                
                for i, match in enumerate(current_round):
                    with cols[i]:
                        p1, p2 = match[0], match[1]
                        # Box Styling
                        st.markdown(f"""
                            <div style="border:1px solid #ddd; padding:10px; border-radius:8px; background-color:#fcfcfc; text-align:center;">
                                <b>{p1}</b><br><small>vs</small><br><b>{p2}</b>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # Selection Logic
                        if p2 == "BYE":
                            next_round_players.append(p1)
                            st.caption("Bye Entry")
                        elif "TBD" in [p1, p2]:
                            next_round_players.append("TBD")
                            st.caption("Waiting...")
                        else:
                            winner = st.selectbox("Winner", ["-", p1, p2], key=f"win_{selected_t}_{round_idx}_{i}")
                            next_round_players.append(winner if winner != "-" else "TBD")
                
                st.divider()
                
                # Setup for loop to draw next round
                if len(next_round_players) > 1:
                    current_round = [next_round_players[j:j+2] for j in range(0, len(next_round_players), 2)]
                    round_idx += 1
                else:
                    if next_round_players[0] not in ["TBD", "-"]:
                        st.balloons()
                        st.success(f"Champion: {next_round_players[0]}")
                    break
