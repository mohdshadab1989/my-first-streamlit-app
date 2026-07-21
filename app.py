import pandas as pd
import streamlit as st

# ==========================================
# 1. PAGE CONFIGURATION & CUSTOM STYLING
# ==========================================
st.set_page_config(
    page_title="Al Fanateer Studio - Timecard & Payroll",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for clean UI styling
st.markdown("""
    <style>
    .main-header {
        display: flex;
        align-items: center;
        gap: 15px;
        margin-bottom: 20px;
    }
    .logo-text {
        font-size: 26px;
        font-weight: 700;
        color: #1E293B;
    }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 2. SESSION STATE & DATABASE INITIALIZATION
# ==========================================
APP_PASSWORD = "8443"

if "app_locked" not in st.session_state:
    st.session_state["app_locked"] = False

if "logs" not in st.session_state:
    st.session_state["logs"] = pd.DataFrame([
        {"Employee": "Remson", "Date": "2026-07-04", "M. In": "11:00", "M. Out": "13:00", "E. In": "ABSENT", "E. Out": "ABSENT"},
        {"Employee": "Remson", "Date": "2026-07-03", "M. In": "OFF", "M. Out": "OFF", "E. In": "OFF", "E. Out": "OFF"},
        {"Employee": "Remson", "Date": "2026-07-02", "M. In": "10:30", "M. Out": "13:00", "E. In": "OFF", "E. Out": "OFF"},
        {"Employee": "Remson", "Date": "2026-07-01", "M. In": "10:30", "M. Out": "13:00", "E. In": "19:00", "E. Out": "22:00"},
    ])


# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def calculate_row_hours(row):
    """Calculates total hours worked in a single day across Morning and Evening shifts."""
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


# ==========================================
# 4. TOP HEADER (LOGO, TITLE & LOCK BUTTON)
# ==========================================
col_header, col_lock = st.columns([5, 1])

with col_header:
    st.markdown("""
        <div class="main-header">
            <span style="font-size: 32px;">👑</span>
            <span class="logo-text">Streamlit - Al Fanateer Studio - Timecard & Payroll</span>
        </div>
    """, unsafe_allow_html=True)

with col_lock:
    if not st.session_state["app_locked"]:
        if st.button("🔒 Lock App", use_container_width=True):
            st.session_state["app_locked"] = True
            st.rerun()

st.divider()


# ==========================================
# 5. APP CONTENT / PASSCODE LOCK SCREEN
# ==========================================
if st.session_state["app_locked"]:
    st.subheader("🔒 App Locked")
    
    lock_col1, lock_col2 = st.columns([1, 2])
    with lock_col1:
        pwd_input = st.text_input("Enter Passcode to Unlock:", type="password", key="pwd_input")
        if st.button("Unlock", type="primary"):
            if pwd_input == APP_PASSWORD:
                st.session_state["app_locked"] = False
                st.success("App unlocked successfully!")
                st.rerun()
            else:
                st.error("Incorrect passcode! Please try again.")

else:
    # Main Navigation Tabs
    tab1, tab2, tab3 = st.tabs(["➕ Log Time", "📊 Payroll Calculation", "📝 Edit Logs & History"])

    # --------------------------------------
    # TAB 1: LOG TIME
    # --------------------------------------
    with tab1:
        st.subheader("Log Daily Shift")
        st.info("Log new employee shifts, days off, or absences here.")

    # --------------------------------------
    # TAB 2: PAYROLL CALCULATION
    # --------------------------------------
    with tab2:
        st.subheader("Payroll Calculations")
        st.info("Calculate overall monthly payroll based on recorded shift history (10 SAR/hr rate).")

    # --------------------------------------
    # TAB 3: EDIT LOGS & HISTORY
    # --------------------------------------
    with tab3:
        st.title("3-Month Shift Log & Manual Edits")

        df_logs = st.session_state["logs"]

        if not df_logs.empty and "Employee" in df_logs.columns:
            # Employee Filter Dropdown
            employees = df_logs["Employee"].unique().tolist()
            selected_emp = st.selectbox("🔍 Filter by Employee Name", options=employees)

            # Filter records for selected employee
            df_filtered = df_logs[df_logs["Employee"] == selected_emp].copy()

            if not df_filtered.empty:
                # 1. SEQUENTIAL SERIAL NUMBERS (1, 2, 3...)
                df_filtered = df_filtered.drop(columns=["ID"], errors="ignore")
                df_display = df_filtered.reset_index(drop=True)
                df_display.index = df_display.index + 1  # 1-based serial index

                # 2. CALCULATE TOTAL HOURS
                df_display["Hours_Worked"] = df_display.apply(calculate_row_hours, axis=1)
                total_hours = df_display["Hours_Worked"].sum()

                # Clean dataframe input for the data editor table
                df_editor_input = df_display.drop(columns=["Hours_Worked"])

                # Display Editable Data Table
                edited_df = st.data_editor(
                    df_editor_input,
                    use_container_width=True,
                    key="history_editor"
                )

                st.write("")  # Spacing

                # 3. SAVE BUTTON & TOTAL HOURS METRIC AT BOTTOM RIGHT
                col_save, col_total = st.columns([3, 1])

                with col_save:
                    if st.button("Save Changes to Database", type="primary"):
                        st.session_state["logs"] = edited_df.reset_index(drop=True)
                        st.success("Changes saved successfully to the database!")

                with col_total:
                    st.metric(label="TOTAL HOURS", value=f"{total_hours:.2f} hrs")

            else:
                st.info("No records found for the selected employee.")
        else:
            st.info("No shift logs found in the database.")
