import streamlit as st
import random
import math
import time

# --- PAGE CONFIG ---
st.set_page_config(page_title="Tennis Tourney Hub", layout="wide", page_icon="🎾")

# --- FIXED CSS FOR TEXT VISIBILITY ---
st.markdown("""
    <style>
    .match-card {
        border-left: 5px solid #2e7d32;
        background-color: #f1f8e9;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 15px;
        min-height: 120px;
        color: #1b5e20 !important; /* Forces Dark Green/Black text */
    }
    .match-card b {
        color: #000000 !important; /* Forces Black for player names */
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

if 'tournaments' not in st.session_state:
    st.session_state.tournaments = {}

def generate_bracket(participants):
    shuffled = [p for p in participants if str(p).strip() != ""]
    random.shuffle(shuffled)
    n = len(shuffled)
    next_pow_2 = 2**math.ceil(math.log2(n)) if n > 0 else 2
    num_byes = next_pow_2 - n
    is_perfect = (n == next_pow_2)
    full_slots = shuffled + (["BYE"] * num_byes)
    bracket = []
    for i in range(next_pow_2 // 2):
        bracket.append([full_slots[i], full_slots[next_pow_2 - 1 - i]])
    return bracket, num_byes, next_pow_2, is_perfect

# --- SIDEBAR ---
st.sidebar.title("🎾 Admin Panel")
new_t = st.sidebar.text_input("Tournament Name")
if st.sidebar.button("Create New Tournament"):
    if new_t:
        st.session_state.tournaments[new_t] = {
            "players": [f"Player {i+1}" for i in range(16)],
            "courts": ["Court 1", "Court 2"],
            "bracket": None,
            "gen_info": {}
        }
        st.rerun()

selected_t = st.sidebar.selectbox("Active Tournament", ["-- Select --"] + list(st.session_state.tournaments.keys()))

# --- MAIN CONTENT ---
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
            bracket, byes, size, perfect = generate_bracket(t_data["players"])
            t_data["bracket"] = bracket
            t_data["gen_info"] = {"byes": byes, "size": size, "perfect": perfect, "total": len([p for p in t_data["players"] if str(p).strip() != ""])}
            st.toast("Generated & Randomized!")
            st.rerun()

    with tab2:
        if not t_data.get("bracket") or not t_data.get("gen_info"):
            st.warning("Please generate the tournament in Setup.")
        else:
            info = t_data["gen_info"]
            if not info["perfect"]:
                st.warning(f"⚠️ **Power of 2 Check:** {info['total']} players isn't a power of 2. Scaled to {info['size']} with {info['byes']} byes.")
            else:
                st.success(f"✅ **Power of 2 Check:** {info['total']} is a perfect bracket size.")

            active_matches = [m for m in t_data["bracket"] if "BYE" not in m]
            if active_matches:
                st.subheader("Current Court Assignments")
                num_courts = len(t_data["courts"])
                cols = st.columns(num_courts)
                for i, match in enumerate(active_matches):
                    court_idx = i % num_courts
                    with cols[court_idx]:
                        # Using !important in CSS above fixes the white-text issue here
                        st.markdown(f"""
                        <div class="match-card">
                            <span class="court-header">📍 {t_data['courts'][court_idx]}</span>
                            <b>{match[0]}</b> <br>
                            <span style="font-size:0.8em; color:#666;">vs</span><br> 
                            <b>{match[1]}</b>
                        </div>
                        """, unsafe_allow_html=True)

    with tab3:
        if t_data.get("bracket"):
            current_round = t_data["bracket"]
            round_idx = 1
            while len(current_round) >= 1:
                st.subheader(f"Round {round_idx}" if len(current_round) > 1 else "Finals")
                cols = st.columns(len(current_round))
                next_round = []
                for i, match in enumerate(current_round):
                    with cols[i]:
                        p1, p2 = match[0], match[1]
                        st.write(f"**{p1}** vs **{p2}**")
                        if p2 == "BYE": next_round.append(p1)
                        elif "TBD" in [p1, p2]: next_round.append("TBD")
                        else:
                            win = st.selectbox("Winner", ["-", p1, p2], key=f"r{round_idx}m{i}{selected_t}")
                            next_round.append(win if win != "-" else "TBD")
                if len(next_round) > 1:
                    current_round = [next_round[j:j+2] for j in range(0, len(next_round), 2)]
                    round_idx += 1
                else: break
