import streamlit as st
import pandas as pd
import sqlite3
import time
from datetime import datetime, date, timedelta

# --- Configuration Constants ---
ADMIN_PASSWORD = "8443"
AUTO_LOCK_SECONDS = 600  # 10 minutes (10 * 60 seconds)

# --- Page Configuration ---
st.set_page_config(
    page_title="Al Fanateer Studio - Timecard & Payroll", 
    page_icon="📷",
    layout="wide"
)

# --- Header Section with Logo ---
col_logo, col_title, col_lock = st.columns([1.2, 4, 1])

with col_logo:
    try:
        st.image("LOGO.png", width=120)
    except Exception:
        st.write("📷")

with col_title:
    st.markdown("""
        <div style='display: flex; flex-direction: column;'>
            <span style='font-size: 26px; font-weight: 800; color: #1E293B;'>AL FANATEER STUDIO</span>
            <span style='font-size: 13px; font-weight: 500; color: #64748B; letter-spacing: 1px;'>SINCE 1995 • COME ONCE STAY FOREVER</span>
        </div>
    """, unsafe_allow_html=True)

# --- Screen Lock & Inactivity Timer Setup ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if "last_activity" not in st.session_state:
    st.session_state["last_activity"] = time.time()

# 10-Minute Auto-Lock Check
if st.session_state["authenticated"]:
    elapsed_time = time.time() - st.session_state["last_activity"]
    if elapsed_time > AUTO_LOCK_SECONDS:
        st.session_state["authenticated"] = False
        st.toast("⚠️ App locked due to 10 minutes of inactivity.", icon="🔒")
    else:
        st.session_state["last_activity"] = time.time()

with col_lock:
    if st.session_state["authenticated"]:
        if st.button("🔒 Lock App", use_container_width=True):
            st.session_state["authenticated"] = False
            st.rerun()

st.markdown("---")

# Prompt for Password if App is Locked
if not st.session_state["authenticated"]:
    st.subheader("🔒 App Locked")
    st.info("Please enter the password to access the app.")
    
    with st.form("login_form"):
        pwd_input = st.text_input("Enter Password", type="password")
        login_btn = st.form_submit_button("Unlock App")
        
        if login_btn:
            if pwd_input == ADMIN_PASSWORD:
                st.session_state["authenticated"] = True
                st.session_state["last_activity"] = time.time()
                st.success("Access Granted!")
                st.rerun()
            else:
                st.error("Incorrect password!")
                
    st.stop()

# --- Database Setup (SQLite) ---
conn = sqlite3.connect("timesheets.db", check_same_thread=False)
c = conn.cursor()

# Table for Employee Names
c.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
''')

# Table for Timecard Entries
c.execute('''
    CREATE TABLE IF NOT EXISTS timecards_v3 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee TEXT,
        work_date TEXT,
        m_in TEXT,
        m_out TEXT,
        e_in TEXT,
        e_out TEXT,
        total_hours REAL
    )
