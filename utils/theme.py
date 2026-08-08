"""Theme utilities and CSS injection for Streamlit UI."""
from __future__ import annotations

import streamlit as st


THEME_VARS = {
    'bg': '#F7FAFC',
    'card': '#FFFFFF',
    'muted': '#6B7280',
    'primary': '#0B6E4F',
    'accent': '#0EA5A4',
    'danger': '#DC2626',
    'shadow': '0 4px 16px rgba(11, 110, 79, 0.08)',
    'radius': '10px',
    'font_family': "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial",
}


def inject_theme(custom: dict | None = None) -> None:
    """Inject CSS variables and base styles into Streamlit page.

    Call this once at app startup. Pass custom dict to override defaults.
    """
    vars = dict(THEME_VARS)
    if custom:
        vars.update(custom)

    css = f"""
    <style>
    :root {{
      --bg: {vars['bg']};
      --card: {vars['card']};
      --muted: {vars['muted']};
      --primary: {vars['primary']};
      --accent: {vars['accent']};
      --danger: {vars['danger']};
      --shadow: {vars['shadow']};
      --radius: {vars['radius']};
      --font-family: {vars['font_family']};
    }}

    /* Page background */
    .main .block-container {{
      padding-top: 1.5rem;
      padding-left: 2rem;
      padding-right: 2rem;
      background: var(--bg);
      font-family: var(--font-family);
    }}

    /* Dark theme overrides when .theme-dark is present on body */
    body.theme-dark .main .block-container {{
      --bg: #0f172a;
      --card: #0b1220;
      --muted: #9ca3af;
      --primary: #34d399;
      --accent: #38bdf8;
    }}

    /* Card */
    .dp-card {{
      background: var(--card);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 1rem;
      margin-bottom: 1rem;
    }}

    .dp-kpi {{
      padding: 1rem;
      border-radius: calc(var(--radius) - 2px);
      background: linear-gradient(180deg, rgba(255,255,255,0.6), var(--card));
      text-align: left;
    }}

    .dp-kpi .label {{
      color: var(--muted);
      font-size: 0.9rem;
      margin-bottom: 0.25rem;
    }}

    .dp-kpi .value {{
      color: var(--primary);
      font-size: 1.5rem;
      font-weight: 700;
    }}

    /* Buttons */
    .stButton>button {{
      border-radius: 8px;
      padding: 0.5rem 0.9rem;
      background-color: var(--primary);
      color: white;
      border: none;
    }}

    /* Small muted text */
    .dp-muted {{ color: var(--muted); font-size: 0.9rem; }}

    /* Dataframe tweaks */
    .stDataFrame table {{ border-radius: 8px; overflow: hidden; }}

    /* Responsive tweaks */
    @media (max-width: 768px) {{
      .main .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
