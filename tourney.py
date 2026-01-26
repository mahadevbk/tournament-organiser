import streamlit as st
import random
import math
import time

# --- PAGE CONFIG ---
st.set_page_config(page_title="Tennis Tourney Hub", layout="wide", page_icon="🎾")

# --- CSS FOR UI ENHANCEMENT ---
st.markdown("""
    <style>
    .match-card {
        border-left: 5px solid #2e7d32;
        background-color: #f1f8e9;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 10px;
        min-height: 120px;
    }
    .bye-card {
        border-left: 5px solid #ffa000;
        background-color: #fff8e1;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize global storage
if 'tournaments' not in st.session_state:
    st.session_state.tournaments = {}

def generate_bracket(participants):
    # Clean list of empty entries
    shuffled = [p for p in participants if str(p).strip() != ""]
    random.shuffle(shuffled)
    n = len(shuffled)
    
    # Calculate Power of 2 requirement
    next_pow_2 = 2**math.ceil(math.log2(n)) if n > 0 else 2
    num_byes = next_pow_2 - n
    is_perfect = (n == next_pow_2)
    
    # Fill bracket slots
    full_slots = shuffled + (["BYE"] * num_byes)
    bracket = []
    for i in range(next_pow_2 // 2):
        bracket.append([full_slots[i], full_slots[next_pow_2 - 1 - i]])
        
    return bracket, num_byes, next_pow_2, is_perfect

# --- SIDEBAR ---
st.sidebar.title("🎾 Admin Panel")
new_t = st.sidebar.text_input("Tournament Name", placeholder="e.g. Winter Open")
if st.sidebar.button("Create New Tournament"):
    if new_t:
        st.session_state.tournaments[new_t] = {
            "players": [f"Player {i+1}" for i in range(20)],
            "courts": ["Court 1", "Court 2"],
            "bracket": None,
            "gen_info": {} # Initialized as empty to prevent KeyError
        }
        st.sidebar.success(f"Created {new_t}")

st.sidebar.divider()
selected_t = st.sidebar.selectbox("Active Tournament", ["-- Select --"] + list(st.session_state.tournaments.keys()))

# --- MAIN CONTENT ---
if selected_t == "-- Select --":
    st.title("Tennis Tournament Organizer")
    st.info("👈 Create or select a tournament in the sidebar to begin.")
else:
    t_data = st.session_state.tournaments[selected_t]
    tab1, tab2, tab3 = st.tabs(["⚙️ Setup", "📅 Order of Play", "📊 Tournament Bracket"])

    with tab1:
        st.subheader(f"Setup: {selected_t}")
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Player Entry**")
            t_data["players"] = st.data_editor(t_data["players"], num_rows="dynamic", key=f"p_edit_{selected_t}")
        with c2:
            st.write("**Court Names**")
            t_data["courts"] = st.data_editor(t_data["courts"], num_rows="dynamic", key=f"c_edit_{selected_t}")
        
        if st.button("🚀 GENERATE TOURNAMENT", type="primary", use_container_width=True):
            with st.spinner("Randomizing players..."):
                time.sleep(0.5)
                bracket, byes, size, perfect = generate_bracket(t_data["players"])
                t_data["bracket"] = bracket
                t_data["gen_info"] = {
                    "byes": byes, 
                    "size": size, 
                    "perfect": perfect, 
                    "total": len([p for p in t_data["players"] if str(p).strip() != ""])
                }
            st.toast("Tournament Generated!", icon="✅")
            st.rerun()

    with tab2:
        # SAFETY CHECK: Only run if bracket exists and gen_info is populated
        if not t_data.get("bracket") or not t_data.get("gen_info"):
            st.warning("⚠️ Tournament not yet generated. Please go to the **Setup** tab and click 'Generate'.")
        else:
            info = t_data["gen_info"]
            
            # Highlight Power of 2 Requirement
            if not info.get("perfect"):
                st.warning(f"⚠️ **Power of 2 Check:** {info['total']} players is not a perfect power of 2. "
                           f"To reach a fair Final, the system created a **{info['size']}-slot bracket** with **{info['byes']} byes**.")
            else:
                st.success(f"✅ **Power of 2 Check:** {info['total']} is a perfect bracket size. No byes needed.")

            st.subheader("📅 Current Court Assignments")
            active_matches = [m for m in t_data["bracket"] if "BYE" not in m]
            bye_matches = [m for m in t_data["bracket"] if "BYE" in m]

            if active_matches:
                # Display matches in a grid based on court count
                num_courts = len(t_data["courts"])
                cols = st.columns(num_courts)
                for i, match in enumerate(active_matches):
                    court_idx = i % num_courts
                    with cols[court_idx]:
                        st.markdown(f"""
                        <div class="match-card">
                            <small style="color:green;"><b>{t_data['courts'][court_idx]}</b></small><br>
                            <div style="font-size:1.1em; margin-top:5px;"><b>{match[0]}</b></div>
                            <div style="color:gray; font-size:0.8em;">vs</div>
                            <div style="font-size:1.1em;"><b>{match[1]}</b></div>
                        </div>
                        """, unsafe_allow_html=True)
            
            if bye_matches:
                with st.expander("View Players with Byes"):
                    for m in bye_matches:
                        p = m[0] if m[1] == "BYE" else m[1]
                        st.markdown(f"<div class='bye-card'>⏩ {p} advances to next round</div>", unsafe_allow_html=True)

    with tab3:
        if not t_data.get("bracket"):
            st.warning("Please generate the tournament first.")
        else:
            current_round = t_data["bracket"]
            round_idx = 1
            while len(current_round) >= 1:
                # Labeling Logic
                if len(current_round) == 1: r_label = "🏆 Championship Final"
                elif len(current_round) == 2: r_label = "Semi-Finals"
                elif len(current_round) == 4: r_label = "Quarter-Finals"
                else: r_label = f"Round {round_idx}"
                
                st.subheader(r_label)
                cols = st.columns(len(current_round))
                next_round = []
                
                for i, match in enumerate(current_round):
                    with cols[i]:
                        p1, p2 = match[0], match[1]
                        st.markdown(f"**{p1}** vs **{p2}**")
                        
                        if p2 == "BYE":
                            next_round.append(p1)
                            st.caption("Bye")
                        elif "TBD" in [p1, p2]:
                            next_round.append("TBD")
                            st.caption("Waiting...")
                        else:
                            win = st.selectbox("Winner", ["-", p1, p2], key=f"r{round_idx}m{i}{selected_t}")
                            next_round.append(win if win != "-" else "TBD")
                
                st.divider()
                if len(next_round) > 1:
                    current_round = [next_round[j:j+2] for j in range(0, len(next_round), 2)]
                    round_idx += 1
                else:
                    if next_round[0] not in ["TBD", "-"]:
                        st.balloons()
                        st.success(f"**Tournament Champion: {next_round[0]}**")
                    break
