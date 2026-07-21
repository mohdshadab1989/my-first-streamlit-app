import pandas as pd
import streamlit as st

# --- Helper function to calculate working hours per shift ---
def calculate_row_hours(row):
    total = 0.0
    # Process Morning Shift
    if row.get('M. In') not in ['OFF', 'ABSENT', None, ''] and row.get('M. Out') not in ['OFF', 'ABSENT', None, '']:
        try:
            t_in = pd.to_datetime(row['M. In'], format='%H:%M')
            t_out = pd.to_datetime(row['M. Out'], format='%H:%M')
            total += (t_out - t_in).total_seconds() / 3600.0
        except Exception:
            pass

    # Process Evening Shift
    if row.get('E. In') not in ['OFF', 'ABSENT', None, ''] and row.get('E. Out') not in ['OFF', 'ABSENT', None, '']:
        try:
            t_in = pd.to_datetime(row['E. In'], format='%H:%M')
            t_out = pd.to_datetime(row['E. Out'], format='%H:%M')
            total += (t_out - t_in).total_seconds() / 3600.0
        except Exception:
            pass

    return total


# --- Fetch / Define Logs DataFrame First ---
# If you store logs in session_state, load them here. Otherwise, fetch from database/file.
if "logs" in st.session_state and st.session_state["logs"] is not None:
    df_logs = pd.DataFrame(st.session_state["logs"])
else:
    # Fallback to empty DataFrame with expected columns if no data is found
    df_logs = pd.DataFrame(columns=['Employee', 'Date', 'M. In', 'M. Out', 'E. In', 'E. Out'])

# Filter by Employee if dropdown is used
if not df_logs.empty and 'Employee' in df_logs.columns:
    employees = df_logs['Employee'].unique().tolist()
    selected_emp = st.selectbox("Filter by Employee Name", options=employees)
    if selected_emp:
        df_logs = df_logs[df_logs['Employee'] == selected_emp]

# --- Edit Logs & History Section ---
if df_logs is not None and not df_logs.empty:
    # 1. FIX SERIAL NUMBER / INDEX
    df_display = df_logs.copy().reset_index(drop=True)
    df_display.index = df_display.index + 1  # Sequential serial number starting from 1

    # 2. CALCULATE TOTAL HOURS
    df_display['Hours_Worked'] = df_display.apply(calculate_row_hours, axis=1)
    total_hours = df_display['Hours_Worked'].sum()

    df_editor_input = df_display.drop(columns=['Hours_Worked'])

    # Display Editable Table
    edited_df = st.data_editor(
        df_editor_input,
        use_container_width=True,
        key="history_editor"
    )

    # 3. DISPLAY TOTAL HOURS ON THE BOTTOM RIGHT
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("Save Changes to Database"):
            # Update session state or save to DB logic
            st.success("Changes saved successfully!")
    with col2:
        st.metric(label="TOTAL HOURS", value=f"{total_hours:.2f} hrs")
else:
    st.info("No records found to display.")
