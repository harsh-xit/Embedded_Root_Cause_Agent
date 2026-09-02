## System Architecture Block Diagram
+----------------------------------------+
|      Edge User Device                  |
+----------------------------------------+
                    |
                    | (Writes Telemetry)
                    v
       +-------------------------+
       |   motor_telemetry.db    | <-- [Sidebar Simulation Scripts, for Demo Running]
       +-------------------------+     
                    |
                    | (Reads Head Data via .iloc[-1])
                    v
       +-------------------------+
       |         app.py          |
       |   (Streamlit UI Loop)   |
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
                    |  (Phi-3 LLM Core)  |
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
