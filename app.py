import streamlit as st

st.title("🚀 My Interactive Streamlit Dashboard")
st.write("Welcome to your first live web application!")

# Create a text input box
user_name = st.text_input("What is your name?", "Developer")

# Create a slider for numbers
number = st.slider("Pick a percentage value:", 0, 100, 50)

# Create an interactive button
if st.button("Click Me to Calculate"):
    result = number * 10
    st.success(f"Hello {user_name}! Your calculated score is {result} points!")
