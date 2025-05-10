import streamlit as st
import random
import math
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

st.set_page_config(page_title="Dev's Easy Tournament Organiser", layout="wide")
st.title("🎾 Dev's Easy Tournament Organiser")

# 🔔 Info about randomisation
st.info("📢 Teams are randomly assigned to courts to ensure fairness.")

# Session state
if 'court_allocations' not in st.session_state:
    st.session_state.court_allocations = {}
if 'tournament_name' not in st.session_state:
    st.session_state.tournament_name = "Untitled Tournament"
if 'tournament_rules' not in st.session_state:
    st.session_state.tournament_rules = ""

# Show tournament name and allocations
if st.session_state.court_allocations:
    st.markdown(f"### 🏆 {st.session_state.tournament_name}")
    st.markdown("### 🏟️ Court Allocations")

    courts = list(st.session_state.court_allocations.items())
    num_cols = 4
    num_rows = math.ceil(len(courts) / num_cols)

    for i in range(num_rows):
        cols = st.columns(num_cols)
        for j in range(num_cols):
            idx = i * num_cols + j
            if idx < len(courts):
                court_name, teams = courts[idx]
                with cols[j]:
                    st.markdown(f"#### {court_name}")
                    if teams:
                        for team in teams:
                            st.markdown(f"- 🎽 **{team}**")
                    else:
                        st.markdown("_No teams assigned._")
    st.markdown("---")

    # Display Tournament Rules if present
    if st.session_state.tournament_rules.strip():
        st.markdown("### 📘 Tournament Rules")
        st.markdown(st.session_state.tournament_rules, unsafe_allow_html=True)

    # --- PDF Download ---
    def generate_pdf(tournament_name, court_allocations, rules_html):
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(200, 750, tournament_name)
        c.setFont("Helvetica", 12)

        y_position = 730
        # Court allocations
        for court, teams in court_allocations.items():
            c.drawString(50, y_position, court)
            y_position -= 20
            for team in teams:
                c.drawString(70, y_position, f"- {team}")
                y_position -= 15
            y_position -= 10

        # Tournament rules
        if rules_html.strip():
            c.showPage()
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, 750, "Tournament Rules")
            c.setFont("Helvetica", 12)
            for line in rules_html.splitlines():
                c.drawString(50, y_position, line.strip())
                y_position -= 15
                if y_position < 100:
                    c.showPage()
                    y_position = 750

        c.save()
        buffer.seek(0)
        return buffer

    pdf_buffer = generate_pdf(
        st.session_state.tournament_name,
        st.session_state.court_allocations,
        st.session_state.tournament_rules
    )
    st.download_button(
        label="📄 Download Tournament Schedule as PDF",
        data=pdf_buffer,
        file_name="tournament_schedule.pdf",
        mime="application/pdf"
    )

# Setup form
with st.form("tournament_form"):
    st.subheader("📝 Tournament Setup")

    tournament_name = st.text_input("Enter Tournament Name", value=st.session_state.tournament_name)
    num_teams = st.number_input("Number of Teams", min_value=2, step=1)
    num_courts = st.number_input("Number of Courts", min_value=1, step=1)

    use_custom_names = st.radio(
        "Do you want to enter custom team names?",
        options=["No", "Yes"],
        horizontal=True,
    )

    team_names = []
    if num_teams % 2 == 0:
        if use_custom_names == "Yes":
            st.subheader("👥 Enter Team Names")
            for i in range(num_teams):
                name = st.text_input(f"Team {i+1}", key=f"team_{i}")
                team_names.append(name if name.strip() else f"Team {i+1}")
        else:
            team_names = [f"Team {i+1}" for i in range(num_teams)]
    else:
        st.warning("⚠️ Odd number of teams detected. Please add one more team for even distribution.")

    rules = st.text_area("📘 Optional: Paste Tournament Rules (rich text supported)", height=200)

    submit = st.form_submit_button("🎲 Organise Tournament")

# Process logic
if submit and num_teams % 2 == 0:
    st.session_state.tournament_name = tournament_name.strip() or "Untitled Tournament"
    st.session_state.tournament_rules = rules
    random.shuffle(team_names)
    base = num_teams // num_courts
    remainder = num_teams % num_courts

    court_allocations = {}
    idx = 0
    for i in range(num_courts):
        count = base + (1 if i < remainder else 0)
        if count % 2 != 0:
            count -= 1
        court_allocations[f"Court {i+1}"] = team_names[idx:idx+count]
        idx += count

    st.session_state.court_allocations = court_allocations
    st.rerun()
