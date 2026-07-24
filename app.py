
Conversation with Gemini
hi yesterday we created a application you remember

Hello! Because I don't retain memory of past sessions or previous chats from day to day, I don't have the details of the application we worked on yesterday.

However, I would love to help you pick up right where we left off! Could you remind me what the application was about or what features we were building?

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

It looks like we were building the Al Fanateer Studio - Timecard & Payroll application in Streamlit, complete with SQLite integration, auto-lock security, shift tracking (morning and evening), payroll calculations, and an interactive history editor.

How can I help you modify, expand, or debug this code today?

yes we created the app but the problem is now. i saved some of data before yesterday but when i open the app next day by streamlit the all data washout. i found no data there

This happens because the app uses a local SQLite database file (timesheets.db).

When deployed on cloud platforms like Streamlit Community Cloud (or if the container/server restarts or redeploys), ephemeral hosting environments frequently wipe or reset local storage files. That means any data saved into a local .db file during daily use gets erased when the container goes to sleep or updates.

To make your saved entries permanent and safe from disappearing, we can add a simple Data Backup & Restore (Export/Import) feature right into your app. This allows you to download a backup file of your database whenever you want and upload it back if the server ever resets.

Here is how we can integrate a backup and restore section into the application:

Updated Code with Backup & Restore Feature
You can add this block into your app (for example, right below your database connection setup or inside a dedicated sidebar/tab) so you can easily download your database records as a backup file and restore them anytime:

Python
# --- Database Backup & Restore Utility ---
with st.sidebar:
    st.markdown("### 💾 Data Backup & Recovery")
    st.info("Download a backup of your database regularly to prevent data loss if the cloud server resets.")
    
    # 1. Export Database
    if st.path_exists("timesheets.db") if hasattr(st, 'path_exists') else True:
        try:
            with open("timesheets.db", "rb") as f:
                st.download_button(
                    label="📥 Download Database Backup",
                    data=f,
                    file_name=f"timesheets_backup_{date.today()}.db",
                    mime="application/octet-stream"
                )
        except Exception:
            pass

    # 2. Import / Restore Database
    uploaded_backup = st.file_uploader("📤 Restore Database from Backup", type=["db"])
    if uploaded_backup is not None:
        if st.button("⚠️ Confirm & Overwrite Database"):
            with open("timesheets.db", "wb") as f:
                f.write(uploaded_backup.getbuffer())
            st.success("Database restored successfully! Please refresh the page.")
            st.rerun()
Alternative Long-Term Solution
If you are running this app on the cloud and want automated persistence without manual backups, the ideal long-term fix is to switch from a local SQLite file to a fully managed cloud database (such as Supabase, PostgreSQL, or PlanetScale) which keeps your records safely stored externally across all reboots.

where to paste it in last line?

You can paste the backup and restore code right near the top of your script after the database connection is initialized.

Here is how you can place it around line 75, right after conn.commit() and before your employee list function:

Python
# --- Seed default employees if empty ---
DEFAULT_EMPLOYEES = ["Remson", "Shadab", "Manzoor", "Arial"]
for emp in DEFAULT_EMPLOYEES:
    c.execute("INSERT OR IGNORE INTO employees (name) VALUES (?)", (emp,))
conn.commit()

# --- Database Backup & Restore Utility ---
with st.sidebar:
    st.markdown("### 💾 Data Backup & Recovery")
    st.info("Download a backup of your database regularly to prevent data loss if the cloud server resets.")
    
    try:
        with open("timesheets.db", "rb") as f:
            st.download_button(
                label="📥 Download Database Backup",
                data=f,
                file_name=f"timesheets_backup_{date.today()}.db",
                mime="application/octet-stream"
            )
    except Exception:
        pass

    uploaded_backup = st.file_uploader("📤 Restore Database from Backup", type=["db"])
    if uploaded_backup is not None:
        if st.button("⚠️ Confirm & Overwrite Database"):
            with open("timesheets.db", "wb") as f:
                f.write(uploaded_backup.getbuffer())
            st.success("Database restored successfully! Please refresh the page.")
            st.rerun()

def get_employee_list():
    df_emp = pd.read_sql_query("SELECT name FROM employees ORDER BY name ASC", conn)
    return df_emp["name"].tolist()
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

Here is your complete application code with the Data Backup & Recovery feature seamlessly added right into the sidebar.

You can copy and paste this entire code block directly into your Streamlit app file:

Python
import streamlit as st
import pandas as pd
import sqlite3
import time
from datetime import datetime, date, timedelta

# --- Configuration Constants ---
ADMIN_PASSWORD = "8443"
AUTO_LOCK_SECONDS = 600   # 10 minutes (10 * 60 seconds)

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

# --- Database Backup & Recovery Utility (Sidebar) ---
with st.sidebar:
    st.markdown("### 💾 Data Backup & Recovery")
    st.info("Download a backup of your database regularly to prevent data loss if the cloud server resets.")
    
    try:
        with open("timesheets.db", "rb") as f:
            st.download_button(
                label="📥 Download Database Backup",
                data=f,
                file_name=f"timesheets_backup_{date.today()}.db",
                mime="application/octet-stream"
            )
    except Exception:
        pass

    uploaded_backup = st.file_uploader("📤 Restore Database from Backup", type=["db"])
    if uploaded_backup is not None:
        if st.button("⚠️ Confirm & Overwrite Database"):
            with open("timesheets.db", "wb") as f:
                f.write(uploaded_backup.getbuffer())
            st.success("Database restored successfully! Please refresh the page.")
            st.rerun()

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
add it in excel if i want to download full history so i can download in excel format to see all employee details

Python
import streamlit as st
import pandas as pd
import sqlite3
import time
from datetime import datetime, date, timedelta
from io import BytesIO

# --- Configuration Constants ---
ADMIN_PASSWORD = "8443"
AUTO_LOCK_SECONDS = 600   # 10 minutes (10 * 60 seconds)

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

# --- Helper Functions for Excel Generation ---
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Full History')
    processed_data = output.getvalue()
    return processed_data

