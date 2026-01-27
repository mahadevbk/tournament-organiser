import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import math
import ast
import datetime
import re

# ────────────────────────────────────────────────
# PAGE CONFIG + AUDIOWIDE FONT
# ────────────────────────────────────────────────
st.set_page_config(page_title="Tennis Tournament Organiser", layout="wide", page_icon="🎾")

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Audiowide&display=swap" rel="stylesheet">
<style>
    html, body, [data-testid="stAppViewContainer"], .stApp, .st-emotion-cache-* {
        font-family: 'Audiowide', sans-serif !important;
    }
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Audiowide', sans-serif !important;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'Audiowide', sans-serif !important;
    }
    button, .stButton > button {
        font-family: 'Audiowide', sans-serif !important;
    }
    input, textarea, select, .stTextInput input, .stSelectbox select {
        font-family: 'Audiowide', sans-serif !important;
    }
    .stDataFrame, .dataframe, td, th {
        font-family: 'Audiowide', sans-serif !important;
    }
    section[data-testid="stSidebar"] * {
        font-family: 'Audiowide', sans-serif !important;
    }
    .match-card {
        background: rgba(30, 41, 59, 0.92);
        border: 1px solid #475569;
        border-radius: 12px;
        padding: 24px;
        margin: 24px auto;
        max-width: 420px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.35);
        text-align: center;
    }
    .match-card:hover {
        transform: translateY(-6px);
        box-shadow: 0 10px 25px rgba(34, 197, 94, 0.3);
    }
    .player-row {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 16px;
        margin: 12px 0;
    }
    .player-avatar {
        width: 80px; height: 80px;
        border-radius: 50%;
        object-fit: cover;
        border: 3px solid #4ade80;
    }
    .mini-avatar {
        width: 40px; height: 40px;
        border-radius: 50%;
        object-fit: cover;
        border: 2px solid #4ade80;
    }
    .vs-divider {
        font-size: 1.5em;
        font-weight: bold;
        color: #4ade80;
        margin: 12px 0;
        letter-spacing: 2px;
    }
    .court-header {
        font-size: 1.4em;
        color: #4ade80;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 10px;
        justify-content: center;
    }
    .court-header::before { content: "🎾"; }
    .round-arrow {
        text-align: center;
        color: #4ade80;
        font-size: 2.5em;
        margin: 30px 0;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# CONNECTION & UTILITIES
# ────────────────────────────────────────────────
conn = st.connection("gsheets", type=GSheetsConnection)

def get_p_img(name, player_list):
    placeholder = 'https://www.gravatar.com/avatar/000?d=mp'
    if name in ["BYE", "TBD", None, '']: return placeholder
    for p in player_list:
        if isinstance(p, dict) and p.get('name') == name:
            url = p.get('img', '')
            if not url: return placeholder
            if "drive.google.com" in url:
                match = re.search(r'/d/([^/]+)', url)
                if match: return f"https://drive.google.com/uc?export=view&id={match.group(1)}"
            return url
    return placeholder

def load_db():
    try:
        df = conn.read(ttl=0)
        return df if df is not None and not df.empty else pd.DataFrame(columns=["Tournament", "Data"])
    except:
        return pd.DataFrame(columns=["Tournament", "Data"])

def save_db(df):
    try:
        conn.update(data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Save failed: {str(e)}")
        return False

# ────────────────────────────────────────────────
# GENERATORS
# ────────────────────────────────────────────────
def generate_bracket(participants):
    names = [p['name'] if isinstance(p, dict) else str(p) for p in participants]
    names = [n.strip() for n in names if n.strip()]
    random.shuffle(names)
    if not names: return None
    next_pow_2 = 2 ** math.ceil(math.log2(max(len(names), 1)))
    full_slots = names + (["BYE"] * (next_pow_2 - len(names)))
    return [full_slots[i:i+2] for i in range(0, len(full_slots), 2)]

def generate_round_robin(participants):
    names = [p['name'] if isinstance(p, dict) else str(p) for p in participants]
    names = [n.strip() for n in names if n.strip()]
    if len(names) < 2: return None
    if len(names) % 2 != 0: names.append("BYE")
    n, rounds = len(names), []
    p_list = names[:]
    for i in range(n - 1):
        rounds.append([[p_list[j], p_list[n - 1 - j]] for j in range(n // 2)])
        p_list = [p_list[0]] + [p_list[-1]] + p_list[1:-1]
    return rounds

def generate_groups(participants):
    names = [p['name'] if isinstance(p, dict) else str(p) for p in participants]
    names = [n.strip() for n in names if n.strip()]
    if len(names) < 4: return None
    random.shuffle(names)
    num_groups = 4 if len(names) >= 16 else 2 if len(names) >= 8 else max(1, len(names) // 3)
    groups = [names[i::num_groups] for i in range(num_groups)]
    group_matches = [generate_round_robin(g) for g in groups]
    return {"groups": groups, "group_matches": group_matches, "knockout": None}

# ────────────────────────────────────────────────
# MAIN APP
# ────────────────────────────────────────────────
st.title("🎾 Tennis Tournament Organiser")

df_db = load_db()
tournament_list = df_db["Tournament"].dropna().unique().tolist()

if not tournament_list:
    st.warning("No tournaments available yet. Create one in the sidebar.")
    st.stop()

default_index = 0 if len(tournament_list) == 1 else None
selected_t = st.selectbox(
    "Select a tournament",
    options=tournament_list,
    index=default_index,
    key="tournament_select_main"
)

if selected_t:
    row = df_db[df_db["Tournament"] == selected_t]
    if not row.empty:
        t_data = ast.literal_eval(row["Data"].values[0])

        defaults = {
            "scores": {}, "winners": {}, "players": [], "courts": ["Court 1"],
            "format": "Single Elimination", "locked": False, "bracket": None,
            "admin_password": ""
        }
        for k, v in defaults.items():
            t_data.setdefault(k, v)

        if t_data.get("players") and isinstance(t_data["players"][0], str):
            t_data["players"] = [{"name": p, "img": ""} for p in t_data["players"]]

        # ── Sidebar: Create always visible, edit/delete protected ──
        with st.sidebar:
            st.header("Admin Desk")

            # ── Create new tournament (always visible) ──
            st.subheader("Create New Tournament")
            new_t = st.text_input("Tournament Name", key="new_t_name")
            admin_pw_new = st.text_input("Set Admin Password", type="password", key="new_pw")
            if st.button("✨ Create Tournament"):
                if new_t and new_t not in tournament_list and admin_pw_new:
                    init_data = {
                        "players": [{"name": f"Player {i+1}", "img": ""} for i in range(8)],
                        "courts": ["Court 1", "Court 2"],
                        "format": "Single Elimination",
                        "bracket": None,
                        "winners": {},
                        "scores": {},
                        "locked": False,
                        "admin_password": admin_pw_new,
                        "last_sync": "Never"
                    }
                    new_row = pd.DataFrame([{"Tournament": new_t, "Data": str(init_data)}])
                    if save_db(pd.concat([df_db, new_row], ignore_index=True)):
                        st.success(f"Tournament **{new_t}** created! Password set.")
                        st.rerun()
                else:
                    st.warning("Enter unique name and password")

            # ── Admin login for editing current tournament ──
            st.markdown("---")
            st.subheader("Edit Current Tournament")
            correct_pw = t_data.get("admin_password", "")
            if "setup_authorized" not in st.session_state:
                st.session_state.setup_authorized = False

            if not st.session_state.setup_authorized:
                entered_pw = st.text_input("Admin Password", type="password", key=f"pw_{selected_t}")
                if st.button("Login to Edit"):
                    if entered_pw == correct_pw:
                        st.session_state.setup_authorized = True
                        st.success("Editing unlocked")
                        st.rerun()
                    else:
                        st.error("Incorrect password")
            else:
                st.success("Editing mode active")
                if st.button("Logout Editing"):
                    st.session_state.setup_authorized = False
                    st.rerun()

                t_data["locked"] = st.toggle("Lock tournament", value=t_data.get("locked", False))

                st.markdown("### Format")
                format_options = ["Single Elimination", "Round Robin", "Double Elimination", "Group Stage + Knockout"]
                fmt = st.radio(
                    "Change format",
                    options=format_options,
                    index=format_options.index(t_data.get("format", "Single Elimination")),
                    horizontal=True,
                    disabled=t_data["locked"],
                    key=f"admin_fmt_{selected_t}"
                )
                t_data["format"] = fmt

                st.markdown("### Participants")
                t_data["players"] = st.data_editor(
                    t_data["players"],
                    num_rows="dynamic",
                    disabled=t_data["locked"],
                    column_config={
                        "img": st.column_config.ImageColumn("Photo"),
                        "name": st.column_config.TextColumn("Name", required=True)
                    }
                )

                st.markdown("### Courts")
                t_data["courts"] = st.data_editor(
                    t_data["courts"],
                    num_rows="dynamic",
                    disabled=t_data["locked"]
                )

                if st.button("🚀 Generate / Regenerate Bracket", type="primary", disabled=t_data["locked"]):
                    if t_data["format"] == "Single Elimination":
                        t_data["bracket"] = generate_bracket(t_data["players"])
                    elif t_data["format"] == "Round Robin":
                        t_data["bracket"] = generate_round_robin(t_data["players"])
                    elif t_data["format"] == "Double Elimination":
                        t_data["bracket"] = {"winner": generate_bracket(t_data["players"]), "loser": []}
                    elif t_data["format"] == "Group Stage + Knockout":
                        t_data["bracket"] = generate_groups(t_data["players"])

                    t_data["winners"] = {}
                    t_data["scores"] = {}

                    df_db.loc[df_db["Tournament"] == selected_t, "Data"] = str(t_data)
                    if save_db(df_db):
                        df_db = load_db()
                        st.success("Bracket generated!")
                        st.balloons()
                        st.rerun()

                # Delete tournament
                st.markdown("---")
                st.subheader("Danger Zone")
                delete_confirm = st.checkbox("Confirm: permanently delete this tournament")
                if delete_confirm and st.button("🗑️ Delete Tournament", type="primary"):
                    df_db = df_db[df_db["Tournament"] != selected_t]
                    if save_db(df_db):
                        st.success(f"Tournament **{selected_t}** deleted!")
                        if "tournament_select_main" in st.session_state:
                            del st.session_state["tournament_select_main"]
                        st.rerun()
                    else:
                        st.error("Delete failed – check connection")

        # ── Main tabs: Progress first, Order of Play second ──
        tab_progress, tab_order = st.tabs(["📊 PROGRESS", "📅 ORDER OF PLAY"])

        # ────── PROGRESS ──────
        with tab_progress:
            st.subheader(f"Progress: {selected_t}")

            if t_data.get("bracket") is None:
                st.info("No bracket generated yet. (Admin can generate via sidebar)")
            else:
                # Clean stale winners
                valid_names = {p["name"] for p in t_data["players"]} | {"BYE"}
                to_remove = [k for k, v in t_data["winners"].items() if v not in valid_names and v is not None]
                for k in to_remove:
                    del t_data["winners"][k]

                champion = None

                if t_data["format"] == "Round Robin":
                    wins = {p['name']: 0 for p in t_data["players"] if p['name'] != "BYE"}
                    for v in t_data["winners"].values():
                        if v in wins: wins[v] += 1
                    leaderboard = pd.DataFrame(
                        [{"Avatar": get_p_img(n, t_data["players"]), "Player": n, "Wins": w} for n, w in wins.items()]
                    ).sort_values("Wins", ascending=False)
                    st.dataframe(leaderboard, hide_index=True, use_container_width=True,
                                 column_config={"Avatar": st.column_config.ImageColumn(width="small")})

                    if not leaderboard.empty and leaderboard.iloc[0]["Wins"] > 0:
                        champion = leaderboard.iloc[0]["Player"]

                    for r_idx, rnd in enumerate(t_data["bracket"]):
                        with st.expander(f"Round {r_idx + 1}"):
                            for m_idx, match in enumerate(rnd):
                                if len(match) < 2 or match[1] == "BYE": continue
                                k = f"rr_r{r_idx}_m{m_idx}_{selected_t}"
                                st.markdown(f"""
                                <div class="match-card">
                                    <div class="player-row">
                                        <img src="{get_p_img(match[0], t_data['players'])}" class="player-avatar"> 
                                        <strong>{match[0]}</strong>
                                    </div>
                                    <div class="vs-divider">VS</div>
                                    <div class="player-row">
                                        <img src="{get_p_img(match[1], t_data['players'])}" class="player-avatar"> 
                                        <strong>{match[1]}</strong>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                                c1, c2 = st.columns([3, 4])
                                with c1:
                                    options = [None, match[0], match[1]]
                                    idx = options.index(t_data["winners"].get(k)) if t_data["winners"].get(k) in options else 0
                                    sel = st.selectbox("Winner", options, index=idx, key=f"win_{k}")
                                    t_data["winners"][k] = sel
                                with c2:
                                    t_data["scores"][k] = st.text_input("Score", t_data["scores"].get(k, ""), key=f"score_{k}")

                elif t_data["format"] == "Group Stage + Knockout" and isinstance(t_data["bracket"], dict):
                    for g_idx, group_players in enumerate(t_data["bracket"].get("groups", [])):
                        with st.expander(f"Group {g_idx+1} – {', '.join(group_players)}"):
                            wins = {p: 0 for p in group_players}
                            for r_idx, rnd in enumerate(t_data["bracket"]["group_matches"][g_idx]):
                                for m_idx, match in enumerate(rnd):
                                    if len(match) < 2 or match[1] == "BYE": continue
                                    k = f"group{g_idx}_r{r_idx}_m{m_idx}_{selected_t}"
                                    saved = t_data["winners"].get(k)
                                    options = [None, match[0], match[1]]
                                    idx = options.index(saved) if saved in options else 0
                                    st.markdown(f"""
                                    <div class="match-card">
                                        <div class="player-row">
                                            <img src="{get_p_img(match[0], t_data['players'])}" class="mini-avatar"> 
                                            <strong>{match[0]}</strong>
                                        </div>
                                        <div class="vs-divider">VS</div>
                                        <div class="player-row">
                                            <img src="{get_p_img(match[1], t_data['players'])}" class="mini-avatar"> 
                                            <strong>{match[1]}</strong>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    c1, c2 = st.columns([3, 4])
                                    with c1:
                                        sel = st.selectbox("Winner", options, index=idx, key=f"win_{k}")
                                        t_data["winners"][k] = sel
                                        if sel: wins[sel] += 1
                                    with c2:
                                        t_data["scores"][k] = st.text_input("Score", t_data["scores"].get(k, ""), key=f"score_{k}")
                            st.dataframe(
                                pd.DataFrame([{"Avatar": get_p_img(p, t_data["players"]), "Player": p, "Wins": w} for p, w in wins.items()])
                                  .sort_values("Wins", ascending=False),
                                hide_index=True,
                                use_container_width=True,
                                column_config={"Avatar": st.column_config.ImageColumn(width="small")}
                            )

                else:  # Single / Double Elimination
                    bracket_data = t_data["bracket"] if isinstance(t_data["bracket"], list) else t_data["bracket"].get("winner", [])
                    curr_round = bracket_data
                    round_num = 1
                    while len(curr_round) > 0:
                        st.markdown(f"#### Round {round_num}")
                        cols = st.columns(max(1, min(4, len(curr_round))))
                        next_round = []
                        for i, match in enumerate(curr_round):
                            with cols[i % len(cols)]:
                                if match[1] == "BYE":
                                    st.success(f"→ {match[0]} advances (BYE)")
                                    next_round.append(match[0])
                                elif "TBD" in match:
                                    st.caption("Waiting...")
                                    next_round.append("TBD")
                                else:
                                    k = f"r{round_num}_m{i}_{selected_t}"
                                    st.markdown(f"""
                                    <div class="match-card">
                                        <div class="player-row">
                                            <img src="{get_p_img(match[0], t_data['players'])}" class="player-avatar"> 
                                            <strong>{match[0]}</strong>
                                        </div>
                                        <div class="vs-divider">VS</div>
                                        <div class="player-row">
                                            <img src="{get_p_img(match[1], t_data['players'])}" class="player-avatar"> 
                                            <strong>{match[1]}</strong>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    options = [None, match[0], match[1]]
                                    saved = t_data["winners"].get(k)
                                    idx = options.index(saved) if saved in options else 0
                                    sel = st.selectbox("Winner", options, index=idx, key=f"win_{k}")
                                    t_data["winners"][k] = sel
                                    t_data["scores"][k] = st.text_input("Score", t_data["scores"].get(k, ""), key=f"score_{k}")
                                    next_round.append(sel if sel else "TBD")
                        if len(next_round) > 1:
                            curr_round = [next_round[j:j+2] for j in range(0, len(next_round), 2)]
                            round_num += 1
                            st.markdown("<div class='round-arrow'>↓ NEXT ROUND ↓</div>", unsafe_allow_html=True)
                        else:
                            if next_round and next_round[0] not in ["TBD", None, ""]:
                                champion = next_round[0]
                            break

                if champion:
                    st.balloons()
                    st.markdown(f"""
                    <div style="text-align:center; padding:40px; background:linear-gradient(45deg,#ca8a04,#fbbf24); border-radius:20px; color:#0f172a; margin:20px 0;">
                        <div style="font-size:1.8em;">🏆 CHAMPION 🏆</div>
                        <img src="{get_p_img(champion, t_data['players'])}" style="width:140px;height:140px;border-radius:50%;border:5px solid #0f172a;margin:20px 0;">
                        <div style="font-size:2.4em;font-weight:bold;">{champion}</div>
                    </div>
                    """, unsafe_allow_html=True)

                if st.button("💾 SAVE PROGRESS", type="primary", use_container_width=True):
                    t_data["last_sync"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    df_db.loc[df_db["Tournament"] == selected_t, "Data"] = str(t_data)
                    if save_db(df_db):
                        st.success("Progress saved!")
                        st.rerun()
                    else:
                        st.error("Save failed – check connection")

        # ────── ORDER OF PLAY ──────
        with tab_order:
            st.subheader(f"Order of Play: {selected_t}")

            if t_data.get("bracket") is None:
                st.info("No bracket generated yet.")
            else:
                st.success("Matches ready for scheduling")

                matches = t_data["bracket"] if isinstance(t_data["bracket"], list) else t_data["bracket"].get("winner", [])
                matches = [m for m in matches if len(m) == 2 and "BYE" not in m]

                num_courts = len(t_data["courts"]) or 1
                courts = t_data["courts"] or ["Court 1"]

                cols = st.columns(2)
                for i, match in enumerate(matches):
                    col = cols[i % 2]
                    court = courts[i % num_courts]
                    with col:
                        st.markdown(f"""
                        <div class="match-card">
                            <div class="court-header">Court {court}</div>
                            <div class="player-row">
                                <img src="{get_p_img(match[0], t_data['players'])}" class="player-avatar">
                                <strong>{match[0]}</strong>
                            </div>
                            <div class="vs-divider">VS</div>
                            <div class="player-row">
                                <img src="{get_p_img(match[1], t_data['players'])}" class="player-avatar">
                                <strong>{match[1]}</strong>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
