import serial
import sqlite3
import time

# --- CONFIGURATION ---
SERIAL_PORT = "COM3"  # Adjust to your active ESP32 port (e.g., /dev/ttyUSB0 on Linux)
BAUD_RATE = 115200
DB_NAME = "motor_telemetry.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Create schema matching the streamlined hardware metrics
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            epoch_ms INTEGER,
            current_ma REAL,
            pwm INTEGER
        )
    """)
    conn.commit()
    conn.close()

def main():
    init_db()
    print(f"[*] Ingestion Engine Active. Listening on {SERIAL_PORT}...")
    
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        ser.flushInput()
    except Exception as e:
        print(f"[-] Serial Connection Error: {e}")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    while True:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                
                # Check for our data header protocol token
                if line.startswith("DATA_FRAME"):
                    parts = line.split(",")
                    if len(parts) == 4:  # HEADER, epoch_ms, current_ma, pwm
                        _, epoch_ms, current_ma, pwm = parts
                        
                        # Convert types
                        epoch_ms = int(epoch_ms)
                        current_ma = float(current_ma)
                        pwm = int(pwm)
                        
                        # Write straight to SQLite
                        cursor.execute("""
                            INSERT INTO telemetry (epoch_ms, current_ma, pwm) 
                            VALUES (?, ?, ?)
                        """, (epoch_ms, current_ma, pwm))
                        conn.commit()
                        
                        print(f"[+] Stored Frame -> MS: {epoch_ms} | mA: {current_ma} | PWM: {pwm}")
        except KeyboardInterrupt:
            print("\n[*] Shutting down Ingestion Engine...")
            break
        except Exception as e:
            print(f"[-] Data parsing variance: {e}")
            continue

    conn.close()
    ser.close()

if __name__ == "__main__":
    main()