"""Restrained visual treatment for scientific exploration."""
import streamlit as st


def apply_theme():
    st.markdown("""<style>
    .stApp {background: #f5f7f8; color: #182f3b;}
    [data-testid="stSidebar"] {background: #e8eef0;}
    h1 {letter-spacing: -.045em; font-weight: 650;}
    h2,h3 {letter-spacing: -.025em;}
    [data-testid="stMetric"] {background: white; padding: 1.2rem;
      border: 1px solid #dce4e7; border-radius: 6px;}
    .block-container {max-width: 1500px; padding-top: 2.5rem;}
    </style>""", unsafe_allow_html=True)
