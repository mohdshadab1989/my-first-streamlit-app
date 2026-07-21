import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta

# --- Page Configuration ---
st.set_page_config(
    page_title="Al Fanateer Studio - Timecard & Payroll", 
    page_icon="📷",
    layout="centered"
)

# --- Admin Password Configuration ---
ADMIN_PASSWORD = "8443"  # <--- Updated Password!

# --- Header Section with Logo ---
st.title("📷 AL FANATEER STUDIO")
st.caption("SINCE 1995 • 'COME ONCE STAY FOREVER'")

# Display logo if uploaded
try:
    st.image("LOGO.png", width=140)
except Exception:
    pass

st.markdown("---")

# --- Screen Lock Check ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.subheader("🔒 App Locked")
    st.info("Please enter the password to access the app.")
    
    with st.form("login_form"):
        pwd_input = st.text_input("Enter Password", type="password")
        login_btn = st.form_submit_button("Unlock App")
        
        if login_btn:
            if pwd_input == ADMIN_PASSWORD:
                st.session_state["authenticated"] = True
                st.success("Access Granted!")
                st.rerun()
            else:
                st.error("Incorrect password!")
                
    st.stop()  # Stops the rest of the script from loading until unlocked

# --- Logout Button (Top Right / Header) ---
col_head, col_logout = st.columns([3, 1])
with col_logout:
    if st.button("🔒 Lock App"):
        st.session_state["authenticated"] = False
        st.rerun()

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
    CREATE TABLE IF NOT EXISTS timecards_v2 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee TEXT,
        hourly_rate REAL,
        work_date TEXT,
        m_in TEXT,
        m_out TEXT,
        e_in TEXT,
        e_out TEXT,
        total_hours REAL
    )
