import streamlit as st
import random

st.set_page_config(page_title="Dev's Easy Tournament Organiser", layout="centered")
st.title("🎾 Dev's Easy Tournament Organiser")

# 🔔 Info about randomisation
st.info("📢 Teams are randomly assigned to courts to ensure fairness.")

# Session state to store final allocation
if 'court_allocations' not in st.session_state:
    st.session_state.court_allocations = {}

# Show allocations at the top
if st.session_state.court_allocations:
    st.markdown("### 🏟️ Court Allocations")
    for court, teams in st.session_state.court_allocations.items():
        with st.container():
            st.markdown(f"#### {court}")
            for team in teams:
                st.markdown(f"- 🎽 **{team}**")
            if not teams:
                st.markdown("_No teams assigned._")
    st.markdown("---")

# Setup form
with st.form("tournament_form"):
    st.subheader("📝 Tournament Setup")
    num_teams = st.number_input("Number of Teams", min_value=2, step=1)
    num_courts = st.number_input("Number of Courts", min_value=1, step=1)

    # Ask if user wants to enter custom team names
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

    submit = st.form_submit_button("🎲 Organise Tournament")

# Process tournament
if submit and num_teams % 2 == 0:
    random.shuffle(team_names)
    base = num_teams // num_courts
    remainder = num_teams % num_courts

    court_allocations = {}
    idx = 0
    for i in range(num_courts):
        count = base + (1 if i < remainder else 0)
        # Ensure even number of teams per court
        if count % 2 != 0:
            count -= 1
        court_allocations[f"Court {i+1}"] = team_names[idx:idx+count]
        idx += count

    st.session_state.court_allocations = court_allocations
    st.rerun()
