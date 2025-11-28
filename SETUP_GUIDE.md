# Quick Setup Guide 🚀

## ✅ Recommended: Hybrid Approach (Easiest!)

Use **Cursor** for coding and visualization, **Arduino IDE** just for uploading.

---

## Step-by-Step Setup

### 1️⃣ Install Arduino IDE & ESP32 Support

1. **Download Arduino IDE**: https://www.arduino.cc/en/software
2. **Install** it (accept defaults)
3. **Open Arduino IDE**
4. Go to **File → Preferences**
5. In "Additional Board Manager URLs" field, paste:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
6. Click **OK**
7. Go to **Tools → Board → Boards Manager**
8. Search: **"ESP32"**
9. Install: **"esp32 by Espressif Systems"** (takes 3-5 minutes)
10. Done! Keep Arduino IDE open for now.

### 2️⃣ Configure ESP32S3 Board

1. Connect your ESP32S3 via USB
2. In Arduino IDE, go to **Tools → Board → esp32**
3. Select: **"ESP32S3 Dev Module"** (or your specific variant)
4. Go to **Tools → Port**
5. Select your COM port (e.g., COM3, COM5)
   - On Windows: Looks like "COM3" or "COM5"
   - On Mac: Looks like "/dev/cu.usbserial-*"
   - On Linux: Looks like "/dev/ttyUSB0"

### 3️⃣ Upload Your Code

1. In Arduino IDE, click **File → Open**
2. Navigate to your project folder
3. Open: **`emg_function.ino`**
4. Click the **Upload** button (→ arrow icon at top)
5. Wait for "Done uploading" message
6. **That's it!** You can minimize Arduino IDE now

### 4️⃣ Install Python Dependencies

Open **Terminal in Cursor** (`` Ctrl+` ``) or Command Prompt:

```bash
# Navigate to your project folder
cd "G:\CPE4B - 1st SEMESTER\DSP\project\emg_function"

# Install Python packages (use python -m pip if pip doesn't work)
python -m pip install -r requirements.txt
```

### 5️⃣ Run the Beautiful Visualizer! 🎨

**Option A** - Double-click:
```
run_visualizer.bat
```

**Option B** - Command line:
```bash
python emg_visualizer.py
```

The script will:
- Show you available COM ports
- Ask you to select one
- Display beautiful real-time graphs!

---

## 🎨 What You'll See

```
╔═══════════════════════════════════════════╗
║  EMG Signal Monitor - Real-Time Display   ║
╠═══════════════════════════════════════════╣
║                                           ║
║  📈 EMG Envelope with Thresholds          ║
║     - Blue line: Main signal              ║
║     - Green line: RMS (smooth)            ║
║     - Yellow dash: Relaxed threshold      ║
║     - Red dash: Stressed threshold        ║
║                                           ║
║  📊 Muscle State Indicator                ║
║     🟢 Relaxed  🟠 Normal  🔴 Stressed    ║
║                                           ║
║  📋 Live Statistics                       ║
║     Current, Average, Max, Min values     ║
╚═══════════════════════════════════════════╝
```

**This looks 100x better than Serial Plotter!**

---

## 🔄 Your Workflow

1. **Edit code** in Cursor (nice editor, AI help, etc.)
2. **Save** your changes
3. **Upload** via Arduino IDE (click Upload button)
4. **Close** Arduino Serial Monitor if open
5. **Run** Python visualizer: `python emg_visualizer.py`
6. **Demo** to your professor! 🎓

---

## ❓ Alternative: ESP-IDF Extension

You mentioned ESP-IDF extension is available in Cursor. **However:**

- ❌ Your code is written for **Arduino framework**
- ❌ ESP-IDF uses different APIs (would need complete rewrite)
- ❌ Much more complex setup
- ❌ Overkill for this project

**Verdict:** Just use Arduino IDE for uploading. It's simpler!

---

## 🐛 Troubleshooting

### ESP32S3 Not Detected

1. **Install drivers:**
   - Most ESP32S3 boards use CH340 or CP210x
   - Download from: http://www.wch-ic.com/downloads/CH341SER_EXE.html (CH340)
   - Or: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers (CP210x)

2. **Try different USB cable** (must be data cable, not charge-only)

3. **Hold BOOT button** while plugging in USB (some boards need this)

4. **Check Device Manager** (Windows):
   - Look for "Ports (COM & LPT)"
   - Should show "USB-SERIAL CH340" or similar

### Python Visualizer Won't Connect

**Most Common Issue:** Arduino Serial Monitor is still open!
- ✅ Close Arduino Serial Monitor
- ✅ Only one program can use serial port at a time

**Check COM port:**
```bash
python emg_visualizer.py
# It will show available ports - select the right one
```

### Upload Failed

1. **Check board selection:** Must be ESP32S3 variant
2. **Check port:** Tools → Port must show your device
3. **Try slower upload speed:** Tools → Upload Speed → 115200
4. **Hold BOOT button** during upload

---

## 💡 Pro Tips

1. **Keep Arduino IDE minimized** - you only need it for uploading
2. **Edit in Cursor** - better editor, AI assistance
3. **Use Python visualizer for demos** - looks professional!
4. **Take screenshots** of Python graphs for your report
5. **Adjust thresholds** in code if too sensitive

---

## 📝 Quick Command Reference

```bash
# Install Python dependencies (once)
pip install -r requirements.txt

# Run visualizer (every time you want to view signals)
python emg_visualizer.py

# Or just double-click
run_visualizer.bat
```

---

## 🎯 Final Notes

**The beauty of this project is the Python visualizer** - that's what makes it stand out! 

The Arduino IDE is just a tool to upload code. You could even:
- Upload once in the lab
- Then demo at home with just the Python visualizer
- Your professor sees professional graphs, not basic Serial Plotter

**You're all set!** Any questions, check the troubleshooting section above. 🚀
