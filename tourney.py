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
    
    /* Graphical Match Cards */
    .match-card {{
        background: rgba(2, 46, 133, 0.8); border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px; border-radius: 15px; margin-bottom: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        display: flex; flex-direction: column; align-items: center;
    }}
    .court-header {{ color: #4ade80 !important; font-size: 0.8em; text-transform: uppercase; margin-bottom: 12px; font-weight: bold; }}
    .player-row {{ display: flex; align-items: center; gap: 15px; width: 100%; justify-content: center; margin: 8px 0; }}
    .player-avatar {{
        width: 50px; height: 50px; border-radius: 50%; object-fit: cover;
        border: 2px solid #4ade80; background-color: #022e85;
    }}
    .player-name {{ color: #ffffff; font-size: 1.1em; font-weight: 500; min-width: 100px; }}
    .vs-divider {{ color: rgba(255,255,255,0.3); font-style: italic; font-size: 0.9em; margin: 5px 0; }}
    .sync-time {{ font-size: 0.8em; color: #4ade80; opacity: 0.8; margin-top: 10px; }}
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE HELPERS ---
def load_db():
    try:
        df = conn.read(ttl=0)
        if df is None or df.empty or "Tournament" not in df.columns:
            return pd.DataFrame(columns=["Tournament", "Data"])
        return df
    except:
        return pd.DataFrame(columns=["Tournament", "Data"])

def save_db(df):
    try:
        conn.update(data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return False

# --- UTILITY: GOOGLE DRIVE IMAGE CONVERTER ---
def get_p_img(name, player_list):
    placeholder = 'https://www.gravatar.com/avatar/000?d=mp'
    for p in player_list:
        if p['name'] == name:
            url = p.get('img', '')
            if not url: return placeholder
            
            # Convert Google Drive Sharing Link to Direct Download Link
            if "drive.google.com" in url:
                match = re.search(r'/d/([^/]+)', url)
                if match:
                    file_id = match.group(1)
                    return f"https://drive.google.com/uc?export=view&id={file_id}"
            return url
    return placeholder

# --- TOURNAMENT LOGIC ---
def generate_bracket(participants):
    names = [p['name'] for p in participants if p['name'].strip()]
    random.shuffle(names)
    if not names: return None
    next_pow_2 = 2**math.ceil(math.log2(len(names)))
    full_slots = names + (["BYE"] * (next_pow_2 - len(names)))
    bracket = []
    for i in range(next_pow_2 // 2):
        bracket.append([full_slots[i], full_slots[next_pow_2 - 1 - i]])
    return bracket

def generate_round_robin(participants):
    names = [p['name'] for p in participants if p['name'].strip()]
    if len(names) < 2: return None
    if len(names) % 2 != 0: names.append("BYE")
    n = len(names)
    rounds = []
    p_list = names[:]
    for i in range(n - 1):
        matches = []
        for j in range(n // 2):
            matches.append([p_list[j], p_list[n - 1 - j]])
        rounds.append(matches)
        p_list = [p_list[0]] + [p_list[-1]] + p_list[1:-1]
    return rounds

# --- MAIN APP ---
st.title("🎾 Tournament Organiser Pro")
df_db = load_db()
tournament_list = df_db["Tournament"].dropna().unique().tolist()

with st.sidebar:
    st.header("Admin Desk")
    new_t = st.text_input("Tournament Name")
    if st.button("✨ Create New"):
        if new_t and new_t not in tournament_list:
            init_data = {
                "players": [{"name": f"Player {i+1}", "img": ""} for i in range(4)], 
                "courts": ["Court 1"], "format": "Single Elimination", "bracket": None, 
                "winners": {}, "locked": False, "last_sync": "Never"
            }
            new_row = pd.DataFrame([{"Tournament": new_t, "Data": str(init_data)}])
            if save_db(pd.concat([df_db, new_row], ignore_index=True)): st.rerun()

    selected_t = st.selectbox("Select Active Tournament", ["-- Select --"] + tournament_list)
    if selected_t != "-- Select --":
        st.divider()
        if st.button("🗑️ Delete Tournament", type="secondary", width="stretch"):
            if save_db(df_db[df_db["Tournament"] != selected_t]): st.rerun()

if selected_t != "-- Select --":
    row = df_db[df_db["Tournament"] == selected_t]
    if not row.empty:
        t_data = ast.literal_eval(row["Data"].values[0])
        
        # Ensure data structure is correct for players
        if t_data.get("players") and isinstance(t_data["players"][0], str):
            t_data["players"] = [{"name": p, "img": ""} for p in t_data["players"]]

        tab1, tab2, tab3 = st.tabs(["⚙️ SETUP", "📅 ORDER OF PLAY", "📊 PROGRESS"])

        with tab1:
            st.markdown("### 🛠️ Configuration")
            t_data["locked"] = st.toggle("🔒 Lock Tournament (Prevents edits)", value=t_data.get("locked", False))
            
            # HELP BOX FOR GOOGLE DRIVE
            st.info("""
            💡 **Google Drive Images:** For player thumbnails to work, you must:
            1. Right-click the image in Drive -> **Share**.
            2. Change General Access to **'Anyone with the link'**.
            3. Paste the share link into the 'img' column below.
            """)
            
            t_data["format"] = st.radio("Tournament Format", ["Single Elimination", "Round Robin"], 
                                       index=0 if t_data.get("format") == "Single Elimination" else 1, 
                                       disabled=t_data["locked"], horizontal=True)
            
            st.write("**Participants & Profile Images**")
            t_data["players"] = st.data_editor(
                t_data["players"], 
                num_rows="dynamic", 
                key=f"p_{selected_t}", 
                disabled=t_data["locked"], 
                width="stretch",
                column_config={
                    "img": st.column_config.ImageColumn("Avatar Preview", help="Paste Google Drive Share Link here"),
                    "name": "Player Name"
                }
            )
            
            st.write("**Available Courts**")
            t_data["courts"] = st.data_editor(t_data["courts"], num_rows="dynamic", key=f"c_{selected_t}", disabled=t_data["locked"], width="stretch")
            
            if st.button("🚀 GENERATE & INITIALIZE", type="primary", width="stretch", disabled=t_data["locked"]):
                t_data["bracket"] = generate_bracket(t_data["players"]) if t_data["format"] == "Single Elimination" else generate_round_robin(t_data["players"])
                t_data["winners"] = {}
                df_db.loc[df_db["Tournament"] == selected_t, "Data"] = str(t_data)
                if save_db(df_db):
                    st.success("✅ Tournament Built! Go to Order of Play.")
                    st.balloons()

        with tab2:
            if t_data.get("bracket"):
                # Adapt current matches view based on format
                if t_data["format"] == "Single Elimination":
                    active = [m for m in t_data["bracket"] if isinstance(m, list) and len(m) == 2 and "BYE" not in m]
                else: 
                    active = [m for m in t_data["bracket"][0] if isinstance(m, list) and len(m) == 2 and "BYE" not in m]
                
                if active:
                    cols = st.columns(min(len(t_data["courts"]), 3)) # Max 3 cards per row for better look
                    for i, match in enumerate(active):
                        p1_n, p2_n = match[0], match[1]
                        p1_i = get_p_img(p1_n, t_data["players"])
                        p2_i = get_p_img(p2_n, t_data["players"])
                        
                        with cols[i % len(cols)]:
                            st.markdown(f"""
                                <div class='match-card'>
                                    <span class='court-header'>📍 {t_data['courts'][i % len(t_data['courts'])]}</span>
                                    <div class='player-row'>
                                        <img src='{p1_i}' class='player-avatar'>
                                        <span class='player-name'>{p1_n}</span>
                                    </div>
                                    <div class='vs-divider'>vs</div>
                                    <div class='player-row'>
                                        <img src='{p2_i}' class='player-avatar'>
                                        <span class='player-name'>{p2_n}</span>
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("No active matches found. Check if the tournament is over or all players have BYEs.")
            else: st.info("Please generate the tournament in the **SETUP** tab.")

        with tab3:
            if t_data.get("bracket"):
                if t_data["format"] == "Round Robin":
                    # --- LEADERBOARD ---
                    st.markdown("### 🏆 Leaderboard")
                    wins = {p['name']: 0 for p in t_data["players"] if p['name'] != "BYE"}
                    for k, v in t_data["winners"].items():
                        if v and v in wins: wins[v] += 1
                    
                    ld_data = [{"Avatar": get_p_img(n, t_data["players"]), "Player": n, "Wins": w} for n, w in wins.items()]
                    leader_df = pd.DataFrame(ld_data).sort_values(by="Wins", ascending=False)
                    st.dataframe(leader_df, hide_index=True, width="stretch", column_config={"Avatar": st.column_config.ImageColumn()})
                    
                    # --- SCHEDULE ---
                    st.markdown("### 📅 Match Schedule")
                    for r_idx, rnd in enumerate(t_data["bracket"]):
                        with st.expander(f"Round {r_idx + 1}"):
                            for m_idx, match in enumerate(rnd):
                                if len(match) < 2: continue
                                p1, p2 = match[0], match[1]
                                if p2 == "BYE": st.text(f"⚪ {p1} (BYE)")
                                else:
                                    k = f"rr_r{r_idx}_m{m_idx}_{selected_t}"
                                    cur_win = t_data["winners"].get(k)
                                    idx = [None, p1, p2].index(cur_win) if cur_win in [p1, p2] else 0
                                    t_data["winners"][k] = st.selectbox(f"{p1} vs {p2}", [None, p1, p2], index=idx, key=k)
                else:
                    # --- SINGLE ELIMINATION ---
                    current_round = t_data["bracket"]
                    r_num = 1
                    while len(current_round) >= 1:
                        st.markdown(f"#### Round {r_num}")
                        cols = st.columns(len(current_round))
                        nxt_rnd = []
                        for i, match in enumerate(current_round):
                            if len(match) < 2: continue
                            with cols[i]:
                                p1, p2 = match[0], match[1]
                                if p2 == "BYE":
                                    st.success(f"⏩ {p1}")
                                    nxt_rnd.append(p1)
                                elif p1 == "TBD" or p2 == "TBD":
                                    st.caption("Waiting for results...")
                                    nxt_rnd.append("TBD")
                                else:
                                    k = f"r{r_num}_m{i}_{selected_t}"
                                    cur_win = t_data["winners"].get(k)
                                    idx = [None, p1, p2].index(cur_win) if cur_win in [p1, p2] else 0
                                    win = st.selectbox(f"{p1} vs {p2}", [None, p1, p2], index=idx, key=k, disabled=t_data["locked"])
                                    t_data["winners"][k] = win
                                    nxt_rnd.append(win if win else "TBD")
                        if len(nxt_rnd) > 1:
                            current_round = [nxt_rnd[j:j+2] for j in range(0, len(nxt_rnd), 2)]
                            r_num += 1
                            st.divider()
                        else:
                            if nxt_rnd and nxt_rnd[0] not in ["TBD", None]: 
                                st.success(f"🎊 **Tournament Champion: {nxt_rnd[0]}** 🎊")
                            break

                st.divider()
                if st.button("💾 SAVE ALL PROGRESS", type="primary", width="stretch"):
                    t_data["last_sync"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    df_db.loc[df_db["Tournament"] == selected_t, "Data"] = str(t_data)
                    if save_db(df_db): st.toast(f"Cloud Synced at {t_data['last_sync']}")
                st.markdown(f"<div class='sync-time'>Last Cloud Sync: {t_data['last_sync']}</div>", unsafe_allow_html=True)
