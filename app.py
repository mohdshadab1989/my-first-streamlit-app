import pandas as pd
import streamlit as st
import os
from PIL import Image

# ==========================================
# 1. PAGE CONFIGURATION & CUSTOM STYLING
# ==========================================
st.set_page_config(
    page_title="Al Fanateer Studio - Timecard & Payroll",
    page_icon="📷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for UI styling
st.markdown("""
    <style>
    .main-header {
        display: flex;
        align-items: center;
        gap: 20px;
        margin-bottom: 10px;
    }
    .title-container {
        display: flex;
        flex-direction: column;
    }
    .logo-text {
        font-size: 28px;
        font-weight: 800;
        color: #1E293B;
        margin: 0;
    }
    .tagline-text {
        font-size: 14px;
        font-weight: 500;
        color: #64748B;
        letter-spacing: 1px;
    }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 2. CONFIG & SESSION STATE INITIALIZATION
# ==========================================
APP_PASSWORD = "8443"
HOURLY_RATE = 10.0  # 10 SAR/hr

if "app_locked" not in st.session_state:
    st.session_state["app_locked"] = False

if "employees" not in st.session_state:
    st.session_state["employees"] = ["Remson", "Ali", "Ahmed"]

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
    """Calculates total working hours per day across Morning and Evening shifts."""
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
# 4. TOP HEADER (LOGO.png, TITLE & LOCK)
# ==========================================
col_logo, col_title, col_lock = st.columns([1.2, 4, 1])

with col_logo:
    # Explicitly check for LOGO.png (or fallbacks)
    logo_file = None
    for f in ["LOGO.png", "logo.png", "LOGO.JPG", "LOGO.jpg"]:
        if os.path.exists(f):
            logo_file = f
            break
            
    if logo_file:
        img = Image.open(logo_file)
        st.image(img, use_container_width=True)
    else:
        st.warning("⚠️ LOGO.png not found in repository root")

with col_title:
    st.markdown("""
        <div class="title-container">
            <span class="logo-text">AL FANATEER STUDIO</span>
            <span class="tagline-text">SINCE 1995 • COME ONCE STAY FOREVER</span>
        </div>
    """, unsafe_allow_html=True)

with col_lock:
    if not st.session_state["app_locked"]:
        if st.button("🔒 Lock App", use_container_width=True):
            st.session_state["app_locked"] = True
            st.rerun()

st.divider()


# ==========================================
# 5. PASSCODE LOCK & MAIN APP LOGIC
# ==========================================
if st.session_state["app_locked"]:
    st.subheader("🔒 App Locked")
    
    lock_col1, lock_col2 = st.columns([1, 2])
    with lock_col1:
        pwd_input = st.text_input("Enter Passcode to Unlock:", type="password", key="pwd_input")
        if st.button("Unlock App", type="primary"):
            if pwd_input == APP_PASSWORD:
                st.session_state["app_locked"] = False
                st.success("App unlocked successfully!")
                st.rerun()
            else:
                st.error("Incorrect passcode! Please try again.")

else:
    # Navigation Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Log Time", "📊 Payroll Calculation", "📝 Edit Logs & History", "⚙️ Manage Employees"])

    # --------------------------------------
    # TAB 1: LOG TIME
    # --------------------------------------
    with tab1:
        st.subheader("Log Shift / Attendance")
        
        emp = st.selectbox("Select Employee", st.session_state["employees"])
        date_selected = st.date_input("Select Date")
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            m_in = st.text_input("Morning Shift IN (HH:MM / OFF / ABSENT)", value="10:30")
        with col_m2:
            m_out = st.text_input("Morning Shift OUT (HH:MM / OFF / ABSENT)", value="13:00")

        col_e1, col_e2 = st.columns(2)
        with col_e1:
            e_in = st.text_input("Evening Shift IN (HH:MM / OFF / ABSENT)", value="19:00")
        with col_e2:
            e_out = st.text_input("Evening Shift OUT (HH:MM / OFF / ABSENT)", value="22:00")

        if st.button("Submit Shift Log", type="primary"):
            new_entry = {
                "Employee": emp,
                "Date": str(date_selected),
                "M. In": m_in,
                "M. Out": m_out,
                "E. In": e_in,
                "E. Out": e_out
            }
            st.session_state["logs"] = pd.concat([pd.DataFrame([new_entry]), st.session_state["logs"]], ignore_index=True)
            st.success(f"Log saved successfully for {emp}!")

    # --------------------------------------
    # TAB 2: PAYROLL CALCULATION
    # --------------------------------------
    with tab2:
        st.subheader("Payroll Calculations (Rate: 10 SAR/hr)")
        
        df_logs = st.session_state["logs"].copy()
        if not df_logs.empty:
            df_logs["Hours"] = df_logs.apply(calculate_row_hours, axis=1)
            
            payroll_df = df_logs.groupby("Employee")["Hours"].sum().reset_index()
            payroll_df["Total SAR"] = payroll_df["Hours"] * HOURLY_RATE
            
            st.dataframe(payroll_df, use_container_width=True)
        else:
            st.info("No data available for calculation.")

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
                # 1. SEQUENTIAL SERIAL NUMBERS (Start clean at 1, 2, 3...)
                df_filtered = df_filtered.drop(columns=["ID"], errors="ignore")
                df_display = df_filtered.reset_index(drop=True)
                df_display.index = df_display.index + 1  # 1-based index

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

    # --------------------------------------
    # TAB 4: MANAGE EMPLOYEES
    # --------------------------------------
    with tab4:
        st.subheader("Manage Employee Roster")
        new_emp = st.text_input("Add New Employee Name:")
        if st.button("Add Employee"):
            if new_emp and new_emp not in st.session_state["employees"]:
                st.session_state["employees"].append(new_emp)
                st.success(f"Added {new_emp} to employee list.")
                st.rerun()

        st.write("Current Employees:", st.session_state["employees"])
