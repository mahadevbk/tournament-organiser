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
st.markdown(f"""
    <style>
    .stApp {{ background-color: #001e5c; font-family: 'sans serif'; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 24px; background-color: #022e85; padding: 10px 20px; border-radius: 10px; }}
    .stTabs [data-baseweb="tab"] {{ height: 50px; color: #ffffff; font-weight: 600; }}
    .stTabs [aria-selected="true"] {{ background-color: #001e5c !important; border-bottom: 2px solid #4ade80 !important; }}
    
    .champ-container {{
        text-align: center; background: linear-gradient(135deg, #022e85 0%, #001e5c 100%);
        padding: 40px; border-radius: 20px; border: 3px solid #ffd700; margin: 20px 0;
        box-shadow: 0 0 30px rgba(255, 215, 0, 0.3);
    }}
    .champ-avatar {{
        width: 150px; height: 150px; border-radius: 50%; object-fit: cover;
        border: 5px solid #ffd700; margin-bottom: 15px;
    }}
    .champ-name {{ color: #ffd700; font-size: 2.5em; font-weight: bold; text-transform: uppercase; }}
    
    .match-card {{
        background: rgba(2, 46, 133, 0.8); border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px; border-radius: 15px; margin-bottom: 15px; display: flex; flex-direction: column; align-items: center;
    }}
    .player-row {{ display: flex; align-items: center; gap: 15px; width: 100%; justify-content: center; margin: 8px 0; color: white; }}
    .player-avatar {{ width: 50px; height: 50px; border-radius: 50%; object-fit: cover; border: 2px solid #4ade80; }}
    .mini-avatar {{ width: 35px; height: 35px; border-radius: 50%; object-fit: cover; border: 1px solid #4ade80; vertical-align: middle; margin-right: 10px; }}
    .vs-divider {{ color: rgba(255,255,255,0.3); font-style: italic; font-size: 0.9em; margin: 5px 0; }}
    .sync-time {{ font-size: 0.8em; color: #4ade80; opacity: 0.8; margin-top: 10px; }}
    </style>
    """, unsafe_allow_html=True)

# --- UTILITY: GOOGLE DRIVE IMAGE CONVERTER ---
def get_p_img(name, player_list):
    placeholder = 'https://www.gravatar.com/avatar/000?d=mp'
    if name in ["BYE", "TBD", None]: return placeholder
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
    except: return pd.DataFrame(columns=["Tournament", "Data"])

def save_db(df):
    try:
        conn.update(data=df)
        st.cache_data.clear()
        return True
    except: return False

# --- TOURNAMENT LOGIC ---
def generate_bracket(participants):
    names = [p['name'] if isinstance(p, dict) else str(p) for p in participants]
    names = [n.strip() for n in names if n.strip()]
    random.shuffle(names)
    if not names: return None
    next_pow_2 = 2**math.ceil(math.log2(len(names)))
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

# --- MAIN APP ---
st.title("🎾 Tournament Organiser")
df_db = load_db()
tournament_list = df_db["Tournament"].dropna().unique().tolist()

with st.sidebar:
    st.header("Admin Desk")
    new_t = st.text_input("Tournament Name")
    if st.button("✨ Create New"):
        if new_t and new_t not in tournament_list:
            init_data = {"players": [{"name": f"Player {i+1}", "img": ""} for i in range(4)], "courts": ["Court 1"], "format": "Single Elimination", "bracket": None, "winners": {}, "locked": False, "last_sync": "Never"}
            if save_db(pd.concat([df_db, pd.DataFrame([{"Tournament": new_t, "Data": str(init_data)}])], ignore_index=True)): st.rerun()
    
    selected_t = st.selectbox("Select Tournament", ["-- Select --"] + tournament_list)
    if selected_t != "-- Select --":
        if st.button("🗑️ Delete", type="secondary", width="stretch"):
            if save_db(df_db[df_db["Tournament"] != selected_t]): st.rerun()

