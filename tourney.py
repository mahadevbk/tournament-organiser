import streamlit as st
import random
import math

st.set_page_config(page_title="Dev's Easy Tournament Organiser", layout="centered")

st.title("🎾 Dev's Easy Tournament Organiser")

# Step 1: Input number of teams and courts
num_teams = st.number_input("Enter the number of teams", min_value=2, step=1)
num_courts = st.number_input("Enter the number of courts", min_value=1, step=1)

# Validate even team count
if num_teams % 2 != 0:
    st.warning("⚠️ You have entered an odd number of teams. Please add one more team for even distribution.")
else:
    # Step 2: Enter team names
    st.subheader("Enter Team Names")
    team_names = []
    for i in range(num_teams):
        name = st.text_input(f"Team {i+1} name", key=f"team_{i}")
        team_names.append(name if name else f"Team {i+1}")

    # Step 3: Randomise and distribute
    if st.button("Organise Tournament"):
        random.shuffle(team_names)

        # Calculate base number of teams per court
        base = num_teams // num_courts
        remainder = num_teams % num_courts

        court_allocations = {}
        idx = 0
        for i in range(num_courts):
            count = base + (1 if i < remainder else 0)
            # Ensure only even number of teams per court
            if count % 2 != 0:
                count -= 1
            court_allocations[f"Court {i+1}"] = team_names[idx:idx+count]
            idx += count

        # Step 4: Display allocation
        st.subheader("🏟️ Final Court Allocations")
        for court, teams in court_allocations.items():
            st.markdown(f"**{court}:**")
            for team in teams:
                st.write(f"• {team}")
            if not teams:
                st.write("• No teams assigned.")
