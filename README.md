# ERCA: Edge-Gateway Real-Time Diagnostic Engine

A hybrid edge-gateway telemetry system combining deterministic physical limit monitoring with localized SLM-assisted anomaly diagnosis.

---

## Overview

Industrial telemetry streams often face a trade-off: traditional threshold monitoring is fast but rigid, while cloud-based AI introduces latency and external network dependencies. 

**ERCA** resolves this trade-off using a **Thick Edge Gateway** design:
1. **Sensor Node Layer:** Continuously samples operating parameters (Current in mA, PWM drive state) in real time and streams structured telemetry over Serial/UART.
2. **Deterministic Triage (`feature_engine.py`):** Instantly catches critical hard-boundary conditions—such as mechanical stalls and open circuits—without computational overhead.
3. **Adaptive ML Track (`erca_engine.py`):** Quantizes unmapped signal deviations into discrete tracking vectors and prompts a localized, zero-temperature Small Language Model (SLM) to deduce physical root causes (e.g., mechanical load changes, supply voltage sags).
4. **Knowledge Persistence (`fault_memory.json`):** Dynamic caching layer that stores novel diagnostics locally to enable sub-millisecond recall on recurring anomalies.

## System Architecture & Data Flow

+----------------------------------------+
|           Edge Sensor Rig              |
+----------------------------------------+
                    |
                    | (Writes Telemetry)
                    v
       +-------------------------+
       |   motor_telemetry.db    | <-- [Simulation Test Scripts]
       +-------------------------+     
                    |
                    | (Reads Head Data via .iloc[-1])
                    v
       +-------------------------+
       |         app.py          |
       |   (Monitoring UI Loop)  |
       +-------------------------+
                    |
                    | (Passes Current & PWM)
                    v
       +-------------------------+
       |    feature_engine.py    |
       | (Deterministic Bounds)  |
       +-------------------------+
                    |
          +---------+---------+
          |                   |
    [Within Rules]     [Out of Bounds / Unmapped]
          |                   |
          v                   v
+------------------+  +------------------+
|  HEALTHY / STALL |  |  ADAPTIVE TRACK  |
|  (Direct Alert)  |  |  (Assigns Tag)   |
+------------------+  +------------------+
                              |
                              v
                    +--------------------+
                    |   erca_engine.py   |
                    |     (SLM Core)     |
                    +--------------------+
                              |
                   +----------+----------+
                   |                     |
            [Knowledge Read]      [Knowledge Write]
                   |                     |
                   v                     v
            +----------------------------------+
            |        fault_memory.json         |
            |      (Local Knowledge Cache)     |
            +----------------------------------+
```

---

## Repository Structure

ERCA_Project/
├── backend/
│   ├── erca_engine.py          # Local SLM inference pipeline & prompt engineering
│   └── feature_engine.py       # Deterministic rules, vector quantization & JSON cache
├── dashboard/
│   └── app.py                  # Streamlit real-time monitoring interface
├── docs/
│   └── architecture_block_diagram.md
├── firmware/
│   └── firmware_ERCA.ino       # Embedded ADC acquisition & UART telemetry streaming
├── simulations/
│   ├── inject_fault.py          # Telemetry fault injection harness
│   ├── simulate_bearing_wear.py # Mechanical friction load simulation
│   ├── simulate_learning_cycle.py
│   ├── simulate_sensor_drift.py
│   └── simulate_voltage_sag.py  # Power rail droop simulation
├── .gitignore
├── README.md
└── requirements.txt

---

## Getting Started

### Prerequisites
* Python 3.10+
* Local SLM runtime environment

### Installation
1. Clone the repository:
   
   git clone [https://github.com/](https://github.com/)<your-username>/<your-repo-name>.git
   cd ERCA_Project
   

2. Set up a virtual environment and install dependencies:
   
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate

   pip install -r requirements.txt
   

### Running the System
1. **Launch the Gateway Dashboard:**
   
   streamlit run dashboard/app.py
   

2. **Simulate Telemetry Ingestion (Test Mode):**
   In a separate terminal, trigger a failure simulation profile:
  
   python simulations/simulate_bearing_wear.py
   
   The engine detects the unmapped state, triggers local inference, and commits the explanation to `fault_memory.json`. Re-running the simulation validates immediate sub-millisecond retrieval from the local memory cache.