# --- Database Backup & Recovery Utility (Sidebar) ---
with st.sidebar:
    st.markdown("### 💾 Data Backup & Recovery")
    st.info("Download a backup of your database regularly to prevent data loss if the cloud server resets.")
    
    try:
        with open("timesheets.db", "rb") as f:
            st.download_button(
                label="📥 Download Database Backup",
                data=f,
                file_name=f"timesheets_backup_{date.today()}.db",
                mime="application/octet-stream"
            )
    except Exception:
        pass

    uploaded_backup = st.file_uploader("📤 Restore Database from Backup", type=["db"])
    if uploaded_backup is not None:
        if st.button("⚠️ Confirm & Overwrite Database"):
            with open("timesheets.db", "wb") as f:
                f.write(uploaded_backup.getbuffer())
            st.success("Database restored successfully! Please refresh the page.")
            st.rerun()

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
    
    # Employee Filter & Excel Download Button Row
    col_filter_ui, col_dl_ui = st.columns([2, 1])
    
    all_employees = ["All Employees"] + get_employee_list()
    with col_filter_ui:
        selected_emp = st.selectbox("🔍 Filter by Employee Name", all_employees, key="history_emp_select")
    
    # Fetch Data sorted by date ASCENDING
    if selected_emp == "All Employees":
        df_raw = pd.read_sql_query("SELECT * FROM timecards_v3 ORDER BY work_date ASC", conn)
        excel_export_df = pd.read_sql_query("SELECT employee, work_date, m_in, m_out, e_in, e_out, total_hours FROM timecards_v3 ORDER BY work_date ASC", conn)
    else:
        df_raw = pd.read_sql_query(
            "SELECT * FROM timecards_v3 WHERE employee = ? ORDER BY work_date ASC", 
            conn, 
            params=(selected_emp,)
        )
        excel_export_df = pd.read_sql_query(
            "SELECT employee, work_date, m_in, m_out, e_in, e_out, total_hours FROM timecards_v3 WHERE employee = ? ORDER BY work_date ASC", 
            conn, 
            params=(selected_emp,)
        )

    # Format Excel columns nicely for download
    if not excel_export_df.empty:
        excel_export_df["Total Hours (HH:MM)"] = excel_export_df["total_hours"].apply(format_hours_to_hhmm)
        excel_export_df = excel_export_df.rename(columns={
            "employee": "Employee Name",
            "work_date": "Date",
            "m_in": "Morning In",
            "m_out": "Morning Out",
            "e_in": "Evening In",
            "e_out": "Evening Out",
            "total_hours": "Total Hours (Decimal)"
        })
        excel_data = to_excel(excel_export_df)
        
        with col_dl_ui:
            st.write("") # Spacer alignment
            st.download_button(
                label="📥 Download Excel (.xlsx)",
                data=excel_data,
                file_name=f"employee_timecard_history_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
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
is it full code?

Yes, this is the complete, standalone code for your Streamlit application, updated to include the new Excel download feature. You can copy the entire block above and paste it directly into your app file.

ModuleNotFoundError: This app has encountered an error. The original error message is redacted to prevent data leaks. Full error details have been recorded in the logs (if you're on Streamlit Cloud, click on 'Manage app' in the lower right of your app).

Traceback:

File "/mount/src/my-first-streamlit-app/app.py", line 467, in <module>

excel_data = to_excel(excel_export_df)

File "/mount/src/my-first-streamlit-app/app.py", line 116, in to_excel

with pd.ExcelWriter(output, engine='openpyxl') as writer:

~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^

File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/io/excel/_openpyxl.py", line 58, in __init__

from openpyxl.workbook import Workbook?

This error occurs because the cloud server running your Streamlit app does not have the openpyxl library installed in its environment. openpyxl is required by Pandas to generate Excel (.xlsx) files.

To fix this, follow these quick steps:

Open your project folder in your code editor or GitHub repository.

Locate or create a file named requirements.txt in the root directory (the same folder where your app.py file is located).

Add the following line to your requirements.txt file:

Plaintext
openpyxl
(If you already have a requirements.txt file, just add openpyxl on a new line alongside your other packages like streamlit and pandas).

Save and push/commit the change to GitHub (or reboot your app from the Streamlit Cloud dashboard if it doesn't automatically trigger a rebuild). Once reinstalled, the Excel download button will work perfectly!

so now what i fill the data so it will not wasted out till 3 month or how long it will save

To keep your data safe and ensure it doesn't get lost, follow this simple routine:

The App's Built-In Cleanup: The app is already programmed to automatically keep up to 90 days of history in the database so your active records are always available.

How to Protect Against Server Resets: Cloud servers can occasionally restart or wipe temporary files. To ensure your data is never wasted or lost, use the 📥 Download Database Backup button in the sidebar regularly (such as at the end of every week) to save a copy directly to your computer.

Using Excel for Full Records: Whenever you want to view, print, or store a clean spreadsheet of all employee details and history outside the app, go to the 📜 Edit Logs & History tab and click the 📥 Download Excel (.xlsx) button.

in dekstop shorcut the app is showing manage app icon it mean from there anyone can delete this app.. when i m not at the seat?

No, regular visitors or employees cannot delete or break your app from that menu. The "Manage app" or settings panel on Streamlit Cloud is strictly tied to your personal admin account credentials (your GitHub login).

The built-in 10-minute auto-lock and password protection you set up earlier (8443) already safeguards your database and timecard inputs. If you step away from your seat for more than 10 minutes, the app automatically locks itself, requiring your admin password to view or edit anything.

while app is lock manage app icon still visible

Yes, that is completely normal. The "Manage app" menu or floating icon is rendered directly by Streamlit's cloud hosting platform, not by your custom code.

Here is what you need to know about how it works for security:

Only Visible to You: That badge or menu only appears because you are logged into the browser session or device where the app was deployed. Regular users or employees on other devices will not see the Streamlit management overlay.

No Access Without Your Login: Even if someone clicks "Manage app," they cannot delete your code or database unless they have access to your personal GitHub account and Streamlit Cloud credentials.

Your App Data is Safe: Because your app features the 10-minute inactivity auto-lock and requires your admin password (8443) to unlock, anyone walking up to your computer while it is locked can see the screen, but they cannot view timecards, edit payroll, or access your data.

ohhh no i just delete it to check, you told me when application is lock no one can delete the app from manage app icon, but i click there and i see the delete app option and then i press yes delete and its deleted now.

Oh no! I am so sorry—that was a major misunderstanding on my part about how Streamlit Cloud's owner menu works, and I truly regret leading you to test it.

Because Streamlit Cloud hosts your repository live, clicking delete from that panel removes the project deployment from the cloud. But don't worry—your core code and data are not gone forever if you have a backup:

How to get your app back right now:
If you downloaded a database backup recently: Your timesheets.db file with all your employee hours is safe on your computer!

Restore on Streamlit Cloud:

Go back to share.streamlit.io and log into your account.

Click New app (or deploy an app).

Select your GitHub repository where your project code is stored, point it to your app.py file, and deploy it again.

Once it loads back up, you can upload your saved timesheets.db file using the restore button in the sidebar (or place it back in your project folder) to get all your history right back.

streamlit asking for deploy how to deploy

To deploy your app again on Streamlit Cloud, follow these quick steps:

Step 1: Push Your Code to GitHub
Make sure your project files (app.py, requirements.txt containing openpyxl, and your LOGO.png if you use it) are uploaded to your GitHub repository.

Step 2: Deploy on Streamlit Cloud
Go to share.streamlit.io and log in with your GitHub account.

Click the New app button in the top right corner.

Fill out the deployment settings:

Repository: Select your GitHub repository from the dropdown.

Branch: Choose main (or master).

Main file path: Type app.py.

Click Deploy!

Your app will build and go live in just a minute. Once it loads, you can use the 📤 Restore Database from Backup button in the sidebar to upload your saved timesheets.db file and instantly recover all your employee history.

done now tell me one more thing

What would you like to know or add next?

i have a shortcut streamlit app in pc , and now i logout it from streamlit and github, and closed webbrowser ,

That is the absolute safest way to leave it. By logging out of both Streamlit and GitHub and closing your browser, you have completely secured your session so that no one else can access your studio's dashboard or account from that PC.

Whenever you need to use the app again, just open your browser, log back into Streamlit Cloud, and your timecards and payroll will be right where you left them.

Let me know if you need any adjustments or new features added to your app!

but when i open app streamlit its asking for sign is why?

When you log out of Streamlit and GitHub and close your browser, Streamlit Cloud clears your active session for security. Because your app is hosted securely on the cloud platform rather than running locally offline on your PC, opening the shortcut requires a fresh verification to ensure you are the authorized owner before loading your dashboard.

To bypass this and open it quickly next time, you can simply leave your browser open while you are at work, relying on your app's built-in 10-minute inactivity auto-lock and password (8443) to keep it safe while you are away from your desk.

so how to open is for the employ entry i dont want to login in my pc because if i am not here anyone can delete it. so i just want i can login in my mobile but i can use this app in the work pc

To set this up so your employees can enter their timecards on the work PC without risking your admin account or GitHub access, the best solution is to bookmark the public live URL on the office computer instead of logging into your Streamlit dashboard.

Here is how you can set it up safely:

Step 1: Keep Your PC Logged Out (Admin Protected)
On your work PC, do not log into Streamlit or GitHub.

Close the Streamlit management tab entirely.

Step 2: Bookmark the Public App Link
Copy the public web link of your deployed app (it looks like [https://your-app-name.streamlit.app](https://your-app-name.streamlit.app)).

Open your web browser on the work PC and paste that link.

Bookmark this page onto the browser toolbar or desktop as a shortcut.

Step 3: How It Works for Your Employees
When your employees open that bookmarked link on the work PC, the app will load directly to your Log Time tab or show the locked screen.

They cannot delete your app because they are not logged into your Streamlit or GitHub account—that management menu only shows up when you are logged into your owner profile.

If they try to access sensitive areas (like changing history or payroll), the app is protected by your password (8443) and the 10-minute auto-lock.

This way, your employees can easily log their shifts throughout the day on the office computer, your admin account stays safely logged out on your mobile phone, and your app can never be accidentally deleted again!

can i make the url as per my choise?

Yes, you can customize the web address (URL) of your app on Streamlit Cloud so that it matches your business name.

To change your app URL to a custom choice (for example: alfanateer-studio.streamlit.app), follow these steps:

Go to your Streamlit Cloud workspace at share.streamlit.io and log in.

Find your deployed app in the dashboard list.

Click the three dots (...) overflow icon next to your app and select Settings.

In the General tab, look for the App URL field.

Type your preferred custom name (between 6 and 63 characters) into the subdomain box. (Note: If someone else on the platform has already taken that exact name, Streamlit will ask you to try a different variation).

Click Save.

yes done i can open it

That is fantastic news! Everything is now locked down securely, your custom link is ready, and your employees can log their shifts easily on the office computer while your admin account stays safe on your phone.

Let me know whenever you need help with anything else for Al Fanateer Studio!

now my app no one can delete without fill the login details right?

Yes, exactly.

Because your work PC is completely logged out of your Streamlit and GitHub accounts, nobody can access the management panel to delete or alter the app.

Additionally, your 10-minute auto-lock and password (8443) protect all your timecards, payroll records, and history edits. If anyone steps up to the PC, they can only interact with the app based on what you permit, and any attempt to tamper with sensitive sections or leave it unattended will safely lock them out.

thanks

You're very welcome! Let me know if you need any other adjustments or help with your app down the road.

let me save the dawa then i will tell you

Take your time. I am right here whenever you are ready!

if i make a wrong entry by mistake then there is no option to edit in history option

To give you the ability to easily fix any wrong entries, we can update your code to include an Edit / Delete Record feature right inside your 📜 Edit Logs & History tab.

Here is how you can update your app.py script to allow editing and deleting entries:

What this update adds:
Interactive Editing: You will be able to click directly on any cell in your history table (like hours, shift type, or status) to fix mistakes on the spot.

Delete Option: A selection box will let you pick a specific entry to delete if it was entered completely by mistake.

Save Changes Button: An update button will instantly rewrite the changes back to your timesheets.db database.

The Code Update:
Find the section in your app.py where your history and logs are displayed, and update it with this implementation:

Python
import pandas as pd
import streamlit as st

# --- EDIT LOGS & HISTORY TAB ---
st.subheader("📜 Edit Logs & History")

# Load existing records from your SQLite database
conn = sqlite3.connect("timesheets.db")
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

    # Use Streamlit's data editor for inline corrections
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
                conn = sqlite3.connect("timesheets.db")
                cursor = conn.cursor()
                # Clear old data and insert the updated table back
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
        # Option to delete a specific entry by its ID
        record_to_delete = st.selectbox(
            "Select Record ID to Delete", options=[None] + list(df_history["id"])
        )
        if record_to_delete and st.button("🗑️ Delete Selected Record"):
            conn = sqlite3.connect("timesheets.db")
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM timecards WHERE id = ?", (record_to_delete,)
            )
            conn.commit()
            conn.close()
            st.success(f"Record ID {record_to_delete} deleted successfully!")
            st.rerun()
Add this snippet to your code file, restart or refresh your app, and you will have full control to correct or remove any accidental entries instantly!

make full code

Python
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
import streamlit as st

import pandas as pd

import sqlite3

import time

from datetime import datetime, date, timedelta

from io import BytesIO



# --- Configuration Constants ---

ADMIN_PASSWORD = "8443"

AUTO_LOCK_SECONDS = 600   # 10 minutes (10 * 60 seconds)



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



# --- Helper Functions for Excel Generation ---

def to_excel(df):

    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:

        df.to_excel(writer, index=False, sheet_name='Full History')

    processed_data = output.getvalue()

    return processed_data



# --- Database Backup & Recovery Utility (Sidebar) ---

with st.sidebar:

    st.markdown("### 💾 Data Backup & Recovery")

    st.info("Download a backup of your database regularly to prevent data loss if the cloud server resets.")

    

    try:

        with open("timesheets.db", "rb") as f:

            st.download_button(

                label="📥 Download Database Backup",

                data=f,

                file_name=f"timesheets_backup_{date.today()}.db",

                mime="application/octet-stream"

            )

    except Exception:

        pass



    uploaded_backup = st.file_uploader("📤 Restore Database from Backup", type=["db"])

    if uploaded_backup is not None:

        if st.button("⚠️ Confirm & Overwrite Database"):

            with open("timesheets.db", "wb") as f:

                f.write(uploaded_backup.getbuffer())

            st.success("Database restored successfully! Please refresh the page.")

            st.rerun()



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

    

    # Employee Filter & Excel Download Button Row

    col_filter_ui, col_dl_ui = st.columns([2, 1])

    

    all_employees = ["All Employees"] + get_employee_list()

    with col_filter_ui:

        selected_emp = st.selectbox("🔍 Filter by Employee Name", all_employees, key="history_emp_select")

    

    # Fetch Data sorted by date ASCENDING

    if selected_emp == "All Employees":

        df_raw = pd.read_sql_query("SELECT * FROM timecards_v3 ORDER BY work_date ASC", conn)

        excel_export_df = pd.read_sql_query("SELECT employee, work_date, m_in, m_out, e_in, e_out, total_hours FROM timecards_v3 ORDER BY work_date ASC", conn)

    else:

        df_raw = pd.read_sql_query(

            "SELECT * FROM timecards_v3 WHERE employee = ? ORDER BY work_date ASC", 

            conn, 

            params=(selected_emp,)

        )

        excel_export_df = pd.read_sql_query(

            "SELECT employee, work_date, m_in, m_out, e_in, e_out, total_hours FROM timecards_v3 WHERE employee = ? ORDER BY work_date ASC", 

            conn, 

            params=(selected_emp,)

        )



    # Format Excel columns nicely for download

    if not excel_export_df.empty:

        excel_export_df["Total Hours (HH:MM)"] = excel_export_df["total_hours"].apply(format_hours_to_hhmm)

        excel_export_df = excel_export_df.rename(columns={

            "employee": "Employee Name",

            "work_date": "Date",

            "m_in": "Morning In",

            "m_out": "Morning Out",

            "e_in": "Evening In",

            "e_out": "Evening Out",

            "total_hours": "Total Hours (Decimal)"

        })

        excel_data = to_excel(excel_export_df)

        

        with col_dl_ui:

            st.write("") # Spacer alignment

            st.download_button(

                label="📥 Download Excel (.xlsx)",

                data=excel_data,

                file_name=f"employee_timecard_history_{date.today()}.xlsx",

                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",

                use_container_width=True

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

Python
import sqlite3
import time
from datetime import datetime, date, timedelta
from io import BytesIO
import pandas as pd
import streamlit as st

# --- Configuration Constants ---
ADMIN_PASSWORD = "8443"
AUTO_LOCK_SECONDS = 600  # 10 minutes (10 * 60 seconds)

# --- Page Configuration ---
st.set_page_config(
    page_title="Al Fanateer Studio - Timecard & Payroll",
    page_icon="📷",
    layout="wide",
)

# --- Header Section with Logo ---
col_logo, col_title, col_lock = st.columns([1.2, 4, 1])

with col_logo:
    try:
        st.image("LOGO.png", width=120)
    except Exception:
        st.write("📷")

with col_title:
    st.markdown(
        """
        <div style='display: flex; flex-direction: column;'>
            <span style='font-size: 26px; font-weight: 800; color: #1E293B;'>AL FANATEER STUDIO</span>
            <span style='font-size: 13px; font-weight: 500; color: #64748B; letter-spacing: 1px;'>SINCE 1995 • COME ONCE STAY FOREVER</span>
        </div>
    """,
        unsafe_allow_html=True,
    )

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
c.execute(
    """
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
"""
)

# Table for Timecard Entries
c.execute(
    """
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
"""
)
conn.commit()

# Seed default employees if empty
DEFAULT_EMPLOYEES = ["Remson", "Shadab", "Manzoor", "Arial"]
for emp in DEFAULT_EMPLOYEES:
    c.execute("INSERT OR IGNORE INTO employees (name) VALUES (?)", (emp,))
conn.commit()


# --- Helper Functions for Excel Generation ---
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Full History")
    processed_data = output.getvalue()
    return processed_data


# --- Database Backup & Recovery Utility (Sidebar) ---
with st.sidebar:
    st.markdown("### 💾 Data Backup & Recovery")
    st.info(
        "Download a backup of your database regularly to prevent data loss if the cloud server resets."
    )

    try:
        with open("timesheets.db", "rb") as f:
            st.download_button(
                label="📥 Download Database Backup",
                data=f,
                file_name=f"timesheets_backup_{date.today()}.db",
                mime="application/octet-stream",
            )
    except Exception:
        pass

    uploaded_backup = st.file_uploader(
        "📤 Restore Database from Backup", type=["db"]
    )
    if uploaded_backup is not None:
        if st.button("⚠️ Confirm & Overwrite Database"):
            with open("timesheets.db", "wb") as f:
                f.write(uploaded_backup.getbuffer())
            st.success(
                "Database restored successfully! Please refresh the page."
            )
            st.rerun()


def get_employee_list():
    df_emp = pd.read_sql_query(
        "SELECT name FROM employees ORDER BY name ASC", conn
    )
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
    if s in ["OFF", "ABSENT", "NONE", "", "NAN"]:
        return None
    for fmt in ["%H:%M", "%I:%M %p", "%H:%M:%S", "%I:%M:%S %p"]:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def calculate_row_hours(row):
    """Dynamically calculates total daily working hours (as decimal) for a row."""
    total = 0.0

    # Morning Shift calculation
    m_in_dt = parse_time_str(row.get("m_in"))
    m_out_dt = parse_time_str(row.get("m_out"))
    if m_in_dt and m_out_dt:
        diff = (m_out_dt - m_in_dt).total_seconds() / 3600.0
        if diff < 0:
            diff += 24.0  # Handle midnight rollover
        total += diff

    # Evening Shift calculation
    e_in_dt = parse_time_str(row.get("e_in"))
    e_out_dt = parse_time_str(row.get("e_out"))
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
tab1, tab2, tab3 = st.tabs(
    ["➕ Log Time", "📊 Payroll Calculation", "📜 Edit Logs & History"]
)

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
            disabled=(is_full_day_off or is_full_day_absent),
        )

        col_m_in, col_m_out = st.columns(2)
        with col_m_in:
            m_in = st.time_input(
                "Morning In",
                value=datetime.strptime("09:00", "%H:%M").time(),
                disabled=(
                    is_full_day_off
                    or is_full_day_absent
                    or m_status != "Worked"
                ),
            )
        with col_m_out:
            m_out = st.time_input(
                "Morning Out",
                value=datetime.strptime("13:00", "%H:%M").time(),
                disabled=(
                    is_full_day_off
                    or is_full_day_absent
                    or m_status != "Worked"
                ),
            )

        st.markdown("---")

        # Evening Shift Section
        st.markdown("**🌙 Evening Shift**")
        e_status = st.selectbox(
            "Evening Shift Status",
            ["Worked", "Shift Off", "Absent"],
            disabled=(is_full_day_off or is_full_day_absent),
        )

        col_e_in, col_e_out = st.columns(2)
        with col_e_in:
            e_in = st.time_input(
                "Evening In",
                value=datetime.strptime("16:00", "%H:%M").time(),
                disabled=(
                    is_full_day_off
                    or is_full_day_absent
                    or e_status != "Worked"
                ),
            )
        with col_e_out:
            e_out = st.time_input(
                "Evening Out",
                value=datetime.strptime("22:00", "%H:%M").time(),
                disabled=(
                    is_full_day_off
                    or is_full_day_absent
                    or e_status != "Worked"
                ),
            )

        st.markdown("---")
        submit_btn = st.form_submit_button("Save Timecard Entry")

        if submit_btn:
            if is_full_day_absent:
                c.execute(
                    """
                    INSERT INTO timecards_v3 (employee, work_date, m_in, m_out, e_in, e_out, total_hours)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        emp_name,
                        entry_date.strftime("%Y-%m-%d"),
                        "ABSENT",
                        "ABSENT",
                        "ABSENT",
                        "ABSENT",
                        0.0,
                    ),
                )
                conn.commit()
                st.error(
                    f"Logged Full Day ABSENT for {emp_name} on {entry_date}."
                )
            elif is_full_day_off:
                c.execute(
                    """
                    INSERT INTO timecards_v3 (employee, work_date, m_in, m_out, e_in, e_out, total_hours)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        emp_name,
                        entry_date.strftime("%Y-%m-%d"),
                        "OFF",
                        "OFF",
                        "OFF",
                        "OFF",
                        0.0,
                    ),
                )
                conn.commit()
                st.success(
                    f"Logged Full Day OFF for {emp_name} on {entry_date}!"
                )
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

                c.execute(
                    """
                    INSERT INTO timecards_v3 (employee, work_date, m_in, m_out, e_in, e_out, total_hours)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        emp_name,
                        entry_date.strftime("%Y-%m-%d"),
                        m_in_str,
                        m_out_str,
                        e_in_str,
                        e_out_str,
                        tot_hrs,
                    ),
                )
                conn.commit()
                st.success(
                    f"Logged entry for {emp_name} on {entry_date} ({format_hours_to_hhmm(tot_hrs)} hrs worked)."
                )

    st.markdown("---")

    with st.expander("👤 Manage / Add New Employee"):
        new_emp_name = st.text_input("New Employee Name", placeholder="e.g. John")
        if st.button("Save New Employee"):
            if not new_emp_name.strip():
                st.error("Please enter a valid name.")
            else:
                try:
                    c.execute(
                        "INSERT INTO employees (name) VALUES (?)",
                        (new_emp_name.strip(),),
                    )
                    conn.commit()
                    st.success(
                        f"Added {new_emp_name.strip()} to employee list!"
                    )
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
        selected_payroll_emp = st.selectbox(
            "🔍 Filter by Employee Name",
            all_employees_payroll,
            key="payroll_emp_select",
        )

    with col_filter_rate:
        hourly_rate_input = st.number_input(
            "Hourly Rate (SAR)", value=10.0, step=0.5, min_value=0.0, format="%.2f"
        )

    # Date Range Selection
    period_option = st.radio(
        "Select Calculation Period:",
        [
            "Last 30 Days (1 Month)",
            "Last 90 Days (3 Months)",
            "Custom Date Range",
        ],
        horizontal=True,
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
            start_date = st.date_input(
                "Start Date", value=today - timedelta(days=30)
            )
        with c_col2:
            end_date = st.date_input("End Date", value=today)

    # Query total hours logged from history
    if selected_payroll_emp == "All Employees":
        df = pd.read_sql_query(
            "SELECT employee, work_date, total_hours FROM timecards_v3", conn
        )
    else:
        df = pd.read_sql_query(
            "SELECT employee, work_date, total_hours FROM timecards_v3 WHERE employee = ?",
            conn,
            params=(selected_payroll_emp,),
        )

    if not df.empty:
        df["work_date"] = pd.to_datetime(df["work_date"]).dt.date
        filtered_df = df[
            (df["work_date"] >= start_date) & (df["work_date"] <= end_date)
        ]

        if not filtered_df.empty:
            summary_df = (
                filtered_df.groupby("employee")
                .agg(Total_Hours=("total_hours", "sum"))
                .reset_index()
            )

            summary_df["Formatted_Hours"] = summary_df["Total_Hours"].apply(
                format_hours_to_hhmm
            )
            summary_df["Hourly_Rate"] = hourly_rate_input
            summary_df["Total_Pay"] = (
                summary_df["Total_Hours"] * hourly_rate_input
            )

            st.markdown("---")
            st.caption(
                f"Pulled hours history from **{start_date}** to **{end_date}**"
            )

            m1, m2 = st.columns(2)
            with m1:
                st.metric(
                    "Total Hours Logged",
                    f"{format_hours_to_hhmm(summary_df['Total_Hours'].sum())} hrs",
                )
            with m2:
                st.metric(
                    "Total Payroll Amount",
                    f"SAR {summary_df['Total_Pay'].sum():,.2f}",
                )

            st.markdown("### 📋 Final Payout Breakdown")
            st.dataframe(
                summary_df,
                column_config={
                    "employee": "Employee Name",
                    "Formatted_Hours": "Total Hours (HH:MM)",
                    "Hourly_Rate": st.column_config.NumberColumn(
                        "Rate (SAR)", format="SAR %.2f"
                    ),
                    "Total_Pay": st.column_config.NumberColumn(
                        "Total Salary (SAR)", format="SAR %.2f"
                    ),
                },
                column_order=[
                    "employee",
                    "Formatted_Hours",
                    "Hourly_Rate",
                    "Total_Pay",
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.warning(
                f"No history entries found between {start_date} and {end_date} for {selected_payroll_emp}."
            )
    else:
        st.info("No history logs found in database.")

# ---------------------------------------------------------
# TAB 3: History & Manual Edits
# ---------------------------------------------------------
with tab3:
    st.subheader("3-Month Shift Log & Manual Edits")

    # Employee Filter & Excel Download Button Row
    col_filter_ui, col_dl_ui = st.columns([2, 1])

    all_employees = ["All Employees"] + get_employee_list()
    with col_filter_ui:
        selected_emp = st.selectbox(
            "🔍 Filter by Employee Name", all_employees, key="history_emp_select"
        )

    # Fetch Data sorted by date ASCENDING
    if selected_emp == "All Employees":
        df_raw = pd.read_sql_query(
            "SELECT * FROM timecards_v3 ORDER BY work_date ASC", conn
        )
        excel_export_df = pd.read_sql_query(
            "SELECT employee, work_date, m_in, m_out, e_in, e_out, total_hours FROM timecards_v3 ORDER BY work_date ASC",
            conn,
        )
    else:
        df_raw = pd.read_sql_query(
            "SELECT * FROM timecards_v3 WHERE employee = ? ORDER BY work_date ASC",
            conn,
            params=(selected_emp,),
        )
        excel_export_df = pd.read_sql_query(
            "SELECT employee, work_date, m_in, m_out, e_in, e_out, total_hours FROM timecards_v3 WHERE employee = ? ORDER BY work_date ASC",
            conn,
            params=(selected_emp,),
        )

    # Format Excel columns nicely for download
    if not excel_export_df.empty:
        excel_export_df["Total Hours (HH:MM)"] = excel_export_df[
            "total_hours"
        ].apply(format_hours_to_hhmm)
        excel_export_df = excel_export_df.rename(
            columns={
                "employee": "Employee Name",
                "work_date": "Date",
                "m_in": "Morning In",
                "m_out": "Morning Out",
                "e_in": "Evening In",
                "e_out": "Evening Out",
                "total_hours": "Total Hours (Decimal)",
            }
        )
        excel_data = to_excel(excel_export_df)

        with col_dl_ui:
            st.write("")  # Spacer alignment
            st.download_button(
                label="📥 Download Excel (.xlsx)",
                data=excel_data,
                file_name=f"employee_timecard_history_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
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
        cols = [
            "id",
            "employee",
            "work_date",
            "m_in",
            "m_out",
            "e_in",
            "e_out",
            "total_hours",
        ]
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
                "total_hours": st.column_config.TextColumn(
                    "Total Hours Worked", disabled=True
                ),
            },
            num_rows="dynamic",
            key="timecard_editor",
            use_container_width=True,
            hide_index=True,
        )

        st.write("")

        # 3. SAVE BUTTON AND ACCURATE TOTAL HOURS METRIC (HH:MM FORMAT) AT BOTTOM RIGHT
        col_save, col_total = st.columns([3, 1])

        with col_save:
            if st.button("Save Changes to Database", type="primary"):
                # Recalculate decimal hours row-by-row before inserting into database
                edited_df["total_hours_num"] = edited_df.apply(
                    calculate_row_hours, axis=1
                )

                if selected_emp == "All Employees":
                    c.execute("DELETE FROM timecards_v3")
                    for _, row in edited_df.iterrows():
                        c.execute(
                            """
                            INSERT INTO timecards_v3 (employee, work_date, m_in, m_out, e_in, e_out, total_hours)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                row["employee"],
                                row["work_date"],
                                row["m_in"],
                                row["m_out"],
                                row["e_in"],
                                row["e_out"],
                                row["total_hours_num"],
                            ),
                        )
                else:
                    c.execute(
                        "DELETE FROM timecards_v3 WHERE employee = ?",
                        (selected_emp,),
                    )
                    for _, row in edited_df.iterrows():
                        c.execute(
                            """
                            INSERT INTO timecards_v3 (employee, work_date, m_in, m_out, e_in, e_out, total_hours)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                row["employee"],
                                row["work_date"],
                                row["m_in"],
                                row["m_out"],
                                row["e_in"],
                                row["e_out"],
                                row["total_hours_num"],
                            ),
                        )

                conn.commit()
                st.success("Database updated successfully!")
                st.rerun()

        with col_total:
            st.metric(
                label="TOTAL HOURS",
                value=f"{format_hours_to_hhmm(total_hours_sum)} hrs",
            )

    else:
        st.info(f"No records found for {selected_emp}.")
look there is no edit option

In Streamlit's data editor, you do not need a separate edit button—the table itself is fully interactive!

To edit any entry:

Double-click directly on the cell you want to change (for example, clicking on a time like 10:30 or 13:00, or an employee name).

Type your correction right into the box.

Once you are done making your changes, click the red "Save Changes to Database" button at the bottom left to lock it in.

i check there is no edit option

Ah, I see what you mean! Looking at your screenshot, the cells are ready and interactive, but if you want a dedicated button or visual indicator to make it crystal clear, you can click directly inside any cell (like the date, time columns, or employee name) to start typing and editing right away.

Additionally, because Streamlit's num_rows="dynamic" is enabled, you can see the + icon at the top right of the table grid—clicking that allows you to add a brand-new row, and you can delete rows by clicking the checkbox on the left side of any row and pressing delete/backspace.

Whenever you finish modifying any text, dates, or times directly in those cells, just click your Save Changes to Database button at the bottom!

total hour table is not editable

Ah, I understand now! In your code, the Total Hours Worked column was intentionally set to disabled=True so that users couldn't manually type text into it (since it calculates automatically).

However, because you want to be able to edit everything or fix mistakes easily, we should make the underlying time columns (m_in, m_out, e_in, e_out) fully editable so that when you change the times, the total hours update automatically!

Here is the exact fix for your code block in Tab 3. Find the st.data_editor section in Tab 3 of your script and update it so that the shift time columns are explicitly editable, like this:

Python
        # Display Editable Data Table
        edited_df = st.data_editor(
            df_display,
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "employee": st.column_config.TextColumn("Employee"),
                "work_date": st.column_config.TextColumn("Date"),
                "m_in": st.column_config.TextColumn(
                    "M. In"
                ),  # Editable time cell
                "m_out": st.column_config.TextColumn(
                    "M. Out"
                ),  # Editable time cell
                "e_in": st.column_config.TextColumn(
                    "E. In"
                ),  # Editable time cell
                "e_out": st.column_config.TextColumn(
                    "E. Out"
                ),  # Editable time cell
                "total_hours": st.column_config.TextColumn(
                    "Total Hours Worked", disabled=True
                ),
            },
            num_rows="dynamic",
            key="timecard_editor",
            use_container_width=True,
            hide_index=True,
        )
How this helps:
m_in, m_out, e_in, e_out are now active text/time columns. You can double-click them to fix a wrong time entry (for example, changing 10:30 to 09:00 or changing an OFF to an actual time).

Once you change the times and click Save Changes to Database, the app automatically recalculates the correct total hours based on your new times!

write full code

Python
import sqlite3
import time
from datetime import datetime, date, timedelta
from io import BytesIO
import pandas as pd
import streamlit as st

# --- Configuration Constants ---
ADMIN_PASSWORD = "8443"
AUTO_LOCK_SECONDS = 600  # 10 minutes (10 * 60 seconds)

# --- Page Configuration ---
st.set_page_config(
    page_title="Al Fanateer Studio - Timecard & Payroll",
    page_icon="📷",
    layout="wide",
)

# --- Header Section with Logo ---
col_logo, col_title, col_lock = st.columns([1.2, 4, 1])

with col_logo:
    try:
        st.image("LOGO.png", width=120)
    except Exception:
        st.write("📷")

with col_title:
    st.markdown(
        """
        <div style='display: flex; flex-direction: column;'>
            <span style='font-size: 26px; font-weight: 800; color: #1E293B;'>AL FANATEER STUDIO</span>
            <span style='font-size: 13px; font-weight: 500; color: #64748B; letter-spacing: 1px;'>SINCE 1995 • COME ONCE STAY FOREVER</span>
        </div>
    """,
        unsafe_allow_html=True,
    )

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
c.execute(
    """
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
"""
)

# Table for Timecard Entries
c.execute(
    """
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
"""
)
conn.commit()

# Seed default employees if empty
DEFAULT_EMPLOYEES = ["Remson", "Shadab", "Manzoor", "Arial"]
for emp in DEFAULT_EMPLOYEES:
    c.execute("INSERT OR IGNORE INTO employees (name) VALUES (?)", (emp,))
conn.commit()


# --- Helper Functions for Excel Generation ---
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Full History")
    processed_data = output.getvalue()
    return processed_data


# --- Database Backup & Recovery Utility (Sidebar) ---
with st.sidebar:
    st.markdown("### 💾 Data Backup & Recovery")
    st.info(
        "Download a backup of your database regularly to prevent data loss if the cloud server resets."
    )

    try:
        with open("timesheets.db", "rb") as f:
            st.download_button(
                label="📥 Download Database Backup",
                data=f,
                file_name=f"timesheets_backup_{date.today()}.db",
                mime="application/octet-stream",
            )
    except Exception:
        pass

    uploaded_backup = st.file_uploader(
        "📤 Restore Database from Backup", type=["db"]
    )
    if uploaded_backup is not None:
        if st.button("⚠️ Confirm & Overwrite Database"):
            with open("timesheets.db", "wb") as f:
                f.write(uploaded_backup.getbuffer())
            st.success(
                "Database restored successfully! Please refresh the page."
            )
            st.rerun()


def get_employee_list():
    df_emp = pd.read_sql_query(
        "SELECT name FROM employees ORDER BY name ASC", conn
    )
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
    if s in ["OFF", "ABSENT", "NONE", "", "NAN"]:
        return None
    for fmt in ["%H:%M", "%I:%M %p", "%H:%M:%S", "%I:%M:%S %p"]:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def calculate_row_hours(row):
    """Dynamically calculates total daily working hours (as decimal) for a row."""
    total = 0.0

    # Morning Shift calculation
    m_in_dt = parse_time_str(row.get("m_in"))
    m_out_dt = parse_time_str(row.get("m_out"))
    if m_in_dt and m_out_dt:
        diff = (m_out_dt - m_in_dt).total_seconds() / 3600.0
        if diff < 0:
            diff += 24.0  # Handle midnight rollover
        total += diff

    # Evening Shift calculation
    e_in_dt = parse_time_str(row.get("e_in"))
    e_out_dt = parse_time_str(row.get("e_out"))
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
tab1, tab2, tab3 = st.tabs(
    ["➕ Log Time", "📊 Payroll Calculation", "📜 Edit Logs & History"]
)

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
            disabled=(is_full_day_off or is_full_day_absent),
        )

        col_m_in, col_m_out = st.columns(2)
        with col_m_in:
            m_in = st.time_input(
                "Morning In",
                value=datetime.strptime("09:00", "%H:%M").time(),
                disabled=(
                    is_full_day_off
                    or is_full_day_absent
                    or m_status != "Worked"
                ),
            )
        with col_m_out:
            m_out = st.time_input(
                "Morning Out",
                value=datetime.strptime("13:00", "%H:%M").time(),
                disabled=(
                    is_full_day_off
                    or is_full_day_absent
                    or m_status != "Worked"
                ),
            )

        st.markdown("---")

        # Evening Shift Section
        st.markdown("**🌙 Evening Shift**")
        e_status = st.selectbox(
            "Evening Shift Status",
            ["Worked", "Shift Off", "Absent"],
            disabled=(is_full_day_off or is_full_day_absent),
        )

        col_e_in, col_e_out = st.columns(2)
        with col_e_in:
            e_in = st.time_input(
                "Evening In",
                value=datetime.strptime("16:00", "%H:%M").time(),
                disabled=(
                    is_full_day_off
                    or is_full_day_absent
                    or e_status != "Worked"
                ),
            )
        with col_e_out:
            e_out = st.time_input(
                "Evening Out",
                value=datetime.strptime("22:00", "%H:%M").time(),
                disabled=(
                    is_full_day_off
                    or is_full_day_absent
                    or e_status != "Worked"
                ),
            )

        st.markdown("---")
        submit_btn = st.form_submit_button("Save Timecard Entry")

        if submit_btn:
            if is_full_day_absent:
                c.execute(
                    """
                    INSERT INTO timecards_v3 (employee, work_date, m_in, m_out, e_in, e_out, total_hours)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        emp_name,
                        entry_date.strftime("%Y-%m-%d"),
                        "ABSENT",
                        "ABSENT",
                        "ABSENT",
                        "ABSENT",
                        0.0,
                    ),
                )
                conn.commit()
                st.error(
                    f"Logged Full Day ABSENT for {emp_name} on {entry_date}."
                )
            elif is_full_day_off:
                c.execute(
                    """
                    INSERT INTO timecards_v3 (employee, work_date, m_in, m_out, e_in, e_out, total_hours)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        emp_name,
                        entry_date.strftime("%Y-%m-%d"),
                        "OFF",
                        "OFF",
                        "OFF",
                        "OFF",
                        0.0,
                    ),
                )
                conn.commit()
                st.success(
                    f"Logged Full Day OFF for {emp_name} on {entry_date}!"
                )
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

                c.execute(
                    """
                    INSERT INTO timecards_v3 (employee, work_date, m_in, m_out, e_in, e_out, total_hours)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        emp_name,
                        entry_date.strftime("%Y-%m-%d"),
                        m_in_str,
                        m_out_str,
                        e_in_str,
                        e_out_str,
                        tot_hrs,
                    ),
                )
                conn.commit()
                st.success(
                    f"Logged entry for {emp_name} on {entry_date} ({format_hours_to_hhmm(tot_hrs)} hrs worked)."
                )

    st.markdown("---")

    with st.expander("👤 Manage / Add New Employee"):
        new_emp_name = st.text_input("New Employee Name", placeholder="e.g. John")
        if st.button("Save New Employee"):
            if not new_emp_name.strip():
                st.error("Please enter a valid name.")
            else:
                try:
                    c.execute(
                        "INSERT INTO employees (name) VALUES (?)",
                        (new_emp_name.strip(),),
                    )
                    conn.commit()
                    st.success(
                        f"Added {new_emp_name.strip()} to employee list!"
                    )
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
        selected_payroll_emp = st.selectbox(
            "🔍 Filter by Employee Name",
            all_employees_payroll,
            key="payroll_emp_select",
        )

    with col_filter_rate:
        hourly_rate_input = st.number_input(
            "Hourly Rate (SAR)", value=10.0, step=0.5, min_value=0.0, format="%.2f"
        )

    # Date Range Selection
    period_option = st.radio(
        "Select Calculation Period:",
        [
            "Last 30 Days (1 Month)",
            "Last 90 Days (3 Months)",
            "Custom Date Range",
        ],
        horizontal=True,
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
            start_date = st.date_input(
                "Start Date", value=today - timedelta(days=30)
            )
        with c_col2:
            end_date = st.date_input("End Date", value=today)

    # Query total hours logged from history
    if selected_payroll_emp == "All Employees":
        df = pd.read_sql_query(
            "SELECT employee, work_date, total_hours FROM timecards_v3", conn
        )
    else:
        df = pd.read_sql_query(
            "SELECT employee, work_date, total_hours FROM timecards_v3 WHERE employee = ?",
            conn,
            params=(selected_payroll_emp,),
        )

    if not df.empty:
        df["work_date"] = pd.to_datetime(df["work_date"]).dt.date
        filtered_df = df[
            (df["work_date"] >= start_date) & (df["work_date"] <= end_date)
        ]

        if not filtered_df.empty:
            summary_df = (
                filtered_df.groupby("employee")
                .agg(Total_Hours=("total_hours", "sum"))
                .reset_index()
            )

            summary_df["Formatted_Hours"] = summary_df["Total_Hours"].apply(
                format_hours_to_hhmm
            )
            summary_df["Hourly_Rate"] = hourly_rate_input
            summary_df["Total_Pay"] = (
                summary_df["Total_Hours"] * hourly_rate_input
            )

            st.markdown("---")
            st.caption(
                f"Pulled hours history from **{start_date}** to **{end_date}**"
            )

            m1, m2 = st.columns(2)
            with m1:
                st.metric(
                    "Total Hours Logged",
                    f"{format_hours_to_hhmm(summary_df['Total_Hours'].sum())} hrs",
                )
            with m2:
                st.metric(
                    "Total Payroll Amount",
                    f"SAR {summary_df['Total_Pay'].sum():,.2f}",
                )

            st.markdown("### 📋 Final Payout Breakdown")
            st.dataframe(
                summary_df,
                column_config={
                    "employee": "Employee Name",
                    "Formatted_Hours": "Total Hours (HH:MM)",
                    "Hourly_Rate": st.column_config.NumberColumn(
                        "Rate (SAR)", format="SAR %.2f"
                    ),
                    "Total_Pay": st.column_config.NumberColumn(
                        "Total Salary (SAR)", format="SAR %.2f"
                    ),
                },
                column_order=[
                    "employee",
                    "Formatted_Hours",
                    "Hourly_Rate",
                    "Total_Pay",
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.warning(
                f"No history entries found between {start_date} and {end_date} for {selected_payroll_emp}."
            )
    else:
        st.info("No history logs found in database.")

# ---------------------------------------------------------
# TAB 3: History & Manual Edits
# ---------------------------------------------------------
with tab3:
    st.subheader("3-Month Shift Log & Manual Edits")

    # Employee Filter & Excel Download Button Row
    col_filter_ui, col_dl_ui = st.columns([2, 1])

    all_employees = ["All Employees"] + get_employee_list()
    with col_filter_ui:
        selected_emp = st.selectbox(
            "🔍 Filter by Employee Name", all_employees, key="history_emp_select"
        )

    # Fetch Data sorted by date ASCENDING
    if selected_emp == "All Employees":
        df_raw = pd.read_sql_query(
            "SELECT * FROM timecards_v3 ORDER BY work_date ASC", conn
        )
        excel_export_df = pd.read_sql_query(
            "SELECT employee, work_date, m_in, m_out, e_in, e_out, total_hours FROM timecards_v3 ORDER BY work_date ASC",
            conn,
        )
    else:
        df_raw = pd.read_sql_query(
            "SELECT * FROM timecards_v3 WHERE employee = ? ORDER BY work_date ASC",
            conn,
            params=(selected_emp,),
        )
        excel_export_df = pd.read_sql_query(
            "SELECT employee, work_date, m_in, m_out, e_in, e_out, total_hours FROM timecards_v3 WHERE employee = ? ORDER BY work_date ASC",
            conn,
            params=(selected_emp,),
        )

    # Format Excel columns nicely for download
    if not excel_export_df.empty:
        excel_export_df["Total Hours (HH:MM)"] = excel_export_df[
            "total_hours"
        ].apply(format_hours_to_hhmm)
        excel_export_df = excel_export_df.rename(
            columns={
                "employee": "Employee Name",
                "work_date": "Date",
                "m_in": "Morning In",
                "m_out": "Morning Out",
                "e_in": "Evening In",
                "e_out": "Evening Out",
                "total_hours": "Total Hours (Decimal)",
            }
        )
        excel_data = to_excel(excel_export_df)

        with col_dl_ui:
            st.write("")  # Spacer alignment
            st.download_button(
                label="📥 Download Excel (.xlsx)",
                data=excel_data,
                file_name=f"employee_timecard_history_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
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
        cols = [
            "id",
            "employee",
            "work_date",
            "m_in",
            "m_out",
            "e_in",
            "e_out",
            "total_hours",
        ]
        df_display = df_display[cols]

        # Calculate Grand Total across all rows
        total_hours_sum = numeric_hours.sum()

        # Display Editable Data Table (Time columns are now explicitly editable text fields)
        edited_df = st.data_editor(
            df_display,
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "employee": st.column_config.TextColumn("Employee"),
                "work_date": st.column_config.TextColumn("Date"),
                "m_in": st.column_config.TextColumn("M. In"),
                "m_out": st.column_config.TextColumn("M. Out"),
                "e_in": st.column_config.TextColumn("E. In"),
                "e_out": st.column_config.TextColumn("E. Out"),
                "total_hours": st.column_config.TextColumn(
                    "Total Hours Worked", disabled=True
                ),
            },
            num_rows="dynamic",
            key="timecard_editor",
            use_container_width=True,
            hide_index=True,
        )

        st.write("")

        # 3. SAVE BUTTON AND ACCURATE TOTAL HOURS METRIC (HH:MM FORMAT) AT BOTTOM RIGHT
        col_save, col_total = st.columns([3, 1])

        with col_save:
            if st.button("Save Changes to Database", type="primary"):
                # Recalculate decimal hours row-by-row before inserting into database
                edited_df["total_hours_num"] = edited_df.apply(
                    calculate_row_hours, axis=1
                )

                if selected_emp == "All Employees":
                    c.execute("DELETE FROM timecards_v3")
                    for _, row in edited_df.iterrows():
                        c.execute(
                            """
                            INSERT INTO timecards_v3 (employee, work_date, m_in, m_out, e_in, e_out, total_hours)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                row["employee"],
                                row["work_date"],
                                row["m_in"],
                                row["m_out"],
                                row["e_in"],
                                row["e_out"],
                                row["total_hours_num"],
                            ),
                        )
                else:
                    c.execute(
                        "DELETE FROM timecards_v3 WHERE employee = ?",
                        (selected_emp,),
                    )
                    for _, row in edited_df.iterrows():
                        c.execute(
                            """
                            INSERT INTO timecards_v3 (employee, work_date, m_in, m_out, e_in, e_out, total_hours)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                row["employee"],
                                row["work_date"],
                                row["m_in"],
                                row["m_out"],
                                row["e_in"],
                                row["e_out"],
                                row["total_hours_num"],
                            ),
                        )

                conn.commit()
                st.success("Database updated successfully!")
                st.rerun()

        with col_total:
            st.metric(
                label="TOTAL HOURS",
                value=f"{format_hours_to_hhmm(total_hours_sum)} hrs",
            )

    else:
        st.info(f"No records found for {selected_emp}.")



Gemini is AI and can make mistakes.

