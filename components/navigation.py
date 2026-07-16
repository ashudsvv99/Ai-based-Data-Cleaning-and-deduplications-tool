import streamlit as st
import os
import requests

@st.cache_data(ttl=5, show_spinner=False)
def check_llm_status(url: str) -> bool:
    try:
        res = requests.get(f"{url}/models", timeout=0.5)
        return res.status_code == 200
    except Exception:
        return False

def render_top_nav():
    """Renders a unified top navigation bar for all pages."""
    lm_url = os.environ.get("LM_STUDIO_URL", "http://localhost:1234/v1")
    os.environ["LM_STUDIO_URL"] = lm_url

    # Check LLM status
    if check_llm_status(lm_url):
        indicator_html = """
        <div style='display: flex; align-items: center; gap: 6px; font-size: 0.8rem; background: rgba(0,0,0,0.2); padding: 8px 14px; border-radius: 20px; border: 1px solid rgba(16, 185, 129, 0.3);'>
            <div style='width:8px;height:8px;border-radius:50%;background:#10b981;box-shadow:0 0 8px #10b981'></div>
            <span style='color:#10b981; font-weight: 600;'>LLM Online</span>
        </div>
        """
    else:
        indicator_html = """
        <div style='display: flex; align-items: center; gap: 6px; font-size: 0.8rem; background: rgba(0,0,0,0.2); padding: 8px 14px; border-radius: 20px; border: 1px solid rgba(239, 68, 68, 0.3);'>
            <div style='width:8px;height:8px;border-radius:50%;background:#ef4444;box-shadow:0 0 8px #ef4444'></div>
            <span style='color:#ef4444; font-weight: 600;'>LLM Offline</span>
        </div>
        """

    # Custom CSS for page links
    st.markdown("""
    <style>
    /* Make page links look like buttons */
    [data-testid="stPageLink-NavLink"] {
        background-color: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 8px;
        padding: 0.5rem 1rem;
        transition: all 0.2s;
    }
    [data-testid="stPageLink-NavLink"]:hover {
        background-color: rgba(139,92,246,0.15);
        border-color: rgba(139,92,246,0.4);
    }
    [data-testid="stPageLink-NavLink"] p {
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

    col_nav1, col_nav2, col_nav3, col_spacer, col_theme, col_status = st.columns([1.2, 1.5, 1.4, 3.4, 1, 1.5])
    
    with col_nav1:
        st.page_link("app.py", label="Home", icon="🏠")
    with col_nav2:
        st.page_link("pages/Live_Database.py", label="Live DB", icon="🗄️")
    with col_nav3:
        st.page_link("pages/Settings.py", label="Settings", icon="⚙️")

    with col_theme:
        theme = st.session_state.get('theme', 'dark')
        if st.button("☀️ Light" if theme == 'dark' else "🌙 Dark", use_container_width=True):
            st.session_state.theme = 'light' if theme == 'dark' else 'dark'
            st.rerun()

    with col_status:
        st.markdown(f"<div style='display:flex; justify-content:flex-end; padding-top:2px'>{indicator_html}</div>", unsafe_allow_html=True)
    
    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
