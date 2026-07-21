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

# --- Header Section with Logo ---
st.title("📷 AL FANATEER STUDIO")
st.caption("SINCE 1995 • 'COME ONCE STAY FOREVER'")

# Display logo if uploaded
try:
    st.image("LOGO.png", width=140)
except Exception:
    pass

st.markdown("---")

# --- Database Setup (SQLite) ---
conn = sqlite3.connect("timesheets.db", check_same_thread=False)
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS timecards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee TEXT,
        hourly_rate REAL,
        work_date TEXT,
        time_in TEXT,
        time_out TEXT,
        hours_worked REAL
    )
''')
conn.commit()

# --- Auto Cleanup: Delete records older than 90 days (3 months) ---
three_months_ago = (date.today() - timedelta(days=90)).strftime("%Y-%m-%d")
c.execute("DELETE FROM timecards WHERE work_date < ?", (three_months_ago,))
conn.commit()

# --- Tab Navigation for Mobile ---
tab1, tab2, tab3 = st.tabs(["➕ Log / Edit Time", "📊 Hours & Salary", "📜 3-Month Logs"])

# ---------------------------------------------------------
# TAB 1: Log or Edit Entry
# ---------------------------------------------------------
with tab1:
    st.subheader("Clock In / Out Entry")
    
    with st.form("time_entry_form", clear_on_submit=True):
        emp_name = st.text_input("Employee Name", placeholder="e.g. Alex Johnson")
        hourly_rate = st.number_input("Hourly Rate ($)", min_value=0.0, value=25.0, step=0.50)
        entry_date = st.date_input("Date", value=date.today())
        
        col_in, col_out = st.columns(2)
        with col_in:
            time_in = st.time_input("Time In", value=datetime.strptime("09:00", "%H:%M").time())
        with col_out:
            time_out = st.time_input("Time Out", value=datetime.strptime("17:00", "%H:%M").time())
            
        submit_btn = st.form_submit_button("Save Timecard Entry")
        
        if submit_btn:
            if not emp_name.strip():
                st.error("Please enter an employee name.")
            else:
                datetime_in = datetime.combine(entry_date, time_in)
                datetime_out = datetime.combine(entry_date, time_out)
                
                # Handle shifts spanning midnight
                if datetime_out <= datetime_in:
                    datetime_out += timedelta(days=1)
                    
                duration = (datetime_out - datetime_in).total_seconds() / 3600.0
                
                c.execute('''
                    INSERT INTO timecards (employee, hourly_rate, work_date, time_in, time_out, hours_worked)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (emp_name, hourly_rate, entry_date.strftime("%Y-%m-%d"), time_in.strftime("%H:%M"), time_out.strftime("%H:%M"), round(duration, 2)))
                conn.commit()
                st.success(f"Logged {duration:.2f} hrs for {emp_name} on {entry_date}!")

# ---------------------------------------------------------
# TAB 2: Payroll Summary
# ---------------------------------------------------------
with tab2:
    st.subheader("Salary & Hours Summary")
    
    df = pd.read_sql_query("SELECT * FROM timecards", conn)
    
    if not df.empty:
        df["Total Salary (SAR)"] = df["hours_worked"] * df["hourly_rate"]

summary_df = df.groupby("employee").agg(
    Total_Hours=("hours_worked", "sum"),
    Hourly_Rate=("hourly_rate", "first"),
    Total_Salary=("Total Salary (SAR)", "sum")
).reset_index()
        
c1, c2 = st.columns(2)
with c1:
st.metric("Total Hours (All Staff)", f"{summary_df['Total_Hours'].sum():.2f} hrs")
with c2:
st.metric("Total Payroll", f"${summary_df['Total_Salary'].sum():,.2f}")
        
        st.markdown("---")
        st.dataframe(
            summary_df,
            column_config={
                "employee": "Employee",
                "Total_Hours": st.column_config.NumberColumn("Total Hours", format="%.2f hrs"),
                "Hourly_Rate": st.column_config.NumberColumn("Rate ($)", format="$%.2f"),
                "Total_Salary": st.column_config.NumberColumn("Total Pay ($)", format="$%.2f")
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
    
    df_raw = pd.read_sql_query("SELECT * FROM timecards ORDER BY work_date DESC", conn)
    
    if not df_raw.empty:
        edited_df = st.data_editor(
            df_raw,
            num_rows="dynamic",
            key="timecard_editor",
            use_container_width=True
        )
        
        if st.button("Save Changes to Database"):
            c.execute("DELETE FROM timecards")
            for _, row in edited_df.iterrows():
                c.execute('''
                    INSERT INTO timecards (id, employee, hourly_rate, work_date, time_in, time_out, hours_worked)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (row['id'], row['employee'], row['hourly_rate'], row['work_date'], row['time_in'], row['time_out'], row['hours_worked']))
            conn.commit()
            st.success("Database updated successfully!")
            st.rerun()
    else:
        st.info("No records to display.")
