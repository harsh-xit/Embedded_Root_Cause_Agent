import sqlite3
import time

DB_NAME = "motor_telemetry.db"
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()
epoch_ms = int(time.time() * 1000)

for i in range(15):
    timestamp = epoch_ms + (i * 200)
    # Scenario 2 Parameters: 3300mA, 200 PWM
    cursor.execute("INSERT INTO telemetry (epoch_ms, current_ma, pwm) VALUES (?, ?, ?)", (timestamp, 3300.0, 200))

conn.commit()
time.sleep(0.3)
conn.close()