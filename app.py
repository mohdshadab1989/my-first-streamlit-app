import streamlit as st
import pandas as pd

# Page setup for mobile responsiveness
st.set_page_config(page_title="Employee Hours & Pay", layout="centered")

st.title("⏱️ Employee Hours & Salary Report")
st.write("Track working hours and calculate salaries.")

# --- Sample Data / Input ---
# Sample employee dataset (In production, this can be linked to a database or CSV)
data = {
    "Employee": ["Alex Johnson", "Sam Lee", "Priya Patel", "Jordan Smith"],
    "Role": ["Developer", "Designer", "Manager", "Support Specialist"],
    "Hours Worked": [160, 145, 175, 150],  # total hours in a month/period
    "Hourly Rate ($)": [35.0, 30.0, 45.0, 25.0]
}

df = pd.DataFrame(data)

# --- Overtime Settings Sidebar ---
st.sidebar.header("Settings")
overtime_threshold = st.sidebar.number_input("Standard Hours Limit", value=160, step=5)
overtime_multiplier = st.sidebar.slider("Overtime Rate Multiplier", 1.0, 2.0, 1.5, 0.1)

# --- Salary Calculation Logic ---
def calculate_salary(row):
    hours = row["Hours Worked"]
    rate = row["Hourly Rate ($)"]
    
    if hours <= overtime_threshold:
        regular_pay = hours * rate
        overtime_pay = 0.0
    else:
        regular_pay = overtime_threshold * rate
        overtime_hours = hours - overtime_threshold
        overtime_pay = overtime_hours * (rate * overtime_multiplier)
        
    total_pay = regular_pay + overtime_pay
    return pd.Series([regular_pay, overtime_pay, total_pay])

df[["Regular Pay ($)", "Overtime Pay ($)", "Total Salary ($)"]] = df.apply(calculate_salary, axis=1)

# --- Summary Metrics ---
col1, col2 = st.columns(2)
with col1:
    st.metric("Total Hours Logged", f"{df['Hours Worked'].sum()} hrs")
with col2:
    st.metric("Total Payroll", f"${df['Total Salary ($)'].sum():,.2f}")

st.markdown("---")

# --- Employee Filter & Individual View ---
st.subheader("📋 Detailed Employee Breakdown")

selected_employee = st.selectbox("Select Employee to view:", ["All"] + list(df["Employee"]))

if selected_employee != "All":
    emp_data = df[df["Employee"] == selected_employee].iloc[0]
    
    st.info(f"**{emp_data['Employee']}** — {emp_data['Role']}")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Hours Worked", f"{emp_data['Hours Worked']} hrs")
    c2.metric("Hourly Rate", f"${emp_data['Hourly Rate ($)']:.2f}")
    c3.metric("Total Pay", f"${emp_data['Total Salary ($)']:.2f}")
    
    st.caption(f"Includes ${emp_data['Regular Pay ($)']:.2f} regular pay + ${emp_data['Overtime Pay ($)']:.2f} overtime.")
else:
    # Full Table View
    st.dataframe(
        df[["Employee", "Role", "Hours Worked", "Hourly Rate ($)", "Total Salary ($)"]],
        use_container_width=True,
        hide_index=True
    )

st.markdown("---")

# --- Interactive Salary Calculator for Quick Checks ---
st.subheader("🧮 Quick Pay Calculator")

calc_hours = st.number_input("Enter Hours Worked:", min_value=0.0, value=40.0, step=1.0)
calc_rate = st.number_input("Enter Hourly Rate ($):", min_value=0.0, value=25.0, step=0.50)

if calc_hours > overtime_threshold:
    reg_hours = overtime_threshold
    ot_hours = calc_hours - overtime_threshold
else:
    reg_hours = calc_hours
    ot_hours = 0.0

total_est = (reg_hours * calc_rate) + (ot_hours * calc_rate * overtime_multiplier)

st.success(f"**Calculated Salary:** ${total_est:,.2f}")
