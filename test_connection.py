"""
Quick test to see which port has your ESP32S3
"""
import serial
import time

ports_to_test = ['COM3', 'COM5']

print("\n" + "="*50)
print("  Testing Ports for ESP32S3")
print("="*50 + "\n")

for port in ports_to_test:
    print(f"Testing {port}...")
    try:
        ser = serial.Serial(port, 115200, timeout=2)
        time.sleep(1)
        
        # Try to read some data
        if ser.in_waiting:
            data = ser.readline().decode('utf-8', errors='ignore').strip()
            if data:
                print(f"  [{port}] Receiving data: {data[:50]}")
                if "EMG" in data or "Envelope" in data or "Calibr" in data:
                    print(f"  >>> This is your ESP32S3! <<<")
            else:
                print(f"  [{port}] Port open but no data yet")
        else:
            print(f"  [{port}] Port open but waiting for data...")
        
        ser.close()
        print(f"  [{port}] Status: OK (available)\n")
        
    except serial.SerialException as e:
        if "PermissionError" in str(e) or "Access is denied" in str(e):
            print(f"  [{port}] Status: IN USE (close Arduino IDE!)\n")
        else:
            print(f"  [{port}] Status: Not available ({e})\n")

print("="*50)
print("\nTo fix 'IN USE' error:")
print("  1. Close Arduino IDE completely")
print("  2. Wait 3 seconds")
print("  3. Run: python emg_visualizer.py")
print("="*50 + "\n")

