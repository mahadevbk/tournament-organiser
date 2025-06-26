import streamlit as st
import random
from fpdf import FPDF
from io import BytesIO
import itertools
import math

st.set_page_config(page_title="Dev's Easy Tournament Organiser", page_icon="court.png")

st.title("Dev's Easy Tournament Organiser 🎾")
st.markdown("<small><i>Assignments of teams and courts are done randomly. Matches within courts and playoffs are randomized, with no team playing more than two consecutive matches.</i></small>", unsafe_allow_html=True)

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
        court_names.append(name if name else f"Court {i+1}")
else:
    court_names = [f"Court {i+1}" for i in range(num_courts)]

# Optional tournament rules input
rules = st.text_area("Enter Tournament Rules (optional, supports rich text)")

if num_teams % 2 != 0:
    st.warning("Number of teams is odd. Consider adding one more team for even distribution.")

def schedule_matches(teams):
    if len(teams) < 2:
        return []
    matches = list(itertools.combinations(teams, 2))
    random.shuffle(matches)
    scheduled = []
    team_consecutive = {team: 0 for team in teams}
    remaining_matches = matches.copy()

    while remaining_matches:
        added = False
        for match in remaining_matches[:]:
            team1, team2 = match
            if team_consecutive[team1] < 2 and team_consecutive[team2] < 2:
                scheduled.append(match)
                remaining_matches.remove(match)
                team_consecutive[team1] += 1
                team_consecutive[team2] += 1
                # Reset consecutive count for teams not in this match
                for team in teams:
                    if team not in (team1, team2):
                        team_consecutive[team] = 0
                added = True
                break
        if not added:
            # If no match can be added without breaking the rule, shuffle and try again
            random.shuffle(remaining_matches)
            # Reset consecutive counts to try a new order
            team_consecutive = {team: 0 for team in teams}
            scheduled = []
            remaining_matches = matches.copy()
    return scheduled

