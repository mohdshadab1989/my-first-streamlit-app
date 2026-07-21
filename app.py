import pandas as pd
import streamlit as st

# --- Helper function to calculate working hours per shift ---
def calculate_row_hours(row):
    total = 0.0
    # Process Morning Shift
    if row['M. In'] not in ['OFF', 'ABSENT', None, ''] and row['M. Out'] not in ['OFF', 'ABSENT', None, '']:
        try:
            t_in = pd.to_datetime(row['M. In'], format='%H:%M')
            t_out = pd.to_datetime(row['M. Out'], format='%H:%M')
            total += (t_out - t_in).total_seconds() / 3600.0
        except Exception:
            pass

    # Process Evening Shift
    if row['E. In'] not in ['OFF', 'ABSENT', None, ''] and row['E. Out'] not in ['OFF', 'ABSENT', None, '']:
        try:
            t_in = pd.to_datetime(row['E. In'], format='%H:%M')
            t_out = pd.to_datetime(row['E. Out'], format='%H:%M')
            total += (t_out - t_in).total_seconds() / 3600.0
        except Exception:
            pass

    return total


# --- Edit Logs & History Section ---
# Assuming `df_logs` is your filtered dataframe loaded from the database:

if not df_logs.empty:
    # 1. FIX SERIAL NUMBER / INDEX
    # Reset index so it counts sequentially (1, 2, 3, ...) regardless of database ID
    df_display = df_logs.copy().reset_index(drop=True)
    df_display.index = df_display.index + 1  # Start serial count at 1

    # 2. CALCULATE TOTAL HOURS
    # Apply calculation row by row
    df_display['Hours_Worked'] = df_display.apply(calculate_row_hours, axis=1)
    total_hours = df_display['Hours_Worked'].sum()

    # Drop the temporary calculation column if you don't want it editable in data_editor
    df_editor_input = df_display.drop(columns=['Hours_Worked'])

    # Display Editable Table
    edited_df = st.data_editor(
        df_editor_input,
        use_container_width=True,
        key="history_editor"
    )

    # 3. DISPLAY TOTAL HOURS ON THE RIGHT DOWN SIDE
    col1, col2 = st.columns([3, 1])
    with col1:
        st.button("Save Changes to Database")
    with col2:
        st.metric(label="TOTAL HOURS", value=f"{total_hours:.2f} hrs")
