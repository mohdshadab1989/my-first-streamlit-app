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
ADMIN_PASSWORD = "8443"

# --- Header Section with Logo ---
st.title("📷 AL FANATEER STUDIO")
st.caption("SINCE 1995 • 'COME ONCE STAY FOREVER'")

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
                
    st.stop()

# --- Logout Button ---
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
        
        # Day Off Checkbox Option
        is_day_off = st.checkbox("🌴 Mark as Day Off (Weekly Off)")
        
        st.markdown("---")
        
        # Morning Shift
        st.markdown("**🌅 Morning Shift**")
        has_morning = st.checkbox("Worked Morning Shift?", value=True, disabled=is_day_off)
        col_m_in, col_m_out = st.columns(2)
        with col_m_in:
            m_in = st.time_input("Morning In", value=datetime.strptime("09:00", "%H:%M").time(), disabled=is_day_off)
        with col_m_out:
            m_out = st.time_input("Morning Out", value=datetime.strptime("13:00", "%H:%M").time(), disabled=is_day_off)
            
        st.markdown("---")
        
        # Evening Shift
        st.markdown("**🌙 Evening Shift**")
        has_evening = st.checkbox("Worked Evening Shift?", value=True, disabled=is_day_off)
        col_e_in, col_e_out = st.columns(2)
        with col_e_in:
            e_in = st.time_input("Evening In", value=datetime.strptime("16:00", "%H:%M").time(), disabled=is_day_off)
        with col_e_out:
            e_out = st.time_input("Evening Out", value=datetime.strptime("22:00", "%H:%M").time(), disabled=is_day_off)
            
        st.markdown("---")
        submit_btn = st.form_submit_button("Save Timecard Entry")
        
        if submit_btn:
            if is_day_off:
                # Store "OFF" for shift times and 0 total hours
                c.execute('''
                    INSERT INTO timecards_v3 (employee, work_date, m_in, m_out, e_in, e_out, total_hours)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (emp_name, entry_date.strftime("%Y-%m-%d"), "OFF", "OFF", "OFF", "OFF", 0.0))
                conn.commit()
                st.success(f"Logged Day Off for {emp_name} on {entry_date}!")
            else:
                if not has_morning and not has_evening:
                    st.error("Please select at least one active shift or check 'Mark as Day Off'.")
                else:
                    m_hrs = calc_shift_hours(m_in, m_out, has_morning)
                    e_hrs = calc_shift_hours(e_in, e_out, has_evening)
                    tot_hrs = round(m_hrs + e_hrs, 2)
                    
                    m_in_str = m_in.strftime("%H:%M") if has_morning else "--"
                    m_out_str = m_out.strftime("%H:%M") if has_morning else "--"
                    e_in_str = e_in.strftime("%H:%M") if has_evening else "--"
                    e_out_str = e_out.strftime("%H:%M") if has_evening else "--"
                    
                    c.execute('''
                        INSERT INTO timecards_v3 (employee, work_date, m_in, m_out, e_in, e_out, total_hours)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (emp_name, entry_date.strftime("%Y-%m-%d"), m_in_str, m_out_str, e_in_str, e_out_str, tot_hrs))
                    conn.commit()
                    st.success(f"Logged {tot_hrs:.2f} hours for {emp_name} on {entry_date}!")

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
# TAB 2: Payroll Calculation (Filter Period & Put Rate)
# ---------------------------------------------------------
with tab2:
    st.subheader("💵 Payroll Calculation")
    
    df = pd.read_sql_query("SELECT * FROM timecards_v3", conn)
    
    if not df.empty:
        df["work_date"] = pd.to_datetime(df["work_date"]).dt.date
        
        # Period Filter Selection
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

        # Filter dataframe by selected period
        filtered_df = df[(df["work_date"] >= start_date) & (df["work_date"] <= end_date)]
        
        if not filtered_df.empty:
            summary_df = filtered_df.groupby("employee").agg(
                Total_Hours=("total_hours", "sum")
            ).reset_index()
            
            summary_df["Hourly_Rate"] = 25.0  
            
            st.markdown("---")
            st.markdown("### ✍️ Enter Hourly Rate to Calculate Pay")
            st.caption(f"Showing total hours from **{start_date}** to **{end_date}**")
            
            edited_rates = st.data_editor(
                summary_df,
                column_config={
                    "employee": st.column_config.Column("Employee", disabled=True),
                    "Total_Hours": st.column_config.NumberColumn("Total Hours Worked", format="%.2f hrs", disabled=True),
                    "Hourly_Rate": st.column_config.NumberColumn("Hourly Rate (SAR)", format="SAR %.2f", min_value=0.0, step=0.50)
                },
                use_container_width=True,
                hide_index=True,
                key="calc_rate_editor"
            )
            
            # Instant calculation
            edited_rates["Total_Pay"] = edited_rates["Total_Hours"] * edited_rates["Hourly_Rate"]
            
            st.markdown("---")
            m1, m2 = st.columns(2)
            with m1:
                st.metric("Total Hours (All Staff)", f"{edited_rates['Total_Hours'].sum():.2f} hrs")
            with m2:
                st.metric("Total Amount to Pay", f"SAR {edited_rates['Total_Pay'].sum():,.2f}")
                
            st.markdown("### 📋 Final Payout Breakdown")
            st.dataframe(
                edited_rates,
                column_config={
                    "employee": "Employee Name",
                    "Total_Hours": st.column_config.NumberColumn("Total Hours", format="%.2f hrs"),
                    "Hourly_Rate": st.column_config.NumberColumn("Rate (SAR)", format="SAR %.2f"),
                    "Total_Pay": st.column_config.NumberColumn("Total Salary (SAR)", format="SAR %.2f")
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning(f"No shift entries found between {start_date} and {end_date}.")
    else:
        st.info("No shift logs found yet.")

# ---------------------------------------------------------
# TAB 3: History & Manual Edits
# ---------------------------------------------------------
with tab3:
    st.subheader("3-Month Shift Log & Manual Edits")
    
    df_raw = pd.read_sql_query("SELECT * FROM timecards_v3 ORDER BY work_date DESC", conn)
    
    if not df_raw.empty:
        edited_df = st.data_editor(
            df_raw,
            column_config={
                "id": "ID",
                "employee": "Employee",
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
            c.execute("DELETE FROM timecards_v3")
            for _, row in edited_df.iterrows():
                c.execute('''
                    INSERT INTO timecards_v3 (id, employee, work_date, m_in, m_out, e_in, e_out, total_hours)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (row['id'], row['employee'], row['work_date'], row['m_in'], row['m_out'], row['e_in'], row['e_out'], row['total_hours']))
            conn.commit()
            st.success("Database updated successfully!")
            st.rerun()
    else:
        st.info("No records to display.")
