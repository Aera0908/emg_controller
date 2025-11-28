# EMG Signal Monitor 📊

Real-time EMG (Electromyography) signal visualization and monitoring system for ESP32S3.

![Project Status](https://img.shields.io/badge/status-active-success.svg)
![Platform](https://img.shields.io/badge/platform-ESP32S3-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 🎯 Features

- **Real-time Signal Processing**: 500 Hz sampling rate with advanced filtering
- **Automatic Calibration**: Adaptive threshold detection based on baseline signal
- **Multiple Visualization Modes**: 
  - Arduino Serial Plotter
  - **Beautiful Python GUI** with real-time graphs (2 versions available)
- **Binary State Detection**: Simple ON/OFF muscle activation detection
- **Professional Output**: RMS values, envelope detection, and adaptive threshold indicator
- **Clean & Documented Code**: Well-organized, easy to understand and modify

## 📋 Hardware Requirements

- ESP32S3 Development Board (XIAO ESP32S3 or similar)
- EMG Sensor Module
- USB Cable
- Computer with USB port

## 🛠️ Software Setup

### Option 1: Using Cursor + Arduino IDE (Recommended) ⭐

**Why this combo?** Edit code in Cursor (better editor), upload via Arduino IDE (simple & reliable).

#### Step 1: Install Arduino IDE & ESP32 Support

1. **Download Arduino IDE**: https://www.arduino.cc/en/software
2. **Install** and open it
3. Go to **File → Preferences**
4. Add to "Additional Board Manager URLs": 
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
5. Go to **Tools → Board → Boards Manager**
6. Search "ESP32" and install **"esp32 by Espressif Systems"**

#### Step 2: Configure and Upload

1. **Connect** ESP32S3 via USB
2. In Arduino IDE:
   - **File → Open** → Select `emg_function.ino`
   - **Tools → Board → esp32** → Select **ESP32S3 Dev Module**
   - **Tools → Port** → Select your COM port
3. Click **Upload** button (→)
4. Wait for "Done uploading"

#### Step 3: Edit Code in Cursor

- Open project folder in Cursor for editing
- Make changes to `emg_function.ino`
- Save and go back to Arduino IDE to upload
- Use Cursor's AI features for code improvements!

### Option 2: Using Arduino IDE

1. Open `emg_function.ino` in Arduino IDE
2. Select board: **ESP32S3 Dev Module**
3. Select correct COM port
4. Click **Upload**
5. Open **Tools → Serial Plotter** to visualize

## 🎨 Python Visualization (Recommended)

### Setup

1. **Install Python** (3.8 or higher)
   - Download from: https://www.python.org/downloads/
   - Make sure to check "Add Python to PATH" during installation

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

   Or install manually:
   ```bash
   pip install pyserial matplotlib numpy
   ```

### Running the Visualizer

1. **Upload code to ESP32S3** (using PlatformIO or Arduino IDE)

2. **Close Serial Monitor** (if open) - Can't have two programs using same port

3. **Run Python Visualizer**:
   
   **Main Visualizer** (with detailed statistics):
   ```bash
   python emg_visualizer.py
   ```
   
   **Simple Visualizer** (cleaner, focused view):
   ```bash
   python emg_visualizer_simple.py
   ```
   
   Or use the batch files:
   - `run_visualizer.bat` (Windows)
   - `run_simple_visualizer.bat` (Windows)

4. **Select COM Port** when prompted

5. **Keep muscle relaxed** for 10 seconds during calibration (one-time only, no recalibration)

6. **Flex your muscle** to see ON/OFF detection!

### What You'll See

**Main Visualizer** displays:
- **Top Panel**: Real-time EMG signals with threshold
  - Blue line: EMG Envelope (main signal)
  - Cyan line: RMS Value (smoothed)
  - Red dashed: Activation threshold
- **Bottom Left**: ON/OFF state indicator (green bar = OFF, red bar = ON)
- **Bottom Right**: Live statistics and metrics

**Simple Visualizer** displays:
- **Top Panel**: EMG Envelope with activation threshold
- **Bottom Left**: RMS values
- **Bottom Right**: ON/OFF state indicator

## 📊 Serial Plotter Format

If using Arduino Serial Plotter, you'll see 4 channels:
1. **Envelope** - Main signal amplitude (EMG envelope)
2. **RMS** - Root mean square for smooth visualization
3. **Threshold** - Activation threshold line (appears after calibration)
4. **State** - Visual state indicator (0 = OFF, >0 = ON)

## 🎛️ Configuration

### Adjust Activation Threshold

Edit in `emg_function.ino`:

```cpp
#define THRESHOLD_MULTIPLIER 3.0f  // Higher = less sensitive, Lower = more sensitive
```

The threshold is calculated as: `Threshold = Baseline_Mean + (THRESHOLD_MULTIPLIER × Baseline_StdDev)`

**Typical values:**
- `2.0` - Very sensitive (may have false positives)
- `3.0` - Balanced (default, recommended)
- `4.0` - Less sensitive (requires stronger contraction)

### Change Sampling Rate

```cpp
#define SAMPLE_RATE 500   // Hz (500 Hz recommended for EMG)
```

### Calibration Duration

```cpp
#define CALIBRATION_SECONDS 10  // seconds (10 seconds for stable baseline)
```

**Note**: Calibration happens **once** at startup. No automatic recalibration.

### Adjust Smoothing

```cpp
#define ENVELOPE_SMOOTH_FACTOR 0.15f  // Lower = smoother but slower response
```

## 🔧 Troubleshooting

### ESP32S3 Not Detected

1. Install CH340/CP210x USB drivers
2. Try different USB cable (data cable, not charge-only)
3. Hold BOOT button while connecting

### Python Visualizer Can't Connect

1. Close Arduino Serial Monitor/Plotter
2. Check COM port in Device Manager (Windows) or `ls /dev/tty*` (Mac/Linux)
3. Ensure pyserial is installed: `pip install pyserial`

### Signal Too Noisy

1. Check electrode placement
2. Ensure good skin contact
3. Clean skin with alcohol wipe
4. Adjust `THRESHOLD_MULTIPLIER` value (increase to reduce sensitivity)
5. Recalibrate by resetting the device

### Arduino Extension Not Working in Cursor

1. Make sure Arduino IDE is installed first
2. Set correct Arduino path in Cursor settings
3. Restart Cursor IDE after installation
4. Check Output panel for Arduino extension logs
5. Try: Ctrl+Shift+P → "Arduino: Initialize"

### Can't Find Arduino Extension

- Search for **"Arduino"** by **Microsoft** (official one)
- If not available, use Arduino IDE directly (Option 2)

## 📁 Project Structure

```
emg_function/
├── emg_function.ino          # Main Arduino code (refined & documented)
├── emg_visualizer.py         # Full-featured Python visualizer with statistics
├── emg_visualizer_simple.py  # Simplified Python visualizer
├── run_visualizer.bat        # Quick launch for main visualizer (Windows)
├── run_simple_visualizer.bat # Quick launch for simple visualizer (Windows)
├── requirements.txt          # Python dependencies
├── platformio.ini            # PlatformIO configuration (optional)
├── README.md                 # This file
├── CHANGELOG.md              # Version history and changes
└── Documentation files/      # Setup guides and notes
```

## 🚀 Quick Start Commands

```bash
# Install Python dependencies
pip install -r requirements.txt

# Upload to ESP32S3 (in Cursor)
# Ctrl+Shift+P → "Arduino: Upload"

# Run Python visualizer
python emg_visualizer.py

# Or specify COM port directly (Windows)
python emg_visualizer.py COM5

# Or on Mac/Linux
python emg_visualizer.py /dev/ttyUSB0
```

## 🧪 Testing Procedure

1. **Setup**: Connect EMG sensor to ESP32S3
2. **Upload**: Flash code to board
3. **Calibrate**: Keep muscle relaxed for 10 seconds (device will notify when complete)
   - This is a **one-time calibration** at startup
   - No automatic recalibration during operation
   - To recalibrate, reset/restart the device
4. **Test**: Perform muscle contractions of varying strengths
5. **Observe**: Watch for ON/OFF state transitions
6. **Adjust**: If too sensitive/insensitive, modify `THRESHOLD_MULTIPLIER` and re-upload

## 📝 Signal Processing Details

- **Sampling Rate**: 500 Hz
- **Filter**: Band-pass Butterworth IIR 4th order (74.5-149.5 Hz)
- **Envelope**: Moving average over 128 samples
- **Smoothing**: Exponential moving average (α = 0.15)
- **RMS**: Calculated over 50 samples for alternative signal representation
- **Output Rate**: 10 Hz (every 100ms)
- **Calibration**: Welford's online algorithm for mean and variance
- **Threshold**: Adaptive, based on baseline: `mean + 3σ`
- **State Detection**: Binary (ON/OFF) based on envelope crossing threshold

## 🎓 For Professors/Reviewers

This system demonstrates:
- Real-time embedded signal processing
- Adaptive threshold calibration
- Professional data visualization
- Multiple output modalities
- Clean code architecture

The Python visualizer provides publication-quality graphs suitable for:
- Academic presentations
- Research papers
- Demo videos
- Technical documentation

## 🤝 Contributing

Feel free to:
- Adjust threshold sensitivity
- Modify visualization colors
- Add new signal processing features
- Improve calibration algorithm

## 📄 License

MIT License - Feel free to use for academic or commercial projects

## 👥 Authors

CPE4B - DSP Project Team

---

## 🆕 Recent Updates

### v2.1 (October 2025): Calibration Enhancement
- ✅ **Extended calibration**: 5 seconds → **10 seconds** (better accuracy)
- ✅ **One-time calibration only**: No automatic recalibration
- ✅ **More stable threshold**: 2× more samples for calculation
- ✅ **User-controlled recalibration**: Reset device to recalibrate

### v2.0 (October 2025): Major Refactoring
- ✅ Simplified detection system: **Relaxed/Active/Stressed** → **ON/OFF**
- ✅ Single adaptive threshold instead of multiple thresholds
- ✅ Improved code documentation with clear section markers
- ✅ Enhanced visualizers with cleaner interface
- ✅ Reduced data output from 6 to 4 fields (better performance)
- ✅ More intuitive configuration parameters

See `CHANGELOG.md` for detailed changes.

---

**Need Help?** Check the troubleshooting section or contact your instructor!

**Tip**: The Python visualizers provide much better visualization than Arduino Serial Plotter - highly recommended for demonstrations! 🎨

**New to the project?** The simple visualizer (`emg_visualizer_simple.py`) is great for beginners - clean interface, easy to understand!

