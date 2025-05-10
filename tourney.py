
import streamlit as st
import random
import math
from fpdf import FPDF

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
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(200, 10, txt=tournament_name, ln=True, align='C')
        pdf.ln(10)

        for court, teams in court_allocations.items():
            pdf.set_font("Arial", "B", 12)
            pdf.cell(200, 10, txt=court, ln=True)
            pdf.set_font("Arial", "", 12)
            for team in teams:
                pdf.cell(200, 8, txt=f"  - {team}", ln=True)
            pdf.ln(5)

        if rules_html.strip():
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(200, 10, txt="Tournament Rules", ln=True)
            pdf.set_font("Arial", "", 12)
            for line in rules_html.splitlines():
                clean_line = line.strip().replace('<br>', '').replace('&nbsp;', ' ')
                pdf.multi_cell(0, 8, txt=clean_line, align='L')

        return pdf.output(dest='S').encode('latin-1')

    pdf_bytes = generate_pdf(
        st.session_state.tournament_name,
        st.session_state.court_allocations,
        st.session_state.tournament_rules
    )
    st.download_button(
        label="📄 Download Tournament Schedule as PDF",
        data=pdf_bytes,
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
