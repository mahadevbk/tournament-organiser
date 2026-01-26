import streamlit as st
import random
import math

# --- PAGE CONFIG ---
st.set_page_config(page_title="Tennis Tourney Hub", layout="wide", page_icon="🎾")

# --- CUSTOM CSS FOR BRACKET STYLING ---
st.markdown("""
    <style>
    .match-box {
        border: 2px solid #e6e9ef;
        border-radius: 10px;
        padding: 15px;
        background-color: #ffffff;
        margin-bottom: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .court-label {
        color: #2e7d32;
        font-weight: bold;
        font-size: 0.8rem;
        text-transform: uppercase;
    }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE EMULATION ---
if 'tournaments' not in st.session_state:
    st.session_state.tournaments = {}

def generate_bracket(participants):
    """Randomizes players and creates the initial round with Byes."""
    shuffled = [p for p in participants if str(p).strip() != ""]
    random.shuffle(shuffled)
    n = len(shuffled)
    if n < 2: return None
    
    # Logic: Find the next power of 2 for a perfect elimination bracket
    next_pow_2 = 2**math.ceil(math.log2(n))
    num_byes = next_pow_2 - n
    
    bracket = []
    idx = 0
    # Assign Byes first to ensure they are spread out
    for _ in range(num_byes):
        bracket.append([shuffled[idx], "BYE"])
        idx += 1
    # Pair the remaining players
    while idx < n:
        bracket.append([shuffled[idx], shuffled[idx+1]])
        idx += 2
    return bracket

# --- SIDEBAR: ORGANIZATION & NAVIGATION ---
st.sidebar.title("🏢 Tournament Desk")
with st.sidebar.expander("✨ Create New Tournament"):
    new_t_name = st.text_input("Tournament Name")
    if st.button("Add to Registry"):
        if new_t_name and new_t_name not in st.session_state.tournaments:
            st.session_state.tournaments[new_t_name] = {
                "bracket": None,
                "players": [f"Player {i+1}" for i in range(8)],
                "courts": ["Court 1", "Court 2", "Court 3"],
                "results": {} # Stores winner of each match
            }
            st.success(f"'{new_t_name}' created!")

st.sidebar.divider()

tourney_list = list(st.session_state.tournaments.keys())
selected_t = st.sidebar.selectbox("Active Tournament", ["-- Select --"] + tourney_list)

# --- MAIN APP ---
if selected_t == "-- Select --":
    st.title("🎾 Tennis Tournament Organizer")
    st.info("Please select or create a tournament in the sidebar to manage participants and brackets.")
    
else:
    t_data = st.session_state.tournaments[selected_t]
    st.title(f"🏆 {selected_t}")
    
    tab1, tab2, tab3 = st.tabs(["⚙️ Setup & Registration", "📅 Order of Play", "📊 Live Bracket & Scores"])

    # --- TAB 1: SETUP ---
    with tab1:
        st.subheader("Participant & Court Management")
        
        with st.expander("📥 Bulk Paste Player Names"):
            bulk_text = st.text_area("Enter names (one per line)")
            if st.button("Import Names"):
                t_data["players"] = [n.strip() for n in bulk_text.split("\n") if n.strip()]
                st.rerun()

        col_left, col_right = st.columns(2)
        with col_left:
            st.write("**Player/Team List**")
            t_data["players"] = st.data_editor(t_data["players"], num_rows="dynamic", use_container_width=True, key=f"p_edit_{selected_t}")
        
        with col_right:
            st.write("**Court Names**")
            t_data["courts"] = st.data_editor(t_data["courts"], num_rows="dynamic", use_container_width=True, key=f"c_edit_{selected_t}")

        if st.button("🚀 RANDOMIZE & GENERATE BRACKET", type="primary", use_container_width=True):
            t_data["bracket"] = generate_bracket(t_data["players"])
            t_data["results"] = {} # Clear previous winners
            st.success("Bracket Randomized! Check the 'Order of Play' tab.")

    # --- TAB 2: ORDER OF PLAY ---
    with tab2:
        if not t_data["bracket"]:
            st.warning("No bracket generated. Go to Setup.")
        else:
            st.header("📅 First Round Schedule")
            schedule = []
            for i, match in enumerate(t_data["bracket"]):
                p1, p2 = match[0], match[1]
                court = t_data["courts"][i % len(t_data["courts"])]
                note = "Walkover" if p2 == "BYE" else "Scheduled"
                schedule.append({
                    "Match": i + 1,
                    "Court": court,
                    "Player 1": p1,
                    "Player 2": p2,
                    "Status": note
                })
            st.table(schedule)
            st.caption("Matches are assigned to courts in the order they were drawn.")

    # --- TAB 3: LIVE BRACKET ---
    with tab3:
        if not t_data["bracket"]:
            st.warning("No bracket generated. Go to Setup.")
        else:
            current_round_matches = t_data["bracket"]
            round_num = 1
            
            while len(current_round_matches) >= 1:
                # Round Header Label
                if len(current_round_matches) == 1: r_title = "🏆 THE FINAL"
                elif len(current_round_matches) == 2: r_title = "Semi-Finals"
                elif len(current_round_matches) == 4: r_title = "Quarter-Finals"
                else: r_title = f"Round {round_num}"
                
                st.subheader(r_title)
                cols = st.columns(len(current_round_matches))
                next_round_players = []
                
                for i, match in enumerate(current_round_matches):
                    p1, p2 = match[0], match[1]
                    with cols[i]:
                        # Visual Match Box
                        court_display = t_data["courts"][i % len(t_data["courts"])] if round_num == 1 else "TBD"
                        st.markdown(f"""
                            <div class="match-box">
                                <div class="court-label">📍 {court_display}</div>
                                <div style="margin-top:5px;"><b>{p1}</b></div>
                                <div style="color:gray; font-size:0.8em;">vs</div>
                                <div><b>{p2}</b></div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # Winner Logic
                        if p2 == "BYE":
                            next_round_players.append(p1)
                            st.caption("✅ Bye")
                        elif p1 == "TBD" or p2 == "TBD":
                            next_round_players.append("TBD")
                            st.caption("Waiting for previous round...")
                        else:
                            winner = st.selectbox("Select Winner", ["--", p1, p2], key=f"win_{selected_t}_{round_num}_{i}")
                            if winner != "--":
                                next_round_players.append(winner)
                            else:
                                next_round_players.append("TBD")
                
                st.divider()
                
                # Setup next round matches
                if len(next_round_players) > 1:
                    new_matches = []
                    for j in range(0, len(next_round_players), 2):
                        new_matches.append([next_round_players[j], next_round_players[j+1]])
                    current_round_matches = new_matches
                    round_num += 1
                else:
                    # Final Result
                    champion = next_round_players[0]
                    if champion != "TBD":
                        st.balloons()
                        st.markdown(f"<h1 style='text-align: center; color: gold;'>🏆 CHAMPION: {champion} 🏆</h1>", unsafe_allow_html=True)
                    break

# --- FOOTER IMPROVEMENTS SUGGESTION ---
st.sidebar.divider()
st.sidebar.caption("💡 **Pro-Tip:** Connect a SQL Database for permanent storage between app restarts.")
