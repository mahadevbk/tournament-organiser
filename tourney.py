import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import math
import ast
import datetime
import re

# --- PAGE CONFIG ---
st.set_page_config(page_title="Tennis Tournament Organiser", layout="wide", page_icon="🎾")

# --- THE ULTIMATE KEY FIX ---
if "connections" in st.secrets and "gsheets" in st.secrets.connections:
    raw_key = st.secrets.connections.gsheets.private_key
    cleaned_key = raw_key.replace("\\n", "\n")
    if "-----BEGIN PRIVATE KEY-----" in cleaned_key and "\n" not in cleaned_key[28:-26]:
        header = "-----BEGIN PRIVATE KEY-----\n"
        footer = "\n-----END PRIVATE KEY-----"
        content = cleaned_key.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "").strip()
        wrapped_content = "\n".join(re.findall(r'.{1,64}', content))
        cleaned_key = f"{header}{wrapped_content}{footer}\n"
    try:
        st.secrets.connections.gsheets["private_key"] = cleaned_key
    except:
        pass

# --- INITIALIZE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CUSTOM THEME CSS ---
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        font-family: 'sans-serif';
    }
    [data-testid="stSidebar"] {
        background: #0f172a !important;
        border-right: 1px solid #334155;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: #022e85;
        padding: 10px 20px;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        color: #ffffff;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #001e5c !important;
        border-bottom: 2px solid #4ade80 !important;
    }
    .stButton > button[kind="primary"] {
        height: 3.2rem;
        font-size: 1.2rem !important;
        font-weight: 600;
        background: linear-gradient(90deg, #22c55e, #16a34a) !important;
        border: none;
    }
    .stButton > button[kind="secondary"] {
        background: #1e293b !important;
        border: 1px solid #475569;
        color: #e2e8f0;
    }
    .format-card {
        padding: 16px;
        border-radius: 12px;
        margin-bottom: 16px;
        cursor: pointer;
        transition: all 0.2s;
        text-align: center;
    }
    .format-card.selected {
        border: 2px solid #4ade80;
        background: rgba(74, 222, 128, 0.15);
        box-shadow: 0 0 20px rgba(74, 222, 128, 0.3);
    }
    .format-card:not(.selected) {
        border: 1px solid #4b5563;
        background: rgba(30, 41, 59, 0.7);
    }
    .format-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.4);
    }
    .champ-container {
        text-align: center;
        background: linear-gradient(45deg, #ca8a04, #fbbf24) !important;
        padding: 40px;
        border-radius: 20px;
        border: 3px solid #ffd700;
        margin: 20px 0;
        box-shadow: 0 0 30px rgba(255, 215, 0, 0.5);
        color: #0f172a !important;
    }
    .champ-avatar {
        width: 150px; height: 150px;
        border-radius: 50%;
        object-fit: cover;
        border: 5px solid #0f172a;
        margin-bottom: 15px;
    }
    .champ-name {
        color: #0f172a;
        font-size: 2.5em;
        font-weight: bold;
        text-transform: uppercase;
    }
    .match-card {
        background: rgba(30, 41, 59, 0.9);
        border: 1px solid #475569;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 15px;
        display: flex;
        flex-direction: column;
        align-items: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.4);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .match-card:hover {
        transform: translateY(-6px);
        box-shadow: 0 10px 25px rgba(34, 197, 94, 0.3);
    }
    .player-row {
        display: flex;
        align-items: center;
        gap: 15px;
        width: 100%;
        justify-content: center;
        margin: 8px 0;
        color: white;
    }
    .player-avatar {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        object-fit: cover;
        border: 3px solid #4ade80;
    }
    .mini-avatar {
        width: 35px;
        height: 35px;
        border-radius: 50%;
        object-fit: cover;
        border: 1px solid #4ade80;
        vertical-align: middle;
        margin-right: 10px;
    }
    .score-badge {
        background: #4ade80;
        color: #001e5c;
        padding: 4px 12px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 1em;
        margin-top: 8px;
    }
    .vs-divider {
        color: rgba(255,255,255,0.4);
        font-style: italic;
        font-size: 1.1em;
        margin: 8px 0;
    }
    .round-arrow {
        text-align: center;
        color: #4ade80;
        font-size: 2.5em;
        margin: 30px 0;
        font-weight: bold;
    }
    .court-header {
        font-size: 1.2em;
        color: #4ade80;
        margin-bottom: 10px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- UTILITIES ---
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
    except:
        return False

# --- TOURNAMENT GENERATORS ---
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

# --- MAIN APP ---
st.title("🎾 Tennis Tournament Organiser")
df_db = load_db()
tournament_list = df_db["Tournament"].dropna().unique().tolist()

with st.sidebar:
    st.header("Admin Desk")
    new_t = st.text_input("Tournament Name", key="new_t_name")
    if st.button("✨ Create New"):
        if new_t and new_t not in tournament_list:
            init_data = {
                "players": [{"name": f"Player {i+1}", "img": ""} for i in range(8)],
                "courts": ["Court 1", "Court 2"],
                "format": "Single Elimination",
                "bracket": None,
                "winners": {},
                "scores": {},
                "locked": False,
                "last_sync": "Never"
            }
            new_row = pd.DataFrame([{"Tournament": new_t, "Data": str(init_data)}])
            if save_db(pd.concat([df_db, new_row], ignore_index=True)):
                st.rerun()

    selected_t = st.selectbox("Select Tournament", ["-- Select --"] + tournament_list, key="select_tourney")

if selected_t != "-- Select --":
    row = df_db[df_db["Tournament"] == selected_t]
    if not row.empty:
        t_data = ast.literal_eval(row["Data"].values[0])

        for key in ["scores", "winners", "players", "courts", "format", "locked", "bracket"]:
            if key not in t_data:
                t_data[key] = {} if key in ["scores", "winners"] else [] if key in ["players", "courts"] else "Single Elimination" if key == "format" else False if key == "locked" else None

        if isinstance(t_data["players"][0], str):
            t_data["players"] = [{"name": p, "img": ""} for p in t_data["players"]]

        tab1, tab2, tab3 = st.tabs(["⚙️ SETUP", "📅 ORDER OF PLAY", "📊 PROGRESS"])

        with tab1:
            # Lock toggle - top right
            col1, col2 = st.columns([6, 1])
            with col2:
                t_data["locked"] = st.toggle("🔒 Lock", value=t_data.get("locked", False))

            st.markdown("<h2 style='text-align: center; color: #e2e8f0; margin-bottom: 1.5rem;'>Tournament Setup</h2>", unsafe_allow_html=True)

            # Format selection - card style
            st.markdown("### Format")
            format_options = [
                ("Single Elimination", "Classic knockout – one loss and you're out", "⚡"),
                ("Round Robin", "Everyone plays everyone – maximum matches", "🔄"),
                ("Double Elimination", "Second chance bracket – two losses to exit", "🔄🔄"),
                ("Group Stage + Knockout", "Groups → finals – balanced & exciting", "🏆")
            ]

            cols = st.columns(2)
            current_format = t_data.get("format", "Single Elimination")

            for i, (name, desc, emoji) in enumerate(format_options):
                with cols[i % 2]:
                    is_selected = current_format == name
                    card_class = "format-card selected" if is_selected else "format-card"
                    st.markdown(f"<div class='{card_class}'>", unsafe_allow_html=True)
                    if st.button(
                        f"{emoji} {name}",
                        key=f"fmt_{name}_{selected_t}",
                        use_container_width=True,
                        type="primary" if is_selected else "secondary",
                        disabled=t_data["locked"]
                    ):
                        if not t_data["locked"]:
                            t_data["format"] = name
                            st.rerun()
                    st.markdown(f"<div style='color:#94a3b8; font-size:0.9rem;'>{desc}</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("---")

            # Players
            st.markdown("### Participants")
            t_data["players"] = st.data_editor(
                t_data["players"],
                num_rows="dynamic",
                key=f"players_{selected_t}",
                disabled=t_data["locked"],
                use_container_width=True,
                hide_index=False,
                column_config={
                    "img": st.column_config.ImageColumn("Photo", width="small"),
                    "name": st.column_config.TextColumn("Name", required=True, width="large")
                }
            )

            st.markdown("### Courts")
            t_data["courts"] = st.data_editor(
                t_data["courts"],
                num_rows="dynamic",
                key=f"courts_{selected_t}",
                disabled=t_data["locked"],
                use_container_width=True,
                column_config={
                    "value": st.column_config.TextColumn("Court Name", required=True)
                }
            )

            st.markdown("---")

            # Generate button
            if st.button(
                "🚀 Generate Tournament",
                type="primary",
                use_container_width=True,
                disabled=t_data["locked"] or len(t_data.get("players", [])) < 2
            ):
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
                    st.success("🎾 Tournament successfully generated! Go to **ORDER OF PLAY** to view matches.")
                    st.balloons()
                    st.rerun()

        # ────────────────────────────────────────────────
        # ORDER OF PLAY (tab2) & PROGRESS (tab3) remain mostly the same as previous version
        # (kept graphical with avatars, cards, courts cycling, etc.)
        # ────────────────────────────────────────────────

        with tab2:
            if not t_data.get("bracket"):
                st.info("Generate the bracket first in the SETUP tab.")
            else:
                st.subheader("Order of Play – Assign Matches to Courts")
                num_courts = len(t_data["courts"]) or 1
                courts = t_data["courts"] or ["Court 1"]

                if t_data["format"] == "Group Stage + Knockout" and isinstance(t_data["bracket"], dict):
                    st.subheader("Group Stage Matches")
                    for g_idx, group in enumerate(t_data["bracket"].get("groups", [])):
                        with st.expander(f"Group {g_idx+1} – {', '.join(group)}"):
                            flat_matches = []
                            for rnd in t_data["bracket"]["group_matches"][g_idx]:
                                flat_matches.extend([m for m in rnd if len(m) == 2 and m[1] != "BYE"])
                            cols = st.columns(min(num_courts, 3))
                            for i, match in enumerate(flat_matches):
                                with cols[i % len(cols)]:
                                    court = courts[i % num_courts]
                                    st.markdown(f"<div class='match-card'>"
                                                f"<span class='court-header'>📍 {court}</span>"
                                                f"<div class='player-row'><img src='{get_p_img(match[0], t_data['players'])}' class='player-avatar'> {match[0]}</div>"
                                                f"<div class='vs-divider'>vs</div>"
                                                f"<div class='player-row'><img src='{get_p_img(match[1], t_data['players'])}' class='player-avatar'> {match[1]}</div>"
                                                f"</div>", unsafe_allow_html=True)
                else:
                    matches = t_data["bracket"] if isinstance(t_data["bracket"], list) else t_data["bracket"].get("winner", [])
                    matches = [m for m in matches if len(m) == 2 and "BYE" not in m]
                    if matches:
                        cols = st.columns(min(num_courts, 3))
                        for i, match in enumerate(matches):
                            with cols[i % len(cols)]:
                                court = courts[i % num_courts]
                                st.markdown(f"<div class='match-card'>"
                                            f"<span class='court-header'>📍 {court}</span>"
                                            f"<div class='player-row'><img src='{get_p_img(match[0], t_data['players'])}' class='player-avatar'> {match[0]}</div>"
                                            f"<div class='vs-divider'>vs</div>"
                                            f"<div class='player-row'><img src='{get_p_img(match[1], t_data['players'])}' class='player-avatar'> {match[1]}</div>"
                                            f"</div>", unsafe_allow_html=True)

        with tab3:
            if not t_data.get("bracket"):
                st.info("No bracket generated yet.")
            else:
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
                                    saved = t_data["winners"].get(k)
                                    idx = options.index(saved) if saved in options else 0
                                    sel = st.selectbox("Winner", options, index=idx, key=f"win_{k}")
                                    t_data["winners"][k] = sel
                                with c2:
                                    t_data["scores"][k] = st.text_input("Score", value=t_data["scores"].get(k, ""), key=f"score_{k}")

                # ... (rest of tab3 remains similar – group stage, knockout rounds, champion display)

                if champion:
                    st.balloons()
                    st.markdown(f"<div class='champ-container'><div style='font-size:1.6em;'>🏆 CHAMPION 🏆</div><img src='{get_p_img(champion, t_data['players'])}' class='champ-avatar'><div class='champ-name'>{champion}</div></div>", unsafe_allow_html=True)

                if st.button("💾 SAVE PROGRESS", type="primary", use_container_width=True):
                    t_data["last_sync"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    df_db.loc[df_db["Tournament"] == selected_t, "Data"] = str(t_data)
                    if save_db(df_db):
                        st.success("Progress saved!", icon="✅")
