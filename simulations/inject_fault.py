import sqlite3
import time

DB_NAME = "motor_telemetry.db"

def inject_mock_fault(current_ma, pwm):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    epoch_ms = int(time.time() * 1000)
    
    # Insert 10 consecutive rows to easily clear the 5-cycle UI stability counter
    for i in range(10):
        cursor.execute(
            "INSERT INTO telemetry (epoch_ms, current_ma, pwm) VALUES (?, ?, ?)", 
            (epoch_ms + (i * 100), current_ma, pwm)
        )
    conn.commit()
    conn.close()
    print(f"Successfully injected telemetry: {current_ma}mA, PWM: {pwm}")

# --- UNCOMMENT THE SCENARIO YOU WANT TO SIMULATE FOR YOUR DEMO ---

# Scenario A: ACS712 Sensor Drift (Current reads an impossible 9000mA while motor operates)
inject_mock_fault(9500.0, 180)

# Scenario B: Motor Driver (L298N) Failure (PWM is maxed out at 255, but current is 0mA)
# inject_mock_fault(5.0, 255)

# Scenario C: Voltage Sag During Startup (Erratic low current during a sudden high PWM draw)
# inject_mock_fault(1200.0, 240)