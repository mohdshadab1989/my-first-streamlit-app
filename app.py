import sqlite3
import time
from datetime import datetime
import pandas as pd
import streamlit as st

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Al Fanateer Studio Timecard & Payroll",
    page_icon="🕒",
    layout="wide",
)

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("timesheets.db", check_same_thread=False)
    cursor = conn.cursor()

    # Create employees table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """
    )

    # Create timecards table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS timecards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            employee TEXT NOT NULL,
            shift_type TEXT NOT NULL,
            hours REAL NOT NULL,
            status TEXT NOT NULL
        )
    """
    )

    # Insert default employees if table is empty
    cursor.execute("SELECT COUNT(*) FROM employees")
    if cursor.fetchone()[0] == 0:
        default_employees = ["Remson", "Shadab", "Manzoor", "Arial"]
        for emp in default_employees:
            cursor.execute(
                "INSERT OR IGNORE INTO employees (name) VALUES (?)", (emp,)
            )

    conn.commit()
    conn.close()


init_db()

# --- SECURITY & AUTO-LOCK SETUP ---
ADMIN_PIN = "8443"
LOCK_TIMEOUT = 600  # 10 minutes in seconds

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "last_activity" not in st.session_state:
    st.session_state.last_activity = time.time()

# Check inactivity timeout
if st.session_state.authenticated:
    if time.time() - st.session_state.last_activity > LOCK_TIMEOUT:
        st.session_state.authenticated = False
        st.warning("Session locked due to 10 minutes of inactivity.")
    else:
        st.session_state.last_activity = time.time()

# --- LOCKSCREEN UI ---
if not st.session_state.authenticated:
    st.markdown(
        "<h2 style='text-align: center;'>🔒 Al Fanateer Studio - Secure Access</h2>",
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        entered_pin = st.text_input(
            "Enter Admin Passcode", type="password", key="pin_input"
        )
        if st.button("Unlock App", use_container_width=True):
            if entered_pin == ADMIN_PIN:
                st.session_state.authenticated = True
                st.session_state.last_activity = time.time()
                st.rerun()
            else:
                st.error("Incorrect Passcode. Please try again.")
    st.stop()

# --- MAIN APP UI ---
st.title("🌟 Al Fanateer Studio - Timecard & Payroll System")
st.markdown("---")

# Sidebar navigation and controls
st.sidebar.header("Navigation & Security")
if st.sidebar.button("🔒 Lock App Now"):
    st.session_state.authenticated = False
    st.rerun()

app_mode = st.sidebar.radio(
    "Choose Action",
    [
        "📝 Log Timecard",
        "📜 Edit Logs & History",
        "💰 Payroll Calculation",
        "👥 Manage Employees",
        "📤 Backup & Restore",
    ],
)

# Fetch current employee list
def get_employees():
    conn = sqlite3.connect("timesheets.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM employees ORDER BY name")
    emps = [row[0] for row in cursor.fetchall()]
    conn.close()
    return emps


# --- 1. LOG TIMECARD TAB ---
if app_mode == "📝 Log Timecard":
    st.subheader("📝 Record Employee Shift")

    employees = get_employees()
    if not employees:
        st.warning(
            "No employees found. Please add employees in the 'Manage Employees' tab."
        )
    else:
        with st.form("timecard_form"):
            selected_date = st.date_input("Date", value=datetime.today())
            selected_employee = st.selectbox("Employee Name", options=employees)

            col1, col2 = st.columns(2)
            with col1:
                shift_type = st.selectbox(
                    "Shift Type", ["Morning", "Evening", "Full Day"]
                )
            with col2:
                status = st.selectbox(
                    "Attendance Status", ["Present", "OFF", "Absent"]
                )

            # Hours logic
            if status == "Present":
                default_hrs = 8.0 if shift_type == "Full Day" else 4.0
                hours = st.number_input(
                    "Hours Worked",
                    min_value=0.5,
                    max_value=24.0,
                    value=default_hrs,
                    step=0.5,
                )
            else:
                hours = 0.0
                st.info(
                    f"Status is set to {status}, hours automatically recorded as 0."
                )

            submitted = st.form_submit_button("Save Timecard Entry")
            if submitted:
                conn = sqlite3.connect("timesheets.db", check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO timecards (date, employee, shift_type, hours, status)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        str(selected_date),
                        selected_employee,
                        shift_type,
                        hours,
                        status,
                    ),
                )
                conn.commit()
                conn.close()
                st.success(
                    f"Successfully logged timecard for {selected_employee}!"
                )

# --- 2. EDIT LOGS & HISTORY TAB ---
elif app_mode == "📜 Edit Logs & History":
    st.subheader("📜 Edit Logs & History")

    conn = sqlite3.connect("timesheets.db", check_same_thread=False)
    df_history = pd.read_sql(
        "SELECT id, date, employee, shift_type, hours, status FROM timecards ORDER BY date DESC, id DESC",
        conn,
    )
    conn.close()

    if df_history.empty:
        st.info("No timecard records found yet.")
    else:
        st.write(
            "You can directly edit the details below or select a record to delete."
        )

        edited_df = st.data_editor(
            df_history,
            num_rows="dynamic",
            key="timecard_editor",
            use_container_width=True,
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("💾 Save Table Changes"):
                try:
                    conn = sqlite3.connect(
                        "timesheets.db", check_same_thread=False
                    )
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM timecards")
                    for index, row in edited_df.iterrows():
                        cursor.execute(
                            """
                            INSERT INTO timecards (id, date, employee, shift_type, hours, status)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """,
                            (
                                row["id"],
                                row["date"],
                                row["employee"],
                                row["shift_type"],
                                row["hours"],
                                row["status"],
                            ),
                        )
                    conn.commit()
                    conn.close()
                    st.success(
                        "Changes successfully saved to the database! Refreshing..."
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving changes: {e}")

        with col2:
            record_to_delete = st.selectbox(
                "Select Record ID to Delete",
                options=[None] + list(df_history["id"]),
            )
            if record_to_delete and st.button("🗑️ Delete Selected Record"):
                conn = sqlite3.connect("timesheets.db", check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM timecards WHERE id = ?", (record_to_delete,)
                )
                conn.commit()
                conn.close()
                st.success(f"Record ID {record_to_delete} deleted successfully!")
                st.rerun()

# --- 3. PAYROLL CALCULATION TAB ---
elif app_mode == "💰 Payroll Calculation":
    st.subheader("💰 Payroll Summary (SAR)")

    conn = sqlite3.connect("timesheets.db", check_same_thread=False)
    df_all = pd.read_sql("SELECT * FROM timecards", conn)
    conn.close()

    if df_all.empty:
        st.info("No records available to calculate payroll.")
    else:
        hourly_rate = st.number_input(
            "Hourly Rate (SAR)", min_value=1.0, value=10.0, step=1.0
        )

        summary_df = (
            df_all.groupby("employee")
            .agg(
                Total_Hours=("hours", "sum"),
                Days_Present=(
                    "status",
                    lambda x: (x == "Present").sum(),
                ),
            )
            .reset_index()
        )

        summary_df["Total Salary (SAR)"] = (
            summary_df["Total_Hours"] * hourly_rate
        )

        st.dataframe(summary_df, use_container_width=True)

# --- 4. MANAGE EMPLOYEES TAB ---
elif app_mode == "👥 Manage Employees":
    st.subheader("👥 Employee Roster Management")

    employees = get_employees()

    col1, col2 = st.columns(2)
    with col1:
        st.write("Current Employees:")
        for emp in employees:
            st.text(f"• {emp}")

    with col2:
        new_emp = st.text_input("Add New Employee Name")
        if st.button("Add Employee"):
            if new_emp.strip():
                try:
                    conn = sqlite3.connect(
                        "timesheets.db", check_same_thread=False
                    )
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO employees (name) VALUES (?)",
                        (new_emp.strip(),),
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"Added employee: {new_emp.strip()}")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Employee already exists.")
            else:
                st.warning("Please enter a valid name.")

# --- 5. BACKUP & RESTORE TAB ---
elif app_mode == "📤 Backup & Restore":
    st.subheader("📤 Database Backup & Restore")

    # Download backup
    with open("timesheets.db", "rb") as f:
        st.download_button(
            label="📥 Download Database Backup (timesheets.db)",
            data=f,
            file_name="timesheets.db",
            mime="application/octet-stream",
        )

    st.markdown("---")

    # Restore backup
    uploaded_file = st.file_uploader(
        "Upload Database Backup to Restore", type=["db"]
    )
    if uploaded_file is not None:
        if st.button("⚠️ Confirm and Restore Database"):
            with open("timesheets.db", "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("Database restored successfully! Please refresh the app.")
            st.rerun()
