import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import math
import ast
import datetime
import re

# ────────────────────────────────────────────────
# PAGE CONFIG + GOOGLE FONT (Orbitron – futuristic)
# ────────────────────────────────────────────────
st.set_page_config(page_title="Tennis Tournament Organiser", layout="wide", page_icon="🎾")

st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&display=swap" rel="stylesheet">
    <style>
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        font-family: 'Orbitron', sans-serif;
    }
    h1, h2, h3, h4, h5, h6, .stMarkdown h1, .stMarkdown h2 {
        font-family: 'Orbitron', sans-serif;
        font-weight: 700;
    }
    /* rest of your previous CSS ... */
    .stTabs [data-baseweb="tab"] {
        font-family: 'Orbitron', sans-serif;
        font-weight: 500;
    }
    .stButton > button {
        font-family: 'Orbitron', sans-serif;
    }
    </style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# CONNECTION & UTILITIES (same as before)
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
    except:
        return False

# ────────────────────────────────────────────────
# GENERATORS (unchanged)
# ────────────────────────────────────────────────

def generate_bracket(participants): ...     # your existing function
def generate_round_robin(participants): ... # your existing function
def generate_groups(participants): ...      # your existing function

# ────────────────────────────────────────────────
# MAIN APP
# ────────────────────────────────────────────────
st.title("🎾 Tennis Tournament Organiser")
df_db = load_db()
tournament_list = df_db["Tournament"].dropna().unique().tolist()

with st.sidebar:
    st.header("Admin Desk")
    new_t = st.text_input("New Tournament Name", key="new_t_name")
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
                "admin_password": admin_pw_new,   # stored in plain text (for simplicity)
                "last_sync": "Never"
            }
            new_row = pd.DataFrame([{"Tournament": new_t, "Data": str(init_data)}])
            if save_db(pd.concat([df_db, new_row], ignore_index=True)):
                st.success(f"Tournament **{new_t}** created! Password set.")
                st.rerun()
        elif not admin_pw_new:
            st.warning("Please set an admin password")

    selected_t = st.selectbox("Select Tournament", ["-- Select --"] + tournament_list)

# ────────────────────────────────────────────────
if selected_t != "-- Select --":
    row = df_db[df_db["Tournament"] == selected_t]
    if not row.empty:
        t_data = ast.literal_eval(row["Data"].values[0])

        # Default keys
        defaults = {
            "scores": {}, "winners": {}, "players": [], "courts": ["Court 1"],
            "format": "Single Elimination", "locked": False, "bracket": None,
            "admin_password": ""
        }
        for k, v in defaults.items():
            t_data.setdefault(k, v)

        if isinstance(t_data["players"][0], str) if t_data.get("players") else False:
            t_data["players"] = [{"name": p, "img": ""} for p in t_data["players"]]

        tab1, tab2, tab3 = st.tabs(["⚙️ SETUP", "📅 ORDER OF PLAY", "📊 PROGRESS"])

        # ────── SETUP TAB ──────
        with tab1:
            st.markdown("<h2 style='text-align:center;'>Tournament Setup</h2>", unsafe_allow_html=True)

            # Password check for editing rights
            correct_pw = t_data.get("admin_password", "")
            if "setup_authorized" not in st.session_state:
                st.session_state.setup_authorized = False

            if not st.session_state.setup_authorized:
                entered_pw = st.text_input("Enter admin password to edit setup", type="password", key=f"pw_{selected_t}")
                if st.button("Unlock Editing"):
                    if entered_pw == correct_pw:
                        st.session_state.setup_authorized = True
                        st.success("✅ Editing unlocked")
                        st.rerun()
                    else:
                        st.error("❌ Incorrect password")
            else:
                st.success("🔓 Editing mode active")
                if st.button("Lock Editing (logout)"):
                    st.session_state.setup_authorized = False
                    st.rerun()

                # ── Only show editable content when authorized ──
                t_data["locked"] = st.toggle("🔒 Lock tournament (view-only)", value=t_data.get("locked", False))

                # Format selection with radio + info
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
                    "Tournament Format",
                    options=format_options,
                    index=format_options.index(t_data.get("format", "Single Elimination")),
                    horizontal=True,
                    captions=captions,
                    key=f"format_{selected_t}",
                    disabled=t_data["locked"] or not st.session_state.setup_authorized
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

                if st.button("🚀 Generate / Regenerate Bracket", type="primary", disabled=not st.session_state.setup_authorized):
                    # your generation logic here...
                    if t_data["format"] == "Single Elimination":
                        t_data["bracket"] = generate_bracket(t_data["players"])
                    # ... etc ...
                    t_data["winners"] = {}
                    t_data["scores"] = {}
                    df_db.loc[df_db["Tournament"] == selected_t, "Data"] = str(t_data)
                    if save_db(df_db):
                        st.success("Bracket (re)generated!")
                        st.rerun()

        # ────── ORDER OF PLAY & PROGRESS tabs remain mostly unchanged ──────
        # (you can keep your existing code for tab2 and tab3)
        # Important: tab3 (progress / scoring) should NOT require password
        # so do NOT wrap it in authorization check

        with tab3:
            # ... your existing progress code ...
            # Anyone can enter winners & scores here
            # No authorization check needed
            pass

        # Save any changes made (especially password-protected ones)
        if st.session_state.setup_authorized or "scores" in t_data or "winners" in t_data:
            df_db.loc[df_db["Tournament"] == selected_t, "Data"] = str(t_data)
            save_db(df_db)   # can be called on change or on button
