import streamlit as st
import config
from backend.config_updater import update_config_file
from components.system_monitor import render_system_monitor
import time
import os

st.set_page_config(page_title="Settings - IntelliClean", page_icon="⚙️", layout="wide")

st.markdown("""
<style>
.sec-hdr {
    font-size: 1.25rem;
    font-weight: 700;
    margin-top: 1.5rem;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 8px;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    padding-bottom: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# Hide sidebar and set top nav
st.markdown("""
<style>
/* Sidebar - Hide entirely */
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
section[data-testid="stSidebar"] { display: none !important; }
button[kind="header"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

from components.navigation import render_top_nav
render_top_nav()

st.markdown('<div class="sec-hdr">⚙️ <span>Global Configuration & Settings</span></div>', unsafe_allow_html=True)
st.markdown("Modify the core parameters of the AI Data Cleaner. Changes will automatically apply and refresh the application.")

tab1, tab2 = st.tabs(["🤖 AI & Processing", "🎨 UI & Theme"])

with tab1:
    with st.form("settings_form"):
        st.markdown("#### 🤖 AI & LLM Settings")
        base_url = st.text_input("LLM Base URL (LM Studio / API)", value=config.LLM_BASE_URL)
        model_name = st.text_input("Model Name", value=config.LLM_MODEL_NAME)
        
        c1, c2 = st.columns(2)
        with c1:
            temperature = st.slider("Temperature", 0.0, 1.0, float(config.LLM_TEMPERATURE), 0.05, 
                                    help="Low values (e.g. 0.1) are better for strict JSON data extraction tasks.")
        with c2:
            chunk_size = st.number_input("Batch Chunk Size", 5, 200, int(config.LLM_CHUNK_SIZE), 
                                         help="Number of rows processed per LLM call. Higher is faster but requires more VRAM.")
                                         
        st.markdown("#### 🧹 Cleaning Thresholds")
        c3, c4 = st.columns(2)
        with c3:
            fuzzy_thresh = st.slider("Fuzzy Match Threshold", 50, 100, int(config.FUZZY_MATCH_THRESHOLD),
                                     help="Lower means looser matches, higher means strictly exact text matches.")
        with c4:
            outlier_mult = st.slider("Outlier IQR Multiplier", 1.0, 5.0, float(config.OUTLIER_IQR_MULTIPLIER), 0.1,
                                     help="Threshold for statistical outlier detection.")
            
        submitted = st.form_submit_button("💾 Save Configuration", type="primary", use_container_width=True)
        
        if submitted:
            updates = {
                "LLM_BASE_URL": base_url,
                "LLM_MODEL_NAME": model_name,
                "LLM_TEMPERATURE": temperature,
                "LLM_CHUNK_SIZE": chunk_size,
                "FUZZY_MATCH_THRESHOLD": fuzzy_thresh,
                "OUTLIER_IQR_MULTIPLIER": outlier_mult
            }
            try:
                update_config_file(updates)
                st.success("✅ Configuration saved successfully! Reloading...")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to save config: {e}")

with tab2:
    st.markdown("#### 🎨 Streamlit Theme")
    st.info("Note: Changing the theme will rewrite `.streamlit/config.toml` and force a full app reload.")
    # Read current theme from config.toml if it exists
    toml_path = os.path.join(".streamlit", "config.toml")
    current_theme = "dark"
    if os.path.exists(toml_path):
        with open(toml_path, "r") as f:
            content = f.read()
            if 'base="light"' in content or "base='light'" in content:
                current_theme = "light"
                
    theme_choice = st.radio("Select Base Theme", ["Dark Mode (Default)", "Light Mode"], index=0 if current_theme == "dark" else 1)
    
    if st.button("Apply Theme", type="primary"):
        new_base = "dark" if "Dark" in theme_choice else "light"
        
        # Write to toml
        toml_content = f"""[theme]
base="{new_base}"
primaryColor="#8b5cf6"
"""
        if new_base == "dark":
            toml_content += """backgroundColor="#080b14"
secondaryBackgroundColor="#0f172a"
textColor="#e2e8f0"
"""
        else:
            # Light defaults
            toml_content += """backgroundColor="#ffffff"
secondaryBackgroundColor="#f1f5f9"
textColor="#0f172a"
"""
        os.makedirs(".streamlit", exist_ok=True)
        with open(toml_path, "w") as f:
            f.write(toml_content)
        st.success(f"✅ Theme updated to {new_base} mode. Streamlit will reload automatically.")
        time.sleep(1)
        st.rerun()

render_system_monitor()
