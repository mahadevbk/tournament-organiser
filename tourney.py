import streamlit as st
import random
import math

# --- PAGE CONFIG ---
st.set_page_config(page_title="Tennis Tourney Hub", layout="wide", page_icon="🎾")

# --- DATABASE EMULATION ---
# Stores everything: { "Tourney Name": { "players": [], "courts": [], "bracket": [], "scores": {} } }
if 'tournaments' not in st.session_state:
    st.session_state.tournaments = {}

def generate_bracket(participants):
    """Logic to handle randomization and power-of-2 byes."""
    shuffled = [p for p in participants if p.strip() != ""]
    random.shuffle(shuffled)
    n = len(shuffled)
    if n < 2: return None
    
    next_pow_2 = 2**math.ceil(math.log2(n))
    num_byes = next_pow_2 - n
    
    bracket = []
    idx = 0
    for _ in range(num_byes):
        bracket.append([shuffled[idx], "BYE"])
        idx += 1
    while idx < n:
        bracket.append([shuffled[idx], shuffled[idx+1]])
        idx += 2
    return bracket

# --- SIDEBAR: NAVIGATION ---
st.sidebar.title("🎾 Tournament Manager")
new_t_name = st.sidebar.text_input("Create New Tournament", placeholder="e.g. Summer Open 2026")

if st.sidebar.button("Add Tournament", use_container_width=True):
    if new_t_name and new_t_name not in st.session_state.tournaments:
        st.session_state.tournaments[new_t_name] = {
            "bracket": None,
            "players": ["Player 1", "Player 2", "Player 3", "Player 4"],
            "courts": ["Court 1", "Court 2"],
            "mode": "Singles"
        }
        st.sidebar.success(f"Added {new_t_name}")

st.sidebar.divider()

selected_t = st.sidebar.selectbox(
    "Select Active Tournament", 
    options=["-- Select --"] + list(st.session_state.tournaments.keys())
)

# --- MAIN APP LOGIC ---
if selected_t == "-- Select --":
    st.title("Welcome to Tennis Tourney Pro")
    st.info("👈 Use the sidebar to create or select a tournament to get started.")
    st.markdown("""
    ### Features:
    * **Multi-Org Support:** Manage different tournaments simultaneously.
    * **Smart Brackets:** Automatic 'Bye' handling for non-power-of-2 entries.
    * **Score Tracking:** Real-time winner advancement.
    * **Court Assignment:** Automatic rotation of available courts.
    """)
else:
    t_data = st.session_state.tournaments[selected_t]
    st.title(f"🏆 {selected_t}")
    
    tab1, tab2 = st.tabs(["⚙️ Setup & Registration", "🎾 Match Brackets"])

    with tab1:
        st.subheader("1. Configure Participants")
        
        # Bulk Import Option
        with st.expander("📥 Bulk Import Names"):
            bulk_input = st.text_area("Paste names (one per line or comma separated)")
            if st.button("Process Bulk List"):
                if "," in bulk_input:
                    names = [n.strip() for n in bulk_input.split(",")]
                else:
                    names = [n.strip() for n in bulk_input.split("\n")]
                t_data["players"] = [n for n in names if n]
                st.rerun()

        col_p, col_c = st.columns(2)
        
        with col_p:
            st.write("**Player/Team List**")
            # This editor syncs directly with our storage
            t_data["players"] = st.data_editor(
                t_data["players"], 
                num_rows="dynamic", 
                use_container_width=True,
                key=f"edit_players_{selected_t}"
            )
            st.caption(f"Total: {len([p for p in t_data['players'] if p])} entries")

        with col_c:
            st.write("**Available Courts**")
            t_data["courts"] = st.data_editor(
                t_data["courts"], 
                num_rows="dynamic", 
                use_container_width=True,
                key=f"edit_courts_{selected_t}"
            )

        st.divider()
        if st.button("🚀 GENERATE RANDOMIZED BRACKET", type="primary", use_container_width=True):
            clean_players = [p for p in t_data["players"] if str(p).strip() != ""]
            if len(clean_players) < 2:
                st.error("You need at least 2 players!")
            else:
                t_data["bracket"] = generate_bracket(clean_players)
                st.success("Bracket generated and randomized!")
                st.rerun()

    with tab2:
        if not t_data.get("bracket"):
            st.warning("No bracket active. Please finalize your player list and hit 'Generate' in the Setup tab.")
        else:
            current_matches = t_data["bracket"]
            round_idx = 1
            
            while len(current_matches) >= 1:
                # Round Labels
                if len(current_matches) == 1: round_label = "🏆 Championship Final"
                elif len(current_matches) == 2: round_label = "Semi-Finals"
                elif len(current_matches) == 4: round_label = "Quarter-Finals"
                else: round_label = f"Round {round_idx}"
                
                st.header(round_label)
                cols = st.columns(len(current_matches))
                next_round_seeds = []
                
                for i, match in enumerate(current_matches):
                    p1, p2 = match[0], match[1]
                    with cols[i]:
                        st.markdown(f"**Match {i+1}**")
                        # Court Assignment Logic
                        court_name = t_data["courts"][i % len(t_data["courts"])]
                        st.caption(f"📍 {court_name}")
                        
                        if p2 == "BYE":
                            st.success(f"✅ {p1}")
                            next_round_seeds.append(p1)
                        else:
                            # Score Inputs
                            sc1 = st.number_input(f"{p1}", 0, 5, key=f"s1_{selected_t}_{round_idx}_{i}")
                            sc2 = st.number_input(f"{p2}", 0, 5, key=f"s2_{selected_t}_{round_idx}_{i}")
                            
                            # Winner Selection
                            options = ["-- Pending --"]
                            if sc1 > sc2: options = [p1]
                            elif sc2 > sc1: options = [p2]
                            elif sc1 == sc2 and sc1 > 0: options = [p1, p2] # Draw/Tiebreak
                            
                            winner = st.selectbox("Winner", options, key=f"win_{selected_t}_{round_idx}_{i}")
                            
                            if winner != "-- Pending --":
                                next_round_seeds.append(winner)
                            else:
                                next_round_seeds.append(None)
                
                st.divider()
                
                # Logic to flow into next round
                if len(next_round_seeds) > 1:
                    # Create pairs for next round
                    next_matches = []
                    for j in range(0, len(next_round_seeds), 2):
                        p_a = next_round_seeds[j]
                        p_b = next_round_seeds[j+1] if j+1 < len(next_round_seeds) else "TBD"
                        next_matches.append([p_a if p_a else "TBD", p_b if p_b else "TBD"])
                    
                    current_matches = next_matches
                    round_idx += 1
                    
                    # Stop rendering if the current round isn't finished
                    if None in next_round_seeds:
                        break
                else:
                    if next_round_seeds[0]:
                        st.balloons()
                        st.title(f"🎉 Winner: {next_round_seeds[0]} 🎉")
                    break
