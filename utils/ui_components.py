"""Reusable UI components for Streamlit pages."""
from __future__ import annotations

import streamlit as st
from typing import Optional


def header(app_title: str, subtitle: Optional[str] = None):
    cols = st.columns([1, 6, 1])
    with cols[1]:
        st.markdown(f"<div class='dp-card' style='padding:12px'><h1 style='margin:0'>{app_title}</h1>{('<div class=dp-muted>'+subtitle+'</div>') if subtitle else ''}</div>", unsafe_allow_html=True)


def summary_card(title: str, value: str, help_text: Optional[str] = None):
    """Render a compact summary card."""
    st.markdown(f"<div class='dp-card dp-kpi'><div class='label'>{title}</div><div class='value'>{value}</div>{('<div class=dp-muted>'+help_text+'</div>') if help_text else ''}</div>", unsafe_allow_html=True)


def form_section(title: str):
    st.subheader(title)


def info_tooltip(text: str):
    st.info(text)