if st.button("Organise Tournament"):
    random.shuffle(team_names)

    # Distribute teams evenly across courts
    base = num_teams // num_courts
    remainder = num_teams % num_courts
    courts = []
    idx = 0
    for i in range(min(num_courts, num_teams)):
        num = base + (1 if i < remainder else 0)
        court_teams = team_names[idx:idx+num] if num > 0 else []
        if court_teams:
            court_idx = i % len(court_names)  # Ensure we use available court names
            courts.append((court_names[court_idx], court_teams))
        idx += num

    # Generate randomized order of play for each court with no team playing more than 2 consecutive matches
    court_matches = []
    for court_name, teams in courts:
        matches = schedule_matches(teams)
        court_matches.append((court_name, matches))

    st.markdown("---")
    st.subheader("Court Assignments and Match Schedules")

    # Dynamic court layout with styled boxes
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
        for j, (court_name, teams) in enumerate(courts[i:i + num_cols]):
            with row[j]:
                matches = next((m for c, m in court_matches if c == court_name), [])
                match_list = ''.join(f'<li>{t1} vs {t2}</li>' for t1, t2 in matches) if matches else '<li>No matches (insufficient teams)</li>'
                st.markdown(
                    f"""
                    <div style='border: 2px solid {primary_color}; border-radius: 12px; padding: 15px; margin: 10px 0; background-color: {primary_color}; color: white;'>
                        <img src='court.png' width='100%' style='border-radius: 8px;' />
                        <h4 style='text-align:center; color:white;'>{court_name}</h4>
                        <h5>Teams:</h5>
                        <ul>{''.join(f'<li>{team}</li>' for team in teams)}</ul>
                        <h5>Match Schedule:</h5>
                        <ul>{match_list}</ul>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    # Playoff bracket for court winners
    winners = [f"Winner of {court_name}" for court_name, _ in courts]
    random.shuffle(winners)
    
    st.subheader("Playoff Bracket")
    
    # Determine playoff structure
    playoff_matches = []
    num_winners = len(winners)
    
    if num_winners > 1:
        if num_winners == 2:
            # Directly to Finals for 2 courts
            playoff_matches.append(("Finals", [(winners[0], winners[1])]))
        else:
            # Check if num_winners is a power of 2
            is_power_of_2 = num_winners > 0 and (num_winners & (num_winners - 1)) == 0
            current_teams = winners.copy()
            round_num = 1

            # First Round (if num_winners is not a power of 2)
            if not is_power_of_2:
                target_teams = 2 ** math.ceil(math.log2(num_winners))
                byes = target_teams - num_winners
                first_round = []
                matches_needed = (num_winners - byes) // 2
                for i in range(0, matches_needed * 2, 2):
                    first_round.append((current_teams[i], current_teams[i+1]))
                for i in range(matches_needed * 2, num_winners):
                    first_round.append((current_teams[i], "Bye"))
                random.shuffle(first_round)
                if first_round:
                    playoff_matches.append(("First Round", first_round))
                current_teams = [f"Winner of R1M{i+1}" if t1 != "Bye" else t2 for i, (t1, t2) in enumerate(first_round)]
                random.shuffle(current_teams)

            # Subsequent rounds
            while len(current_teams) > 1:
                round_name = "Finals" if len(current_teams) == 2 else (
                    "Semi-Finals" if len(current_teams) == 4 else (
                        "Quarter-Finals" if len(current_teams) <= 8 else f"Round {round_num}"
                    )
                )
                matches = []
                for i in range(0, len(current_teams) - (len(current_teams) % 2), 2):
                    matches.append((current_teams[i], current_teams[i+1]))
                if len(current_teams) % 2 == 1 and len(current_teams) > 2:
                    matches.append((current_teams[-1], "Bye"))
                random.shuffle(matches)
                playoff_matches.append((round_name, matches))
                current_teams = [f"Winner of {round_name[:2]}M{i+1}" if t1 != "Bye" else t2 for i, (t1, t2) in enumerate(matches)]
                random.shuffle(current_teams)
                round_num += 1

    # Display playoff matches
    for round_name, matches in playoff_matches:
        st.markdown(f"### {round_name}")
        cols = st.columns(2 if len(matches) > 1 else 1)
        for idx, (team1, team2) in enumerate(matches):
            with cols[idx % len(cols)]:
                st.markdown(
                    f"""
                    <div style='border: 2px solid {primary_color}; border-radius: 12px; padding: 15px; margin: 10px 0; background-color: {primary_color}; color: white;'>
                        <h5>{round_name} Match {idx+1}</h5>
                        <p>{team1} vs {team2}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    if rules:
        st.subheader("Tournament Rules")
        st.markdown(rules, unsafe_allow_html=True)

    # PDF Generation
    def generate_pdf(tournament_name, courts, court_matches, playoff_matches, rules):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, tournament_name, ln=True, align="C")
        pdf.ln(10)

        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Court Assignments and Match Schedules", ln=True)
        pdf.set_font("Arial", '', 12)
        for court_name, teams in courts:
            pdf.set_text_color(46, 139, 87)
            pdf.cell(0, 10, court_name, ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(10)
            pdf.cell(0, 10, "Teams:", ln=True)
            for team in teams:
                pdf.cell(20)
                pdf.cell(0, 10, f"- {team}", ln=True)
            matches = next((m for c, m in court_matches if c == court_name), [])
            if matches:
                pdf.cell(10)
                pdf.cell(0, 10, "Match Schedule:", ln=True)
                for t1, t2 in matches:
                    pdf.cell(20)
                    pdf.cell(0, 10, f"- {t1} vs {t2}", ln=True)
            else:
                pdf.cell(20)
                pdf.cell(0, 10, "- No matches (insufficient teams)", ln=True)
            pdf.ln(2)

        pdf.ln(5)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Playoff Bracket", ln=True)
        pdf.set_font("Arial", '', 12)
        for round_name, matches in playoff_matches:
            pdf.cell(0, 10, round_name, ln=True)
            for idx, (t1, t2) in enumerate(matches):
                pdf.cell(10)
                pdf.cell(0, 10, f"Match {idx+1}: {t1} vs {t2}", ln=True)
            pdf.ln(2)

        if rules:
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, "Tournament Rules", ln=True)
            pdf.set_font("Arial", '', 11)
            for line in rules.splitlines():
                pdf.multi_cell(0, 8, line)

        return pdf.output(dest='S').encode('latin-1')

    pdf_bytes = generate_pdf(tournament_name, courts, court_matches, playoff_matches, rules)
    st.download_button(
        label="Download PDF",
        data=pdf_bytes,
        file_name=f"{tournament_name or 'tournament'}.pdf",
        mime='application/pdf'
    )

st.markdown("----")
st.info("Built with ❤️ using [Streamlit](https://streamlit.io/) — free and open source. [Other Scripts by dev](https://devs-scripts.streamlit.app/) on Streamlit.")
