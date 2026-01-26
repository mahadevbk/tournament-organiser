import streamlit as st
import random
import math

st.set_page_config(page_title="Tennis Tourney Pro", layout="wide", page_icon="🎾")

if 'tournaments' not in st.session_state:
    st.session_state.tournaments = {}

def generate_bracket(participants):
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

# --- SIDEBAR ---
st.sidebar.title("🎾 Admin Portal")
new_t_name = st.sidebar.text_input("New Tournament Name")
if st.sidebar.button("Create"):
    if new_t_name:
        st.session_state.tournaments[new_t_name] = {
            "bracket": None,
            "players": ["Player 1", "Player 2", "Player 3", "Player 4"],
            "courts": ["Court 1", "Court 2"]
        }

selected_t = st.sidebar.selectbox("Select Tournament", ["-- Select --"] + list(st.session_state.tournaments.keys()))

if selected_t != "-- Select --":
    t_data = st.session_state.tournaments[selected_t]
    
    tab1, tab2, tab3 = st.tabs(["⚙️ Setup", "📅 Order of Play", "🏆 Live Bracket"])

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Players**")
            t_data["players"] = st.data_editor(t_data["players"], num_rows="dynamic", key=f"p_{selected_t}")
        with c2:
            st.write("**Courts**")
            t_data["courts"] = st.data_editor(t_data["courts"], num_rows="dynamic", key=f"c_{selected_t}")
        
        if st.button("🚀 Generate Tournament Schedule", type="primary", use_container_width=True):
            t_data["bracket"] = generate_bracket(t_data["players"])
            st.rerun()

    with tab2:
        if t_data["bracket"]:
            st.header("📅 Initial Match Assignments")
            # Create a table for the Order of Play
            schedule_data = []
            for i, match in enumerate(t_data["bracket"]):
                court = t_data["courts"][i % len(t_data["courts"])]
                p1, p2 = match[0], match[1]
                status = "Direct Entry" if p2 != "BYE" else "Advances on Bye"
                schedule_data.append({"Match": i+1, "Court": court, "Player 1": p1, "Player 2": p2, "Status": status})
            
            st.table(schedule_data)
            
            st.info("💡 Match times are assigned based on court availability in the order matches were drawn.")
        else:
            st.warning("Please generate a bracket in the Setup tab.")

    with tab3:
        if t_data["bracket"]:
            st.header("🏆 Tournament Flow")
            # We display the full path even if winners aren't picked yet
            current_matches = t_data["bracket"]
            round_idx = 1
            
            while len(current_matches) >= 1:
                labels = {1: "Final", 2: "Semi-Finals", 4: "Quarter-Finals"}
                st.subheader(labels.get(len(current_matches), f"Round {round_idx}"))
                
                cols = st.columns(len(current_matches))
                next_round_seeds = []
                
                for i, match in enumerate(current_matches):
                    with cols[i]:
                        p1, p2 = match[0], match[1]
                        st.markdown(f"""
                        <div style="border:1px solid #ddd; padding:10px; border-radius:5px; background-color:#f9f9f9">
                            <small>Match {i+1}</small><br>
                            <b>{p1}</b> vs <b>{p2}</b>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if p2 == "BYE":
                            next_round_seeds.append(p1)
                        else:
                            winner = st.selectbox("Result", ["-", p1, p2], key=f"w_{selected_t}_{round_idx}_{i}")
                            next_round_seeds.append(winner if winner != "-" else "TBD")
                
                st.divider()
                if len(next_round_seeds) > 1:
                    current_matches = [next_round_seeds[j:j+2] for j in range(0, len(next_round_seeds), 2)]
                    round_idx += 1
                else:
                    if next_round_seeds[0] not in ["TBD", "-"]:
                        st.balloons()
                        st.success(f"Champion: {next_round_seeds[0]}")
                    break
        else:
            st.warning("Generate a bracket to see the flow.")