''')
conn.commit()

# Seed default employees if table is empty
DEFAULT_EMPLOYEES = ["Remson", "Shadab", "Manzoor", "Arial"]
for emp in DEFAULT_EMPLOYEES:
    c.execute("INSERT OR IGNORE INTO employees (name) VALUES (?)", (emp,))
conn.commit()

# Function to get active employee list from DB
def get_employee_list():
    df_emp = pd.read_sql_query("SELECT name FROM employees ORDER BY name ASC", conn)
    return df_emp["name"].tolist()

# --- Auto Cleanup: Delete records older than 90 days ---
three_months_ago = (date.today() - timedelta(days=90)).strftime("%Y-%m-%d")
c.execute("DELETE FROM timecards_v2 WHERE work_date < ?", (three_months_ago,))
conn.commit()

# Helper function to calculate shift duration in hours
def calc_shift_hours(t_in, t_out, active):
    if not active:
        return 0.0
    dt_in = datetime.combine(date.today(), t_in)
    dt_out = datetime.combine(date.today(), t_out)
    if dt_out <= dt_in:
        dt_out += timedelta(days=1)
    return (dt_out - dt_in).total_seconds() / 3600.0

# --- Tab Navigation ---
tab1, tab2, tab3 = st.tabs(["➕ Log / Edit Time", "📊 Payroll Summary", "📜 Edit Logs & History"])

# ---------------------------------------------------------
# TAB 1: Log Entry & Add Employee
# ---------------------------------------------------------
with tab1:
    st.subheader("Clock In / Out Entry")
    
    current_employees = get_employee_list()
    
    with st.form("time_entry_form", clear_on_submit=True):
        # Dropdown selection for employee name
        emp_name = st.selectbox("Select Employee", current_employees)
        hourly_rate = st.number_input("Hourly Rate (SAR)", min_value=0.0, value=25.0, step=0.50)
        entry_date = st.date_input("Date", value=date.today())
        
        st.markdown("---")
        
        # Morning Shift Section
        st.markdown("**🌅 Morning Shift**")
        has_morning = st.checkbox("Worked Morning Shift?", value=True)
        col_m_in, col_m_out = st.columns(2)
        with col_m_in:
            m_in = st.time_input("Morning In", value=datetime.strptime("09:00", "%H:%M").time())
        with col_m_out:
            m_out = st.time_input("Morning Out", value=datetime.strptime("13:00", "%H:%M").time())
            
        st.markdown("---")
        
        # Evening Shift Section
        st.markdown("**🌙 Evening Shift**")
        has_evening = st.checkbox("Worked Evening Shift?", value=True)
        col_e_in, col_e_out = st.columns(2)
        with col_e_in:
            e_in = st.time_input("Evening In", value=datetime.strptime("16:00", "%H:%M").time())
        with col_e_out:
            e_out = st.time_input("Evening Out", value=datetime.strptime("22:00", "%H:%M").time())
            
        st.markdown("---")
        submit_btn = st.form_submit_button("Save Timecard Entry")
        
        if submit_btn:
            if not has_morning and not has_evening:
                st.error("Please select at least one active shift (Morning or Evening).")
            else:
                m_hrs = calc_shift_hours(m_in, m_out, has_morning)
                e_hrs = calc_shift_hours(e_in, e_out, has_evening)
                tot_hrs = round(m_hrs + e_hrs, 2)
                
                m_in_str = m_in.strftime("%H:%M") if has_morning else "--"
                m_out_str = m_out.strftime("%H:%M") if has_morning else "--"
                e_in_str = e_in.strftime("%H:%M") if has_evening else "--"
                e_out_str = e_out.strftime("%H:%M") if has_evening else "--"
                
                c.execute('''
                    INSERT INTO timecards_v2 (employee, hourly_rate, work_date, m_in, m_out, e_in, e_out, total_hours)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (emp_name, hourly_rate, entry_date.strftime("%Y-%m-%d"), m_in_str, m_out_str, e_in_str, e_out_str, tot_hrs))
                conn.commit()
                st.success(f"Logged {tot_hrs:.2f} total hours for {emp_name} on {entry_date}!")

    st.markdown("---")
    
    # --- Add New Employee Section ---
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
# TAB 2: Payroll Summary
# ---------------------------------------------------------
with tab2:
    st.subheader("Salary & Hours Summary")
    
    df = pd.read_sql_query("SELECT * FROM timecards_v2", conn)
    
    if not df.empty:
        df["Total Salary (SAR)"] = df["total_hours"] * df["hourly_rate"]

        summary_df = df.groupby("employee").agg(
            Total_Hours=("total_hours", "sum"),
            Hourly_Rate=("hourly_rate", "first"),
            Total_Salary=("Total Salary (SAR)", "sum")
        ).reset_index()
        
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Total Hours (All Staff)", f"{summary_df['Total_Hours'].sum():.2f} hrs")
        with c2:
            st.metric("Total Payroll", f"SAR {summary_df['Total_Salary'].sum():,.2f}")
            
        st.markdown("---")
        st.dataframe(
            summary_df,
            column_config={
                "employee": "Employee",
                "Total_Hours": st.column_config.NumberColumn("Total Hours", format="%.2f hrs"),
                "Hourly_Rate": st.column_config.NumberColumn("Rate (SAR)", format="SAR %.2f"),
                "Total_Salary": st.column_config.NumberColumn("Total Pay (SAR)", format="SAR %.2f")
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No logs found. Add shift entries in the first tab!")

# ---------------------------------------------------------
# TAB 3: History & Manual Edits
# ---------------------------------------------------------
with tab3:
    st.subheader("3-Month Shift Log & Manual Edits")
    
    df_raw = pd.read_sql_query("SELECT * FROM timecards_v2 ORDER BY work_date DESC", conn)
    
    if not df_raw.empty:
        edited_df = st.data_editor(
            df_raw,
            column_config={
                "id": "ID",
                "employee": "Employee",
                "hourly_rate": "Rate (SAR)",
                "work_date": "Date",
                "m_in": "M. In",
                "m_out": "M. Out",
                "e_in": "E. In",
                "e_out": "E. Out",
                "total_hours": st.column_config.NumberColumn("Total Hours", format="%.2f hrs")
            },
            num_rows="dynamic",
            key="timecard_editor",
            use_container_width=True
        )
        
        if st.button("Save Changes to Database"):
            c.execute("DELETE FROM timecards_v2")
            for _, row in edited_df.iterrows():
                c.execute('''
                    INSERT INTO timecards_v2 (id, employee, hourly_rate, work_date, m_in, m_out, e_in, e_out, total_hours)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (row['id'], row['employee'], row['hourly_rate'], row['work_date'], row['m_in'], row['m_out'], row['e_in'], row['e_out'], row['total_hours']))
            conn.commit()
            st.success("Database updated successfully!")
            st.rerun()
    else:
        st.info("No records to display.")