''')
conn.commit()

# Seed default employees if empty
DEFAULT_EMPLOYEES = ["Remson", "Shadab", "Manzoor", "Arial"]
for emp in DEFAULT_EMPLOYEES:
    c.execute("INSERT OR IGNORE INTO employees (name) VALUES (?)", (emp,))
conn.commit()

def get_employee_list():
    df_emp = pd.read_sql_query("SELECT name FROM employees ORDER BY name ASC", conn)
    return df_emp["name"].tolist()

# --- Auto Cleanup: Delete records older than 90 days ---
three_months_ago = (date.today() - timedelta(days=90)).strftime("%Y-%m-%d")
c.execute("DELETE FROM timecards_v3 WHERE work_date < ?", (three_months_ago,))
conn.commit()

def calc_shift_hours(t_in, t_out, active):
    if not active:
        return 0.0
    dt_in = datetime.combine(date.today(), t_in)
    dt_out = datetime.combine(date.today(), t_out)
    if dt_out <= dt_in:
        dt_out += timedelta(days=1)
    return (dt_out - dt_in).total_seconds() / 3600.0

def parse_time_str(time_val):
    """Attempts to parse string time inputs into datetime objects."""
    s = str(time_val).strip().upper()
    if s in ['OFF', 'ABSENT', 'NONE', '', 'NAN']:
        return None
    for fmt in ['%H:%M', '%I:%M %p', '%H:%M:%S', '%I:%M:%S %p']:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None

def calculate_row_hours(row):
    """Dynamically calculates total daily working hours (as decimal) for a row."""
    total = 0.0
    
    # Morning Shift calculation
    m_in_dt = parse_time_str(row.get('m_in'))
    m_out_dt = parse_time_str(row.get('m_out'))
    if m_in_dt and m_out_dt:
        diff = (m_out_dt - m_in_dt).total_seconds() / 3600.0
        if diff < 0:
            diff += 24.0  # Handle midnight rollover
        total += diff

    # Evening Shift calculation
    e_in_dt = parse_time_str(row.get('e_in'))
    e_out_dt = parse_time_str(row.get('e_out'))
    if e_in_dt and e_out_dt:
        diff = (e_out_dt - e_in_dt).total_seconds() / 3600.0
        if diff < 0:
            diff += 24.0  # Handle midnight rollover
        total += diff

    return round(total, 2)

def format_hours_to_hhmm(decimal_hours):
    """Converts decimal hours (e.g. 1.50, 1.75) into HH:MM format (e.g. 1:30, 1:45)."""
    try:
        val = float(decimal_hours)
        total_minutes = int(round(val * 60))
        hours = total_minutes // 60
        minutes = total_minutes % 60
        return f"{hours}:{minutes:02d}"
    except (ValueError, TypeError):
        return "0:00"

# --- Tab Navigation ---
tab1, tab2, tab3 = st.tabs(["➕ Log Time", "📊 Payroll Calculation", "📜 Edit Logs & History"])

# ---------------------------------------------------------
# TAB 1: Daily Log Entry
# ---------------------------------------------------------
with tab1:
    st.subheader("Clock In / Out Entry")
    
    current_employees = get_employee_list()
    
    with st.form("time_entry_form", clear_on_submit=True):
        emp_name = st.selectbox("Select Employee", current_employees)
        entry_date = st.date_input("Date", value=date.today())
        
        st.markdown("---")
        
        # Quick Full-Day Overrides
        st.markdown("**⚡ Full Day Overrides (Optional)**")
        status_col1, status_col2 = st.columns(2)
        with status_col1:
            is_full_day_off = st.checkbox("🌴 Entire Day OFF")
        with status_col2:
            is_full_day_absent = st.checkbox("❌ Entire Day ABSENT")
        
        st.markdown("---")
        
        # Morning Shift Section
        st.markdown("**🌅 Morning Shift**")
        m_status = st.selectbox(
            "Morning Shift Status",
            ["Worked", "Shift Off", "Absent"],
            disabled=(is_full_day_off or is_full_day_absent)
        )
        
        col_m_in, col_m_out = st.columns(2)
        with col_m_in:
            m_in = st.time_input("Morning In", value=datetime.strptime("09:00", "%H:%M").time(), disabled=(is_full_day_off or is_full_day_absent or m_status != "Worked"))
        with col_m_out:
            m_out = st.time_input("Morning Out", value=datetime.strptime("13:00", "%H:%M").time(), disabled=(is_full_day_off or is_full_day_absent or m_status != "Worked"))
            
        st.markdown("---")
        
        # Evening Shift Section
        st.markdown("**🌙 Evening Shift**")
        e_status = st.selectbox(
            "Evening Shift Status",
            ["Worked", "Shift Off", "Absent"],
            disabled=(is_full_day_off or is_full_day_absent)
        )
        
        col_e_in, col_e_out = st.columns(2)
        with col_e_in:
            e_in = st.time_input("Evening In", value=datetime.strptime("16:00", "%H:%M").time(), disabled=(is_full_day_off or is_full_day_absent or e_status != "Worked"))
        with col_e_out:
            e_out = st.time_input("Evening Out", value=datetime.strptime("22:00", "%H:%M").time(), disabled=(is_full_day_off or is_full_day_absent or e_status != "Worked"))
            
        st.markdown("---")
        submit_btn = st.form_submit_button("Save Timecard Entry")
        
        if submit_btn:
            if is_full_day_absent:
                c.execute('''
                    INSERT INTO timecards_v3 (employee, work_date, m_in, m_out, e_in, e_out, total_hours)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (emp_name, entry_date.strftime("%Y-%m-%d"), "ABSENT", "ABSENT", "ABSENT", "ABSENT", 0.0))
                conn.commit()
                st.error(f"Logged Full Day ABSENT for {emp_name} on {entry_date}.")
            elif is_full_day_off:
                c.execute('''
                    INSERT INTO timecards_v3 (employee, work_date, m_in, m_out, e_in, e_out, total_hours)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (emp_name, entry_date.strftime("%Y-%m-%d"), "OFF", "OFF", "OFF", "OFF", 0.0))
                conn.commit()
                st.success(f"Logged Full Day OFF for {emp_name} on {entry_date}!")
            else:
                # Process Morning Shift values
                if m_status == "Worked":
                    m_hrs = calc_shift_hours(m_in, m_out, True)
                    m_in_str = m_in.strftime("%H:%M")
                    m_out_str = m_out.strftime("%H:%M")
                elif m_status == "Shift Off":
                    m_hrs = 0.0
                    m_in_str = "OFF"
                    m_out_str = "OFF"
                else:  # Absent
                    m_hrs = 0.0
                    m_in_str = "ABSENT"
                    m_out_str = "ABSENT"

                # Process Evening Shift values
                if e_status == "Worked":
                    e_hrs = calc_shift_hours(e_in, e_out, True)
                    e_in_str = e_in.strftime("%H:%M")
                    e_out_str = e_out.strftime("%H:%M")
                elif e_status == "Shift Off":
                    e_hrs = 0.0
                    e_in_str = "OFF"
                    e_out_str = "OFF"
                else:  # Absent
                    e_hrs = 0.0
                    e_in_str = "ABSENT"
                    e_out_str = "ABSENT"

                tot_hrs = round(m_hrs + e_hrs, 2)

                c.execute('''
                    INSERT INTO timecards_v3 (employee, work_date, m_in, m_out, e_in, e_out, total_hours)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (emp_name, entry_date.strftime("%Y-%m-%d"), m_in_str, m_out_str, e_in_str, e_out_str, tot_hrs))
                conn.commit()
                st.success(f"Logged entry for {emp_name} on {entry_date} ({format_hours_to_hhmm(tot_hrs)} hrs worked).")

    st.markdown("---")
    
    with st.expander("👤 Manage / Add New Employee"):
        new_emp_name = st.text_input("New Employee Name", placeholder="e.g. John")
        if st.button("Save New Employee"):
            if not new_emp_name.strip():
                st.error("Please enter a valid name.")
            else:
                try:
                    c.execute("INSERT INTO employees (name) VALUES (?)", (new_emp_name.strip(),))
                    conn.commit()
                    st.success(f"Added {new_emp_name.strip()} to employee list!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.warning("This employee already exists!")

# ---------------------------------------------------------
# TAB 2: Payroll Calculation
# ---------------------------------------------------------
with tab2:
    st.subheader("💵 Payroll Calculation")
    
    # Filters Section
    col_filter_emp, col_filter_rate = st.columns([2, 1])
    
    all_employees_payroll = ["All Employees"] + get_employee_list()
    with col_filter_emp:
        selected_payroll_emp = st.selectbox("🔍 Filter by Employee Name", all_employees_payroll, key="payroll_emp_select")
        
    with col_filter_rate:
        hourly_rate_input = st.number_input("Hourly Rate (SAR)", value=10.0, step=0.5, min_value=0.0, format="%.2f")

    # Date Range Selection
    period_option = st.radio(
        "Select Calculation Period:",
        ["Last 30 Days (1 Month)", "Last 90 Days (3 Months)", "Custom Date Range"],
        horizontal=True
    )
    
    today = date.today()
    if period_option == "Last 30 Days (1 Month)":
        start_date = today - timedelta(days=30)
        end_date = today
    elif period_option == "Last 90 Days (3 Months)":
        start_date = today - timedelta(days=90)
        end_date = today
    else:
        c_col1, c_col2 = st.columns(2)
        with c_col1:
            start_date = st.date_input("Start Date", value=today - timedelta(days=30))
        with c_col2:
            end_date = st.date_input("End Date", value=today)

    # Query total hours logged from history
    if selected_payroll_emp == "All Employees":
        df = pd.read_sql_query("SELECT employee, work_date, total_hours FROM timecards_v3", conn)
    else:
        df = pd.read_sql_query(
            "SELECT employee, work_date, total_hours FROM timecards_v3 WHERE employee = ?", 
            conn, 
            params=(selected_payroll_emp,)
        )
    
    if not df.empty:
        df["work_date"] = pd.to_datetime(df["work_date"]).dt.date
        filtered_df = df[(df["work_date"] >= start_date) & (df["work_date"] <= end_date)]
        
        if not filtered_df.empty:
            summary_df = filtered_df.groupby("employee").agg(
                Total_Hours=("total_hours", "sum")
            ).reset_index()
            
            summary_df["Formatted_Hours"] = summary_df["Total_Hours"].apply(format_hours_to_hhmm)
            summary_df["Hourly_Rate"] = hourly_rate_input
            summary_df["Total_Pay"] = summary_df["Total_Hours"] * hourly_rate_input
            
            st.markdown("---")
            st.caption(f"Pulled hours history from **{start_date}** to **{end_date}**")
            
            m1, m2 = st.columns(2)
            with m1:
                st.metric("Total Hours Logged", f"{format_hours_to_hhmm(summary_df['Total_Hours'].sum())} hrs")
            with m2:
                st.metric("Total Payroll Amount", f"SAR {summary_df['Total_Pay'].sum():,.2f}")
                
            st.markdown("### 📋 Final Payout Breakdown")
            st.dataframe(
                summary_df,
                column_config={
                    "employee": "Employee Name",
                    "Formatted_Hours": "Total Hours (HH:MM)",
                    "Hourly_Rate": st.column_config.NumberColumn("Rate (SAR)", format="SAR %.2f"),
                    "Total_Pay": st.column_config.NumberColumn("Total Salary (SAR)", format="SAR %.2f")
                },
                column_order=["employee", "Formatted_Hours", "Hourly_Rate", "Total_Pay"],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning(f"No history entries found between {start_date} and {end_date} for {selected_payroll_emp}.")
    else:
        st.info("No history logs found in database.")

# ---------------------------------------------------------
# TAB 3: History & Manual Edits
# ---------------------------------------------------------
with tab3:
    st.subheader("3-Month Shift Log & Manual Edits")
    
    # Employee Filter
    all_employees = ["All Employees"] + get_employee_list()
    selected_emp = st.selectbox("🔍 Filter by Employee Name", all_employees, key="history_emp_select")
    
    # Fetch Data sorted by date ASCENDING
    if selected_emp == "All Employees":
        df_raw = pd.read_sql_query("SELECT * FROM timecards_v3 ORDER BY work_date ASC", conn)
    else:
        df_raw = pd.read_sql_query(
            "SELECT * FROM timecards_v3 WHERE employee = ? ORDER BY work_date ASC", 
            conn, 
            params=(selected_emp,)
        )
    
    if not df_raw.empty:
        df_display = df_raw.copy()
        
        # 1. MAKE ID CONTINUOUS & SEQUENTIAL (1, 2, 3...)
        df_display["id"] = range(1, len(df_display) + 1)
        
        # 2. DYNAMICALLY CALCULATE HOURS (NUMERIC) AND FORMAT AS HH:MM FOR DISPLAY
        numeric_hours = df_display.apply(calculate_row_hours, axis=1)
        df_display["total_hours_num"] = numeric_hours
        df_display["total_hours"] = numeric_hours.apply(format_hours_to_hhmm)
        
        # Reorder columns explicitly including the total_hours column
        cols = ["id", "employee", "work_date", "m_in", "m_out", "e_in", "e_out", "total_hours"]
        df_display = df_display[cols]

        # Calculate Grand Total across all rows
        total_hours_sum = numeric_hours.sum()

        # Display Editable Data Table
        edited_df = st.data_editor(
            df_display,
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "employee": "Employee",
                "work_date": "Date",
                "m_in": "M. In",
                "m_out": "M. Out",
                "e_in": "E. In",
                "e_out": "E. Out",
                "total_hours": st.column_config.TextColumn("Total Hours Worked", disabled=True)
            },
            num_rows="dynamic",
            key="timecard_editor",
            use_container_width=True,
            hide_index=True
        )
        
        st.write("")
        
        # 3. SAVE BUTTON AND ACCURATE TOTAL HOURS METRIC (HH:MM FORMAT) AT BOTTOM RIGHT
        col_save, col_total = st.columns([3, 1])
        
        with col_save:
            if st.button("Save Changes to Database", type="primary"):
                # Recalculate decimal hours row-by-row before inserting into database
                edited_df["total_hours_num"] = edited_df.apply(calculate_row_hours, axis=1)
                
                if selected_emp == "All Employees":
                    c.execute("DELETE FROM timecards_v3")
                    for _, row in edited_df.iterrows():
                        c.execute('''
                            INSERT INTO timecards_v3 (employee, work_date, m_in, m_out, e_in, e_out, total_hours)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (row['employee'], row['work_date'], row['m_in'], row['m_out'], row['e_in'], row['e_out'], row['total_hours_num']))
                else:
                    c.execute("DELETE FROM timecards_v3 WHERE employee = ?", (selected_emp,))
                    for _, row in edited_df.iterrows():
                        c.execute('''
                            INSERT INTO timecards_v3 (employee, work_date, m_in, m_out, e_in, e_out, total_hours)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (row['employee'], row['work_date'], row['m_in'], row['m_out'], row['e_in'], row['e_out'], row['total_hours_num']))
                
                conn.commit()
                st.success("Database updated successfully!")
                st.rerun()

        with col_total:
            st.metric(label="TOTAL HOURS", value=f"{format_hours_to_hhmm(total_hours_sum)} hrs")

    else:
        st.info(f"No records found for {selected_emp}.")
