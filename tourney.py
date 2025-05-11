import streamlit as st
import random
from fpdf import FPDF
from io import BytesIO

st.set_page_config(page_title="Dev's Easy Tournament Organiser", page_icon="court.png")

st.title("Dev's Easy Tournament Organiser 🎾")
st.markdown("<small><i>Assignments of teams and courts are done randomly.</i></small>", unsafe_allow_html=True)

# Input fields
st.subheader("Tournament Setup")
tournament_name = st.text_input("Enter Tournament Name")
num_teams = st.number_input("Enter number of teams", min_value=2, step=1)
num_courts = st.number_input("Enter number of courts", min_value=1, step=1)
enter_names = st.radio("Do you want to enter team names?", ("No", "Yes"))
enter_court_names = st.radio("Do you want to enter court names?", ("No", "Yes"))

# Collect team names early, depending on radio selection
team_names = []
if num_teams and enter_names == "Yes":
    st.subheader("Enter Team Names")
    if num_teams <= 8:
        cols = st.columns(2)
    elif num_teams <= 16:
        cols = st.columns(3)
    else:
        cols = st.columns(4)

    for i in range(num_teams):
        col = cols[i % len(cols)]
        with col:
            name = st.text_input(f"Team {i+1} Name", key=f"team_{i}")
            team_names.append(name if name else f"Team {i+1}")
else:
    team_names = [f"Team {i+1}" for i in range(num_teams)]

# Optional court names
court_names = []
if num_courts and enter_court_names == "Yes":
    st.subheader("Enter Court Names")
    for i in range(num_courts):
        key = f"court_name_{i}"
        if key not in st.session_state:
            st.session_state[key] = f"Court {i+1}"
        name = st.text_input(f"Court {i+1} Name", key=key)
        court_names.append(name)
else:
    court_names = [f"Court {i+1}" for i in range(num_courts)]

# Optional tournament rules input
rules = st.text_area("Enter Tournament Rules (optional, supports rich text)")

if num_teams % 2 != 0:
    st.warning("Number of teams is odd. Consider adding one more team for even distribution.")

if st.button("Organise Tournament"):
    random.shuffle(team_names)

    base = len(team_names) // num_courts
    extras = len(team_names) % num_courts

    courts = []
    idx = 0
    for i in range(num_courts):
        num = base + (1 if i < extras else 0)
        if num % 2 != 0:
            if i < num_courts - 1:
                num += 1
        court_teams = team_names[idx:idx+num]
        courts.append((court_names[i], court_teams))
        idx += num

    st.markdown("---")
    st.subheader("Court Assignments")

    # Dynamic court layout with styled boxes matching config.toml primary color
    primary_color = "#022e85"  # Deep blue from config.toml

    if len(courts) <= 4:
        num_cols = len(courts)
    elif len(courts) <= 8:
        num_cols = 4
    elif len(courts) <= 12:
        num_cols = 3
    else:
        num_cols = 2

    for i in range(0, len(courts), num_cols):
        row = st.columns(num_cols)
        for j, court in enumerate(courts[i:i + num_cols]):
            with row[j]:
                court_name, teams = court
                st.markdown(
                    f"""
                    <div style='border: 2px solid {primary_color}; border-radius: 12px; padding: 15px; margin: 10px 0; background-color: {primary_color}; color: white;'>
                        <img src='court.png' width='100%' style='border-radius: 8px;' />
                        <h4 style='text-align:center; color:white;'>{court_name}</h4>
                        <ul>{''.join(f'<li><b>{team}</b></li>' for team in teams)}</ul>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    if rules:
        st.subheader("Tournament Rules")
        st.markdown(rules, unsafe_allow_html=True)

    # PDF Generation
    def generate_pdf(tournament_name, courts, rules):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, tournament_name, ln=True, align="C")
        pdf.ln(10)

        pdf.set_font("Arial", '', 12)
        for court_name, teams in courts:
            pdf.set_text_color(46, 139, 87)
            pdf.cell(0, 10, court_name, ln=True)
            pdf.set_text_color(0, 0, 0)
            for team in teams:
                pdf.cell(10)
                pdf.cell(0, 10, f"- {team}", ln=True)
            pdf.ln(2)

        if rules:
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, "Tournament Rules", ln=True)
            pdf.set_font("Arial", '', 11)
            for line in rules.splitlines():
                pdf.multi_cell(0, 8, line)

        return pdf.output(dest='S').encode('latin-1')

    pdf_bytes = generate_pdf(tournament_name, courts, rules)
    st.download_button(
        label="Download PDF",
        data=pdf_bytes,
        file_name=f"{tournament_name or 'tournament'}.pdf",
        mime='application/pdf'
    )

    # Attribution
    st.markdown(
        '<small><a href="https://www.flaticon.com/free-icons/tennis" target="_blank">'
        'Tennis icons created by Smashicons - Flaticon</a></small>',
        unsafe_allow_html=True
    )
