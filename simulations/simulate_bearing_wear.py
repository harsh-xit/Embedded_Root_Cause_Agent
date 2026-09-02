import sqlite3
import time

DB_NAME = "motor_telemetry.db"
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()
epoch_ms = int(time.time() * 1000)

for i in range(15):
    timestamp = epoch_ms + (i * 200)
    # Scenario 1 Parameters: 4980mA, 180 PWM
    cursor.execute("INSERT INTO telemetry (epoch_ms, current_ma, pwm) VALUES (?, ?, ?)", (timestamp, 4980.0, 180))

conn.commit()
time.sleep(0.3)
conn.close()