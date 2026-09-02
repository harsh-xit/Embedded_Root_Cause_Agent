import streamlit as st
import sqlite3
import pandas as pd
import time
from feature_engine import unsupervised_anomaly_detector, generate_local_ai_explanation 

DB_NAME = "motor_telemetry.db"

st.set_page_config(page_title="ERCA Local AI Diagnostics", layout="wide")
st.title("🤖 ERCA Dashboard")

import subprocess
import os

# --- ENTERPRISE SIDEBAR SIMULATION CONTROLLER ---
st.sidebar.title("🎮 ERCA Environment Controller")
st.sidebar.markdown("Use this panel to inject complex ML-track environments via automated simulation background scripts.")

st.sidebar.subheader("Available Test Suites")

# Scenario 1 Button Trigger
if st.sidebar.button("📊 Inject Scenario 1: Gradual Bearing Wear", use_container_width=True):
    script_path = "simulate_bearing_wear.py"
    if os.path.exists(script_path):
        st.sidebar.info("Injecting Phase 1...")
        # Run the script asynchronously in the background so it doesn't lock up your dashboard UI
        subprocess.Popen(["python", script_path])
        st.sidebar.success("🚀 Bearing wear environment loaded!")
    else:
        st.sidebar.error(f"Missing script: {script_path}")

# Scenario 2 Button Trigger
if st.sidebar.button("⚡ Inject Scenario 2: Voltage Rail Sag", use_container_width=True):
    script_path = "simulate_voltage_sag.py"
    if os.path.exists(script_path):
        st.sidebar.info("Injecting Phase 2...")
        subprocess.Popen(["python", script_path])
        st.sidebar.success("🚀 Voltage sag environment loaded!")
    else:
        st.sidebar.error(f"Missing script: {script_path}")

# Scenario 3 Button Trigger
if st.sidebar.button("🚨 Inject Scenario 3: ACS712 Sensor Drift", use_container_width=True):
    script_path = "simulate_sensor_drift.py"
    if os.path.exists(script_path):
        st.sidebar.info("Injecting Phase 3...")
        subprocess.Popen(["python", script_path])
        st.sidebar.success("🚀 Sensor calibration fault loaded!")
    else:
        st.sidebar.error(f"Missing script: {script_path}")

st.sidebar.markdown("---")

# Quick Memory Purge option for resetting during consecutive presentation runs
if st.sidebar.button("🗑️ Reset ML Memory Cache (JSON)", use_container_width=True):
    if os.path.exists("fault_memory.json"):
        os.remove("fault_memory.json")
        st.sidebar.success("Wiped historical memory bank. Ready for fresh learning!")
    else:
        st.sidebar.warning("Memory cache is already clean.")

diagnostic_banner = st.empty()
ai_explanation_box = st.empty()

current_widget = st.empty()
pwm_widget = st.empty()

st.subheader("Live Electrical Signal Analysis")
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.write("**Current Consumption (mA)**")
    current_chart = st.empty()

with chart_col2:
    st.write("**Control Logic Input (PWM)**")
    pwm_chart = st.empty()

def fetch_telemetry_data():
    try:
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query("SELECT epoch_ms, current_ma, pwm FROM telemetry ORDER BY id DESC LIMIT 100", conn)
        conn.close()
        return df.iloc[::-1]
    except Exception:
        return pd.DataFrame()

# Track the last state so we only query the local LLM when a state change happens
last_logged_state = None

if 'last_confirmed_state' not in st.session_state:
    st.session_state.last_confirmed_state = "HEALTHY_OPERATION"
if 'pending_state' not in st.session_state:
    st.session_state.pending_state = "HEALTHY_OPERATION"
if 'stability_counter' not in st.session_state:
    st.session_state.stability_counter = 0

# Initialize a fallback timestamp before the while True loop starts
if 'last_received_time' not in st.session_state:
    st.session_state.last_received_time = time.time()

# Define your maximum allowed silence threshold (in seconds)
TIMEOUT_THRESHOLD = 5.0

