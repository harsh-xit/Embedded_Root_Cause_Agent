import sqlite3
import time
import os

DB_NAME = "motor_telemetry.db"

def clear_and_init_db():
    """Ensures the database exists and wipes old data to start fresh for the demo."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            epoch_ms INTEGER,
            current_ma REAL,
            pwm INTEGER
        )
    """)
    cursor.execute("DELETE FROM telemetry")
    conn.commit()
    conn.close()
    print("🧹 Database wiped and initialized for pure simulation track.")

def write_telemetry_frame(current_ma, pwm):
    """Inserts a single raw frame into the database head."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    epoch_ms = int(time.time() * 1000)
    cursor.execute(
        "INSERT INTO telemetry (epoch_ms, current_ma, pwm) VALUES (?, ?, ?)", 
        (epoch_ms, current_ma, pwm)
    )
    conn.commit()
    conn.close()

def run_simulation():
    clear_and_init_db()
    
    # Reset the local memory bank file so the audience sees it learn live
    if os.path.exists("fault_memory.json"):
        os.remove("fault_memory.json")
        print("🗑️ Reset local fault_memory.json cache.")

    print("\n🚀 Starting Live Simulation Loop...")
    
    # Phase 1: Establish Healthy Baseline Running Conditions
    print("\n🟢 PHASE 1: Running under healthy baseline conditions (4500mA @ 180 PWM)...")
    for _ in range(15):
        write_telemetry_frame(4510.0, 180) # minor sensor jitter simulated
        time.sleep(0.2)
        
    # Phase 2: First-Time Injection of an Undetermined Fault (Learning Curve Activated)
    # We will simulate an intermediate electrical failure profile: 3300mA at 200 PWM
    print("\n🟣 PHASE 2: Ingesting UNKNOWN Electrical Anomaly for the FIRST time...")
    print("👉 Watch Dashboard: It will declare NEW_ANOMALY and trigger Phi-3 Physics Deduction.")
    for _ in range(20):
        write_telemetry_frame(3300.0, 200)
        time.sleep(0.2)
        
    # Phase 3: Return to Nominal State to clear active error tracking flags
    print("\n🟢 PHASE 3: Clearing fault. System returns to nominal parameters...")
    for _ in range(15):
        write_telemetry_frame(4490.0, 180)
        time.sleep(0.2)
        
    # Phase 4: Re-inject the Exact Same Fault Profile (Memory Recall Activated)
    print("\n🔵 PHASE 4: Re-injecting the SAME Electrical Anomaly for the SECOND time...")
    print("👉 Watch Dashboard: The engine should instantly recognize the signature and match memory history!")
    for _ in range(20):
        write_telemetry_frame(3300.0, 200)
        time.sleep(0.2)

    print("\n🏁 Simulation completed successfully.")

if __name__ == "__main__":
    run_simulation()