"""
Quick script to check what's using your serial ports
"""
import serial.tools.list_ports

print("\n" + "="*50)
print("  Available Serial Ports")
print("="*50 + "\n")

ports = serial.tools.list_ports.comports()

if not ports:
    print("❌ No serial ports found!")
else:
    for i, port in enumerate(ports):
        print(f"{i+1}. {port.device}")
        print(f"   Description: {port.description}")
        print(f"   Manufacturer: {port.manufacturer}")
        
        # Try to open
        try:
            s = serial.Serial(port.device, 115200, timeout=0.5)
            s.close()
            print(f"   Status: [OK] Available")
        except serial.SerialException as e:
            if "PermissionError" in str(e) or "Access is denied" in str(e):
                print(f"   Status: [IN USE] Locked by another program!")
            else:
                print(f"   Status: [ERROR] {e}")
        print()

print("="*50)
print("\nIf a port shows 'IN USE', close:")
print("  - Arduino Serial Monitor")
print("  - Arduino IDE")
print("  - Any other serial terminal programs")
print("="*50 + "\n")

