import streamlit as st
import config
from backend.config_updater import update_config_file
import time

# Ensure backward compatibility if dialog is not available
if hasattr(st, "dialog"):
    dialog_decorator = st.dialog
elif hasattr(st, "experimental_dialog"):
    dialog_decorator = st.experimental_dialog
else:
    # Fallback mock decorator if on very old Streamlit
    def dialog_decorator(title):
        def decorator(func):
            return func
        return decorator

@dialog_decorator("⚙️ Global Configuration")
def render_settings_modal():
    st.markdown("Modify the core parameters of the AI Data Cleaner. Changes will automatically apply and refresh the application.")
    
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
