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

if 'tournaments' not in st.session_state:
    st.session_state.tournaments = {}

def generate_bracket(participants):
    shuffled = [p for p in participants if str(p).strip() != ""]
    random.shuffle(shuffled)
    n = len(shuffled)
    
    # Calculate Power of 2 requirement
    next_pow_2 = 2**math.ceil(math.log2(n))
    num_byes = next_pow_2 - n
    is_perfect = (n == next_pow_2)
    
    # Interleave Byes and Players for a balanced bracket
    full_slots = shuffled + (["BYE"] * num_byes)
    bracket = []
    for i in range(next_pow_2 // 2):
        bracket.append([full_slots[i], full_slots[next_pow_2 - 1 - i]])
        
    return bracket, num_byes, next_pow_2, is_perfect

# --- SIDEBAR ---
st.sidebar.title("🎾 Admin Panel")
new_t = st.sidebar.text_input("Tournament Name")
if st.sidebar.button("Create New"):
    if new_t:
        st.session_state.tournaments[new_t] = {
            "players": [f"Player {i+1}" for i in range(20)],
            "courts": ["Court 1", "Court 2"],
            "bracket": None,
            "gen_info": {}
        }

selected_t = st.sidebar.selectbox("Active Tournament", ["-- Select --"] + list(st.session_state.tournaments.keys()))

if selected_t != "-- Select --":
    t_data = st.session_state.tournaments[selected_t]
    tab1, tab2, tab3 = st.tabs(["⚙️ Setup", "📅 Order of Play", "📊 Tournament Bracket"])

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Player Entry**")
            t_data["players"] = st.data_editor(t_data["players"], num_rows="dynamic", key=f"p_{selected_t}")
        with c2:
            st.write("**Court Names**")
            t_data["courts"] = st.data_editor(t_data["courts"], num_rows="dynamic", key=f"c_{selected_t}")
        
        if st.button("🚀 GENERATE TOURNAMENT", type="primary", use_container_width=True):
            with st.spinner("Randomizing players and assigning courts..."):
                time.sleep(1) # Visual delay for confirmation
                bracket, byes, size, perfect = generate_bracket(t_data["players"])
                t_data["bracket"] = bracket
                t_data["gen_info"] = {"byes": byes, "size": size, "perfect": perfect, "total": len([p for p in t_data["players"] if p])}
            st.toast("Tournament Generated Successfully!", icon="✅")
            st.rerun()

    with tab2:
        if not t_data.get("bracket"):
            st.info("Awaiting tournament generation...")
        else:
            info = t_data["gen_info"]
            
            # --- HIGHLIGHT ORDER OF 2 REQUIREMENT ---
            if not info["perfect"]:
                st.warning(f"⚠️ **Bracket Adjusted:** {info['total']} players does not meet a power of 2 ($2^n$). "
                           f"The tournament has been scaled to a **{info['size']}-player bracket** with **{info['byes']} byes** to ensure a valid final.")
            else:
                st.success(f"✅ **Perfect Bracket:** {info['total']} is a power of 2. No byes required.")

            st.subheader("📅 Live Court Assignments")
            active_matches = [m for m in t_data["bracket"] if "BYE" not in m]
            bye_matches = [m for m in t_data["bracket"] if "BYE" in m]

            if active_matches:
                cols = st.columns(len(t_data["courts"]))
                for i, match in enumerate(active_matches):
                    court_idx = i % len(t_data["courts"])
                    with cols[court_idx]:
                        st.markdown(f"""
                        <div class="match-card">
                            <small><b>{t_data['courts'][court_idx]}</b></small><br>
                            {match[0]} <br>vs<br> {match[1]}
                        </div>
                        """, unsafe_allow_html=True)
            
            if bye_matches:
                with st.expander("Show Round 1 Byes"):
                    for m in bye_matches:
                        p = m[0] if m[1] == "BYE" else m[1]
                        st.markdown(f"<div class='bye-card'>⏩ {p} advances on Bye</div>", unsafe_allow_html=True)

    with tab3:
        if t_data.get("bracket"):
            # The bracket visual logic
            current_round = t_data["bracket"]
            round_idx = 1
            while len(current_round) >= 1:
                st.subheader(f"Round {round_idx}" if len(current_round) > 1 else "Finals")
                cols = st.columns(len(current_round))
                next_round = []
                for i, match in enumerate(current_round):
                    with cols[i]:
                        p1, p2 = match[0], match[1]
                        st.markdown(f"**{p1}** vs **{p2}**")
                        if p2 == "BYE": next_round.append(p1)
                        elif "TBD" in [p1, p2]: next_round.append("TBD")
                        else:
                            win = st.selectbox("Win", ["-", p1, p2], key=f"r{round_idx}m{i}{selected_t}")
                            next_round.append(win if win != "-" else "TBD")
                st.divider()
                if len(next_round) > 1:
                    current_round = [next_round[j:j+2] for j in range(0, len(next_round), 2)]
                    round_idx += 1
                else: break
