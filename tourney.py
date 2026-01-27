import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import math
import ast
import datetime
import re

# ────────────────────────────────────────────────
# PAGE CONFIG + FUTURISTIC FONT
# ────────────────────────────────────────────────
st.set_page_config(page_title="Tennis Tournament Organiser", layout="wide", page_icon="🎾")

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;900&display=swap" rel="stylesheet">
<style>
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        font-family: 'Orbitron', sans-serif !important;
    }
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Orbitron', sans-serif;
        font-weight: 700;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'Orbitron', sans-serif;
        font-weight: 500;
    }
    .stButton > button {
        font-family: 'Orbitron', sans-serif;
        font-weight: 600;
    }
    .match-card {
        background: rgba(30, 41, 59, 0.9);
        border: 1px solid #475569;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.4);
        transition: all 0.2s;
    }
    .match-card:hover {
        transform: translateY(-6px);
        box-shadow: 0 10px 25px rgba(34, 197, 94, 0.3);
    }
    .player-row {
        display: flex;
        align-items: center;
        gap: 15px;
        justify-content: center;
        color: white;
    }
    .player-avatar {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        object-fit: cover;
        border: 3px solid #4ade80;
    }
    .vs-divider {
        color: rgba(255,255,255,0.4);
        font-style: italic;
        font-size: 1.1em;
        margin: 8px 0;
    }
    .court-header {
        font-size: 1.2em;
        color: #4ade80;
        margin-bottom: 10px;
        font-weight: bold;
    }
    div.row-widget.stRadio > div {
        flex-direction: row;
        justify-content: space-around;
        gap: 12px;
        flex-wrap: wrap;
    }
    div.row-widget.stRadio > div > label {
        background: #1e293b;
        border: 1px solid #475569;
        border-radius: 8px;
        padding: 12px 16px;
        flex: 1 1 180px;
        text-align: center;
        min-width: 140px;
    }
    div.row-widget.stRadio > div > label[data-checked="true"] {
        background: rgba(74, 222, 128, 0.25) !important;
        border-color: #4ade80 !important;
        box-shadow: 0 0 12px rgba(74, 222, 128, 0.4);
    }
    div.row-widget.stRadio > div > label > div[data-testid="stCaption"] {
        color: #94a3b8;
        font-size: 0.85rem;
        margin-top: 6px;
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

with st.sidebar:
    st.header("Admin Desk")
    new_t = st.text_input("New Tournament Name")
    admin_pw_new = st.text_input("Set Admin Password", type="password")

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
            st.warning("Please enter a unique name and set a password")

    selected_t = st.selectbox("Select Tournament", ["-- Select --"] + tournament_list)

if selected_t != "-- Select --":
    row = df_db[df_db["Tournament"] == selected_t]
    if not row.empty:
        t_data = ast.literal_eval(row["Data"].values[0])

        # Ensure keys exist
        defaults = {
            "scores": {}, "winners": {}, "players": [], "courts": ["Court 1"],
            "format": "Single Elimination", "locked": False, "bracket": None,
            "admin_password": ""
        }
        for k, v in defaults.items():
            if k not in t_data:
                t_data[k] = v

        if t_data.get("players") and isinstance(t_data["players"][0], str):
            t_data["players"] = [{"name": p, "img": ""} for p in t_data["players"]]

        tab1, tab2, tab3 = st.tabs(["⚙️ SETUP", "📅 ORDER OF PLAY", "📊 PROGRESS"])

        # Authorization for SETUP editing
        if "setup_authorized" not in st.session_state:
            st.session_state.setup_authorized = False

        # ────── SETUP TAB ──────
        with tab1:
            st.markdown("<h2 style='text-align:center;'>Tournament Setup</h2>", unsafe_allow_html=True)

            correct_pw = t_data.get("admin_password", "")

            if not st.session_state.setup_authorized:
                entered_pw = st.text_input("Enter admin password to edit", type="password", key=f"pw_setup_{selected_t}")
                if st.button("Unlock Editing"):
                    if entered_pw == correct_pw:
                        st.session_state.setup_authorized = True
                        st.success("✅ Editing unlocked")
                        st.rerun()
                    else:
                        st.error("❌ Wrong password")
            else:
                st.success("🔓 Editing mode active")
                if st.button("Lock Editing"):
                    st.session_state.setup_authorized = False
                    st.rerun()

                t_data["locked"] = st.toggle("🔒 Lock tournament", value=t_data.get("locked", False))

                st.markdown("### Format")
                format_options = ["Single Elimination", "Round Robin", "Double Elimination", "Group Stage + Knockout"]
                captions = ["One loss → out", "Everyone vs everyone", "Two losses → out", "Groups → finals"]
                descriptions = {
                    "Single Elimination": "Classic knockout. One loss = eliminated. Fast & simple.",
                    "Round Robin": "Everyone plays everyone. Most matches, very fair.",
                    "Double Elimination": "Two losses to be out. More games, second chance bracket.",
                    "Group Stage + Knockout": "Group stage → top advance to knockout. Balanced & exciting."
                }

                fmt = st.radio(
                    "Select format",
                    options=format_options,
                    index=format_options.index(t_data.get("format", "Single Elimination")),
                    horizontal=True,
                    captions=captions,
                    disabled=t_data["locked"] or not st.session_state.setup_authorized,
                    key=f"format_radio_{selected_t}"
                )
                t_data["format"] = fmt

                with st.container(border=True):
                    st.info(descriptions.get(fmt, ""), icon="ℹ️")

                st.divider()

                st.markdown("### Participants")
                t_data["players"] = st.data_editor(
                    t_data["players"],
                    num_rows="dynamic",
                    disabled=t_data["locked"] or not st.session_state.setup_authorized,
                    column_config={
                        "img": st.column_config.ImageColumn("Photo"),
                        "name": st.column_config.TextColumn("Name", required=True)
                    }
                )

                st.markdown("### Courts")
                t_data["courts"] = st.data_editor(
                    t_data["courts"],
                    num_rows="dynamic",
                    disabled=t_data["locked"] or not st.session_state.setup_authorized
                )

                if st.button("🚀 Generate / Regenerate", type="primary",
                             disabled=t_data["locked"] or not st.session_state.setup_authorized):
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
                        df_db = load_db()  # force refresh
                        st.success("Tournament generated successfully!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Save failed – check connection")

        # ────── ORDER OF PLAY ──────
        with tab2:
            if t_data.get("bracket") is None:
                st.info("No bracket generated yet. Go to SETUP and generate.")
            else:
                st.subheader("Order of Play")
                num_courts = len(t_data["courts"]) or 1
                courts = t_data["courts"] or ["Court 1"]

                if t_data["format"] == "Group Stage + Knockout" and isinstance(t_data["bracket"], dict):
                    for g_idx, group in enumerate(t_data["bracket"].get("groups", [])):
                        with st.expander(f"Group {g_idx+1} – {', '.join(group)}"):
                            flat = []
                            for rnd in t_data["bracket"]["group_matches"][g_idx]:
                                flat.extend([m for m in rnd if len(m) == 2 and m[1] != "BYE"])
                            cols = st.columns(min(num_courts, 3))
                            for i, m in enumerate(flat):
                                with cols[i % len(cols)]:
                                    st.markdown(f"<div class='match-card'>"
                                                f"<span class='court-header'>📍 {courts[i % num_courts]}</span>"
                                                f"<div class='player-row'><img src='{get_p_img(m[0], t_data['players'])}' class='player-avatar'> {m[0]}</div>"
                                                f"<div class='vs-divider'>vs</div>"
                                                f"<div class='player-row'><img src='{get_p_img(m[1], t_data['players'])}' class='player-avatar'> {m[1]}</div>"
                                                f"</div>", unsafe_allow_html=True)
                else:
                    matches = t_data["bracket"] if isinstance(t_data["bracket"], list) else t_data["bracket"].get("winner", [])
                    matches = [m for m in matches if len(m) == 2 and "BYE" not in m]
                    cols = st.columns(min(num_courts, 3))
                    for i, m in enumerate(matches):
                        with cols[i % len(cols)]:
                            st.markdown(f"<div class='match-card'>"
                                        f"<span class='court-header'>📍 {courts[i % num_courts]}</span>"
                                        f"<div class='player-row'><img src='{get_p_img(m[0], t_data['players'])}' class='player-avatar'> {m[0]}</div>"
                                        f"<div class='vs-divider'>vs</div>"
                                        f"<div class='player-row'><img src='{get_p_img(m[1], t_data['players'])}' class='player-avatar'> {m[1]}</div>"
                                        f"</div>", unsafe_allow_html=True)

        # ────── PROGRESS ────── (open to everyone)
        with tab3:
            if t_data.get("bracket") is None:
                st.info("No bracket generated yet.")
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
                    st.subheader("Leaderboard")
                    st.dataframe(leaderboard, hide_index=True, use_container_width=True,
                                 column_config={"Avatar": st.column_config.ImageColumn(width="small")})

                    if not leaderboard.empty and leaderboard.iloc[0]["Wins"] > 0:
                        champion = leaderboard.iloc[0]["Player"]

                    for r_idx, rnd in enumerate(t_data["bracket"]):
                        with st.expander(f"Round {r_idx + 1}"):
                            for m_idx, match in enumerate(rnd):
                                if len(match) < 2 or match[1] == "BYE": continue
                                k = f"rr_r{r_idx}_m{m_idx}_{selected_t}"
                                st.markdown(f"<div class='match-card'>"
                                            f"<div class='player-row'><img src='{get_p_img(match[0], t_data['players'])}' class='player-avatar'> **{match[0]}**</div>"
                                            f"<div class='vs-divider'>vs</div>"
                                            f"<div class='player-row'><img src='{get_p_img(match[1], t_data['players'])}' class='player-avatar'> **{match[1]}**</div>"
                                            f"</div>", unsafe_allow_html=True)
                                c1, c2 = st.columns([3, 4])
                                with c1:
                                    options = [None, match[0], match[1]]
                                    idx = options.index(t_data["winners"].get(k)) if t_data["winners"].get(k) in options else 0
                                    sel = st.selectbox("Winner", options, index=idx, key=f"win_{k}")
                                    t_data["winners"][k] = sel
                                with c2:
                                    t_data["scores"][k] = st.text_input("Score", t_data["scores"].get(k, ""), key=f"score_{k}")

                # ... (add your Group Stage and Knockout logic here similarly)

                if champion:
                    st.balloons()
                    st.markdown(f"<div class='champ-container'><div>🏆 CHAMPION 🏆</div><img src='{get_p_img(champion, t_data['players'])}' class='champ-avatar'><div class='champ-name'>{champion}</div></div>", unsafe_allow_html=True)

                if st.button("💾 SAVE PROGRESS", type="primary"):
                    t_data["last_sync"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    df_db.loc[df_db["Tournament"] == selected_t, "Data"] = str(t_data)
                    if save_db(df_db):
                        st.success("Saved!")
                    else:
                        st.error("Save failed")