if selected_t != "-- Select --":
    row = df_db[df_db["Tournament"] == selected_t]
    if not row.empty:
        t_data = ast.literal_eval(row["Data"].values[0])
        if "players" in t_data and len(t_data["players"]) > 0 and isinstance(t_data["players"][0], str):
            t_data["players"] = [{"name": p, "img": ""} for p in t_data["players"]]

        tab1, tab2, tab3 = st.tabs(["⚙️ SETUP", "📅 ORDER OF PLAY", "📊 PROGRESS"])

        with tab1:
            t_data["locked"] = st.toggle("🔒 Lock Tournament", value=t_data.get("locked", False))
            st.info("💡 **Google Drive:** Paste share link set to 'Anyone with the link'.")
            t_data["format"] = st.radio("Format", ["Single Elimination", "Round Robin"], index=0 if t_data.get("format") == "Single Elimination" else 1, disabled=t_data["locked"], horizontal=True)
            t_data["players"] = st.data_editor(t_data["players"], num_rows="dynamic", key=f"p_{selected_t}", disabled=t_data["locked"], width="stretch", column_config={"img": st.column_config.ImageColumn("Avatar"), "name": "Name"})
            t_data["courts"] = st.data_editor(t_data["courts"], num_rows="dynamic", key=f"c_{selected_t}", disabled=t_data["locked"], width="stretch")
            
            if st.button("🚀 GENERATE", type="primary", width="stretch", disabled=t_data["locked"]):
                t_data["bracket"] = generate_bracket(t_data["players"]) if t_data["format"] == "Single Elimination" else generate_round_robin(t_data["players"])
                t_data["winners"] = {}
                df_db.loc[df_db["Tournament"] == selected_t, "Data"] = str(t_data)
                if save_db(df_db): st.rerun()

        with tab2:
            if t_data.get("bracket"):
                active = (t_data["bracket"] if t_data["format"] == "Single Elimination" else t_data["bracket"][0])
                active = [m for m in active if len(m) == 2 and "BYE" not in m]
                cols = st.columns(min(len(t_data["courts"]), 3))
                for i, match in enumerate(active):
                    p1_i, p2_i = get_p_img(match[0], t_data["players"]), get_p_img(match[1], t_data["players"])
                    with cols[i % len(cols)]:
                        st.markdown(f"<div class='match-card'><span class='court-header'>📍 {t_data['courts'][i % len(t_data['courts'])]}</span><div class='player-row'><img src='{p1_i}' class='player-avatar'> {match[0]}</div><div class='vs-divider'>vs</div><div class='player-row'><img src='{p2_i}' class='player-avatar'> {match[1]}</div></div>", unsafe_allow_html=True)

        with tab3:
            if t_data.get("bracket"):
                champion = None
                if t_data["format"] == "Round Robin":
                    wins = {p['name']: 0 for p in t_data["players"] if p['name'] != "BYE"}
                    for k, v in t_data["winners"].items(): 
                        if v in wins: wins[v] += 1
                    ld_df = pd.DataFrame([{"Avatar": get_p_img(n, t_data["players"]), "Player": n, "Wins": w} for n, w in wins.items()]).sort_values(by="Wins", ascending=False)
                    st.dataframe(ld_df, hide_index=True, width="stretch", column_config={"Avatar": st.column_config.ImageColumn()})
                    if not ld_df.empty and ld_df.iloc[0]['Wins'] > 0: champion = ld_df.iloc[0]['Player']
                    
                    for r_idx, rnd in enumerate(t_data["bracket"]):
                        with st.expander(f"Round {r_idx + 1}"):
                            for m_idx, match in enumerate(rnd):
                                if len(match) < 2: continue
                                k = f"rr_r{r_idx}_m{m_idx}_{selected_t}"
                                cur_win = t_data["winners"].get(k)
                                idx = [None, match[0], match[1]].index(cur_win) if cur_win in match else 0
                                st.markdown(f"<img src='{get_p_img(match[0], t_data['players'])}' class='mini-avatar'> **{match[0]}** vs <img src='{get_p_img(match[1], t_data['players'])}' class='mini-avatar'> **{match[1]}**", unsafe_allow_html=True)
                                t_data["winners"][k] = st.selectbox(f"Winner:", [None, match[0], match[1]], index=idx, key=k)
                else:
                    # FIXED BRACKET PROGRESSION
                    curr_round_matches = t_data["bracket"]
                    r_num = 1
                    while len(curr_round_matches) >= 1:
                        st.markdown(f"#### Round {r_num}")
                        cols = st.columns(len(curr_round_matches))
                        next_round_players = []
                        for i, match in enumerate(curr_round_matches):
                            with cols[i]:
                                if len(match) == 2:
                                    p1, p2 = match[0], match[1]
                                    if p2 == "BYE":
                                        st.success(f"⏩ {p1}")
                                        next_round_players.append(p1)
                                    elif p1 == "TBD" or p2 == "TBD":
                                        st.caption("Waiting...")
                                        next_round_players.append("TBD")
                                    else:
                                        st.markdown(f"<img src='{get_p_img(p1, t_data['players'])}' class='mini-avatar'> vs <img src='{get_p_img(p2, t_data['players'])}' class='mini-avatar'>", unsafe_allow_html=True)
                                        k = f"r{r_num}_m{i}_{selected_t}"
                                        options = [None, p1, p2]
                                        saved_val = t_data["winners"].get(k)
                                        idx = options.index(saved_val) if saved_val in options else 0
                                        win = st.selectbox(f"Winner", options, index=idx, key=k)
                                        t_data["winners"][k] = win
                                        next_round_players.append(win if win else "TBD")
                        
                        if len(next_round_players) > 1:
                            # Group the winners into pairs for the next round
                            curr_round_matches = [next_round_players[j:j+2] for j in range(0, len(next_round_players), 2)]
                            r_num += 1
                            st.divider()
                        else:
                            # We have reached the final winner
                            if next_round_players and next_round_players[0] not in ["TBD", None]:
                                champion = next_round_players[0]
                            break

                if champion:
                    st.balloons()
                    st.markdown(f"""
                        <div class='champ-container'>
                            <div style='color: #ffd700; font-size: 1.2em; letter-spacing: 2px;'>🏆 TOURNAMENT CHAMPION 🏆</div>
                            <img src='{get_p_img(champion, t_data['players'])}' class='champ-avatar'>
                            <div class='champ-name'>{champion}</div>
                        </div>
                    """, unsafe_allow_html=True)

                if st.button("💾 SAVE PROGRESS", type="primary", width="stretch"):
                    t_data["last_sync"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    df_db.loc[df_db["Tournament"] == selected_t, "Data"] = str(t_data)
                    save_db(df_db); st.toast("Synced!")
