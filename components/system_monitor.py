import streamlit as st
import psutil

@st.fragment(run_every="2s")
def render_system_monitor():
    """
    Renders a floating, transparent system resource monitor in the bottom-left corner.
    Works on both Windows and Linux environments using psutil.
    """
    try:
        # Fetch CPU and RAM usage
        # Use interval=0.1 to get an accurate CPU reading immediately
        cpu_usage = psutil.cpu_percent(interval=0.1)
        ram_info = psutil.virtual_memory()
        ram_usage = ram_info.percent
        
        # Color coding logic
        cpu_color = "#4ade80" if cpu_usage < 60 else "#facc15" if cpu_usage < 85 else "#f87171"
        ram_color = "#4ade80" if ram_usage < 60 else "#facc15" if ram_usage < 85 else "#f87171"
        
        # Inject floating HTML/CSS
        html_code = f"""
        <div style="
            position: fixed; 
            bottom: 20px; 
            left: 20px; 
            background: rgba(15, 23, 42, 0.75); 
            backdrop-filter: blur(12px); 
            -webkit-backdrop-filter: blur(12px);
            padding: 10px 15px; 
            border-radius: 10px; 
            border: 1px solid rgba(255, 255, 255, 0.1); 
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            color: #e2e8f0; 
            font-size: 0.85rem; 
            z-index: 999999; 
            display: flex; 
            gap: 15px; 
            font-family: monospace;
            pointer-events: none; /* Let clicks pass through if it covers anything */
        ">
            <div style="display: flex; flex-direction: column; align-items: center;">
                <span style="font-size: 0.65rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px;">CPU</span>
                <span style="font-weight: bold; color: {cpu_color};">{cpu_usage:.1f}%</span>
            </div>
            <div style="width: 1px; background: rgba(255,255,255,0.1);"></div>
            <div style="display: flex; flex-direction: column; align-items: center;">
                <span style="font-size: 0.65rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px;">RAM</span>
                <span style="font-weight: bold; color: {ram_color};">{ram_usage:.1f}%</span>
            </div>
        </div>
        """
        st.markdown(html_code, unsafe_allow_html=True)
    except Exception as e:
        # Silently fail or log if psutil has issues (e.g., permissions)
        pass
