import pandas as pd
import streamlit as st
import os
from PIL import Image

# ==========================================
# 4. TOP HEADER (LOGO IMAGE, TITLE & LOCK)
# ==========================================
col_logo, col_title, col_lock = st.columns([1.5, 4, 1])

with col_logo:
    # Try loading LOGO.png or logo.jpg
    logo_filename = None
    for file in ["LOGO.jpg", "logo.jpg", "LOGO.jpeg", "logo.png"]:
        if os.path.exists(file):
            logo_filename = file
            break

    if logo_filename:
        image = Image.open(logo_filename)
        st.image(image, use_container_width=True)
    else:
        st.warning("Logo file not found in repo")

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