while True:
    # 1. FETCH LIVE TELEMETRY FROM THE DATABASE
    telemetry_df = fetch_telemetry_data()
    
    # Flag to determine if we should evaluate for timeouts
    data_is_flowing = False
    
    if not telemetry_df.empty:
        # Extract the absolute latest current and PWM values
        current_ma = float(telemetry_df['current_ma'].iloc[-1])
        pwm_val = int(telemetry_df['pwm'].iloc[-1])
        
        # Update metrics widgets on screen
        current_widget.metric("Live Current", f"{current_ma} mA")
        pwm_widget.metric("Live PWM Control", f"{pwm_val} / 255")
        
        # Update live rolling line charts
        current_chart.line_chart(telemetry_df.set_index('epoch_ms')['current_ma'])
        pwm_chart.line_chart(telemetry_df.set_index('epoch_ms')['pwm'])
        
        # 2. RUN THE UNSUPERVISED ANOMALY DETECTOR ENGINE
        raw_predicted_state = unsupervised_anomaly_detector(current_ma, pwm_val)
        
        # Check if the hardware data is changing or if it's matching a static simulation row
        # This update prevents the background scripts from immediately timing out
        st.session_state.last_received_time = time.time()
        data_is_flowing = True
        
        # 3. DEBOUNCE / STABILITY LAYER
        if raw_predicted_state == st.session_state.pending_state:
            st.session_state.stability_counter += 1
        else:
            st.session_state.pending_state = raw_predicted_state
            st.session_state.stability_counter = 0
            
        # Commit state change and query Phi-3 after 5 consecutive identical readings
        if st.session_state.stability_counter >= 5:
            if st.session_state.pending_state != st.session_state.last_confirmed_state:
                st.session_state.last_confirmed_state = st.session_state.pending_state
                
                with st.spinner("🤖 Local Phi-3 compiling stable diagnostics..."):
                    ai_narrative = generate_local_ai_explanation(st.session_state.last_confirmed_state, current_ma, pwm_val)
                    ai_explanation_box.info(ai_narrative)

        # 4. FLEXIBLE UI STYLE SELECTOR
        active_state = st.session_state.last_confirmed_state
        
        if "HEALTHY" in active_state:
            ui_status, ui_color = "SYSTEM NOMINAL", "#28A745"
        elif "STALL" in active_state:
            ui_status, ui_color = "CRITICAL FAULT: STALL DETECTED", "#FF4B4B"
        elif "OPEN_CIRCUIT" in active_state:
            ui_status, ui_color = "CRITICAL FAULT: OPEN CIRCUIT", "#FFA500"
        elif "ANOMALY" in active_state:
            metric_tag = active_state.replace("NEW_", "").replace("LEARNED_", "")
            if "NEW" in active_state:
                ui_status, ui_color = f"🚨 NEW FAULT SIGNATURE MAPPED ({metric_tag})", "#7B1FA2"
            else:
                ui_status, ui_color = f"🧠 HISTORICAL PATTERN MATCHED ({metric_tag})", "#00838F"
        else:
            ui_status, ui_color = "🔄 STABILIZING TELEMETRY...", "#6C757D"

    else:
        ui_status, ui_color = "⚠️ WAITING FOR HARDWARE DATA LINK...", "#6C757D"

    # 🚨 5. THE TIMEOUT INTERCEPTOR (With Adaptive State Bypass Protection)
    time_since_last_update = time.time() - st.session_state.last_received_time
    
    # CRITICAL FIX: Only trigger communication timeout if the system is supposed to be in
    # a healthy baseline state. If an anomaly is actively confirmed on screen, let the 
    # user read the AI's diagnostic explanation text instead of overwriting it!
    if time_since_last_update > TIMEOUT_THRESHOLD and "ANOMALY" not in st.session_state.last_confirmed_state:
        ui_status = "❌ TIMEOUT ERROR: UNABLE TO COMMUNICATE WITH USER DEVICE"
        ui_color = "#7F0000"  # Crimson warning
        ai_explanation_box.error(
            f"⚠️ **ERCA System Alert:** Telemetry sync lost for {round(time_since_last_update, 1)} seconds. "
            "The localized diagnostic core is unable to communicate with the edge user device."
        )

    # 6. RENDER THE DYNAMIC ALERT BANNER
    diagnostic_banner.markdown(f"""
    <div style="background-color:{ui_color}; padding:15px; border-radius:10px; color:white; margin-bottom:10px;">
        <h3 style="margin:0; color:white;">[ML Classifier Track] {ui_status}</h3>
    </div>
    """, unsafe_allow_html=True)
        
    time.sleep(0.1)