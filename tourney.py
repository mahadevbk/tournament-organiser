import streamlit as st
import random
import math

st.set_page_config(page_title="Multi-Org Tennis Hub", layout="wide")

# --- DATABASE EMULATION ---
# In a production app, you'd use a SQL database. 
# Here, we use a global session state to store multiple tournaments.
if 'tournaments' not in st.session_state:
    st.session_state.tournaments = {}

def generate_bracket(participants):
    shuffled = list(participants)
    random.shuffle(shuffled)
    n = len(shuffled)
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

# --- SIDEBAR: TOURNAMENT SELECTOR ---
st.sidebar.title("🏢 Organization Portal")
new_t_name = st.sidebar.text_input("Create New Tournament Name")
if st.sidebar.button("Add Tournament"):
    if new_t_name and new_t_name not in st.session_state.tournaments:
        st.session_state.tournaments[new_t_name] = {
            "bracket": None,
            "scores": {},
            "players": [],
            "courts": [],
            "mode": "Singles"
        }
        st.sidebar.success(f"'{new_t_name}' Created!")

st.sidebar.divider()

selected_t = st.sidebar.selectbox(
    "Select Active Tournament", 
    options=["-- Select --"] + list(st.session_state.tournaments.keys())
)

# --- MAIN INTERFACE ---
if selected_t == "-- Select --":
    st.title("🎾 Tennis Tournament Hub")
    st.info("Select a tournament from the sidebar or create a new one to begin.")
    st.image("https://images.unsplash.com/photo-1595435066319-389369269550?q=80&w=1000&auto=format&fit=crop", width=700)
else:
    t_data = st.session_state.tournaments[selected_t]
    st.title(f"🏆 Managing: {selected_t}")
    
    tab1, tab2 = st.tabs(["⚙️ Setup & Players", "🎾 Live Bracket & Scores"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            mode = st.selectbox("Format", ["Singles", "Doubles"], key=f"mode_{selected_t}")
            num_p = st.number_input("Entries", 2, 64, 4, key=f"num_{selected_t}")
            player_input = st.data_editor(
                [f"Player {i+1}" for i in range(num_p)], 
                key=f"edit_{selected_t}", 
                use_container_width=True
            )
        with col2:
            num_c = st.number_input("Courts", 1, 10, 2, key=f"cnum_{selected_t}")
            court_input = st.data_editor(
                [f"Court {i+1}" for i in range(num_c)], 
                key=f"cedit_{selected_t}", 
                use_container_width=True
            )

        if st.button("Initialize / Reset Bracket", type="primary"):
            t_data["bracket"] = generate_bracket(player_input)
            t_data["players"] = player_input
            t_data["courts"] = court_input
            t_data["scores"] = {} # Clear old scores
            st.success("New bracket generated for this tournament!")
            st.rerun()

    with tab2:
        if not t_data["bracket"]:
            st.warning("No bracket generated for this tournament yet. Go to Setup.")
        else:
            current_matches = t_data["bracket"]
            round_idx = 1
            
            while len(current_matches) >= 1:
                title = "Final" if len(current_matches) == 1 else f"Round {round_idx}"
                st.subheader(f"📍 {title}")
                cols = st.columns(len(current_matches))
                next_round_seeds = []
                
                for i, match in enumerate(current_matches):
                    p1, p2 = match[0], match[1]
                    with cols[i]:
                        st.caption(f"Match {i+1}")
                        if p2 == "BYE":
                            st.success(f"✅ {p1}")
                            next_round_seeds.append(p1)
                        else:
                            # Unique key per tournament, per round, per match
                            s1 = st.number_input(f"{p1}", 0, 3, key=f"s1_{selected_t}_{round_idx}_{i}")
                            s2 = st.number_input(f"{p2}", 0, 3, key=f"s2_{selected_t}_{round_idx}_{i}")
                            
                            win_opt = ["-"]
                            if s1 > 0 or s2 > 0:
                                win_opt = [p1 if s1 > s2 else p2]
                            
                            winner = st.selectbox("Winner", win_opt, key=f"w_{selected_t}_{round_idx}_{i}")
                            
                            if winner != "-":
                                next_round_seeds.append(winner)
                            else:
                                next_round_seeds.append(None)
                
                st.divider()
                if len(next_round_seeds) > 1:
                    current_matches = [next_round_seeds[j:j+2] for j in range(0, len(next_round_seeds), 2)]
                    round_idx += 1
                    if None in next_round_seeds: break 
                else:
                    if next_round_seeds[0]:
                        st.balloons()
                        st.title(f"🏅 Champion: {next_round_seeds[0]}")
                    break
