# EMG Function - Changelog

## Version 2.1 - Extended Calibration

### Date: October 17, 2025

### 🔧 Calibration Changes
- **Extended calibration period**: 5 seconds → **10 seconds**
- **Removed automatic recalibration**: No more 20-second recalibration cycles
- **One-time calibration only**: Calibrates once at startup, remains constant
- **Better baseline measurement**: 2× more samples (5,000 vs 2,500)
- **More stable threshold**: Improved statistical accuracy

**To recalibrate**: Simply reset/restart the device

---

## Version 2.0 - ON/OFF Detection Refactor

### Date: October 17, 2025

---

## 🎯 Major Changes

### 1. **Arduino Code Refinement (`emg_function.ino`)**

#### Code Organization
- ✅ Added comprehensive header documentation
- ✅ Organized code into clearly labeled sections with visual separators
- ✅ Added detailed function documentation with JSDoc-style comments
- ✅ Improved variable naming for better code clarity
- ✅ Enhanced code readability with structured comments

#### Threshold Detection System
- **CHANGED**: Simplified from 3-level detection (Relaxed/Active/Stressed) to **binary ON/OFF detection**
- **CHANGED**: Single adaptive threshold calculated as: `mean + 3.0 × std_dev`
- Removed: `RELAXED_K`, `ACTIVE_K`, `STRESSED_K` multipliers
- Added: `THRESHOLD_MULTIPLIER` (default: 3.0)
- Added: `muscle_active` boolean flag for clear state tracking

#### Calibration
- **Extended to 10-second calibration period** for more stable baseline
- **One-time calibration only** - removed automatic recalibration
- Uses Welford's algorithm for online mean/variance calculation
- More informative calibration status messages
- Clearer completion notification
- To recalibrate, simply reset/restart the device

#### Data Output Format
**Old Format** (6 fields):
```
Envelope, RMS, Relaxed_Threshold, Active_Threshold, Stressed_Threshold, State
```

**New Format** (4 fields):
```
Envelope, RMS, Threshold, State
```

Where:
- `Envelope`: Smoothed EMG envelope value
- `RMS`: Root mean square of signal
- `Threshold`: Activation threshold (0 during calibration)
- `State`: 0 = OFF, >0 = ON (displays as threshold × 1.3)

---

### 2. **Main Visualizer Update (`emg_visualizer.py`)**

#### User Interface
- **CHANGED**: Title from "Real-Time Visualization" to **"ON/OFF Detection"**
- **CHANGED**: State indicator from 3 levels (Relaxed/Normal/Stressed) to **2 levels (OFF/ON)**
- Simplified threshold display: Single red dashed line instead of three lines
- Updated legend: "Activation Threshold" instead of multiple thresholds

#### State Visualization
- **Removed**: Three-bar indicator (green/orange/red)
- **Added**: Two-bar indicator:
  - 🟢 **Green** = OFF (muscle relaxed)
  - 🔴 **Red** = ON (muscle active)

#### Statistics Panel
- Added "Activation Threshold" display
- Updated muscle state display: "ON 🔴" or "OFF 🟢"
- Clearer calibration status indicator

#### Data Processing
- Simplified parsing logic for new 4-field format
- Removed complex multi-level state detection
- Binary state detection: `muscle_on = (state > 0)`

---

### 3. **Simple Visualizer Update (`emg_visualizer_simple.py`)**

#### Complete Redesign
- **CHANGED**: From raw signal display to **threshold-based detection**
- **REMOVED**: Raw ADC signal plot
- **REMOVED**: Filtered signal plot
- **KEPT**: EMG envelope plot
- **KEPT**: RMS plot
- **ADDED**: Activation threshold line overlay
- **ADDED**: ON/OFF state indicator

#### Layout
New 3-panel layout:
1. **Main Plot** (top, spans full width):
   - EMG Envelope (blue solid line)
   - Activation Threshold (red dashed line)
2. **RMS Plot** (bottom left):
   - Real-time RMS values
3. **State Indicator** (bottom right):
   - Two-bar ON/OFF display

---

## 📊 Technical Improvements

### Signal Processing
- ✅ Maintained 500 Hz sampling rate
- ✅ Band-pass filter (74.5-149.5 Hz) with detailed documentation
- ✅ Envelope detection via moving average (128 samples)
- ✅ Exponential smoothing (α = 0.15) for stability
- ✅ RMS calculation (50-sample window)

### Calibration Algorithm
- ✅ Welford's online algorithm for running statistics
- ✅ Minimum noise floor protection (5.0 units)
- ✅ 5-second baseline measurement
- ✅ Automatic threshold calculation

### Data Reporting
- ✅ 10 Hz output rate (100ms intervals)
- ✅ Reduced data fields from 6 to 4 (33% reduction)
- ✅ Clearer state representation

---

## 🔧 Configuration Parameters

### Arduino (`emg_function.ino`)
```cpp
#define SAMPLE_RATE 500                  // 500 Hz sampling
#define CALIBRATION_SECONDS 10           // 10s one-time calibration
#define THRESHOLD_MULTIPLIER 3.0f        // Threshold = mean + 3σ
#define ENVELOPE_SMOOTH_FACTOR 0.15f     // EMA smoothing
#define BUFFER_SIZE 128                  // Moving average window
#define RMS_BUFFER_SIZE 50               // RMS calculation window
#define REPORT_INTERVAL_MS 100           // 10 Hz reporting
```

### Python Visualizers
```python
BAUD_RATE = 115200          # Serial communication speed
MAX_POINTS = 500            # Display last 50 seconds
UPDATE_INTERVAL = 20        # 20ms refresh (50 Hz)
```

---

## 📈 Benefits

1. **Simpler User Experience**
   - Easy to understand ON/OFF states
   - Clear visual feedback
   - Less cognitive load

2. **Improved Performance**
   - Reduced data transmission (4 fields vs 6)
   - Simpler state logic
   - Faster processing

3. **Better Code Quality**
   - Well-documented functions
   - Clear variable names
   - Organized structure
   - Easy to maintain

4. **More Reliable Detection**
   - Single adaptive threshold
   - Based on user's baseline
   - Reduces false positives
   - Consistent behavior

---

## 🔄 Migration Guide

### For Users
1. Upload the new `emg_function.ino` to your ESP32S3
2. Run either visualizer:
   - `run_visualizer.bat` (main, with statistics)
   - `run_simple_visualizer.bat` (simple, cleaner view)
3. Keep muscle relaxed during 5-second calibration
4. Flex muscle to see ON/OFF detection

### For Developers
If you have custom code using the old format:
- Update serial parsing from 6 fields to 4 fields
- Replace three-level state detection with binary detection
- Update threshold handling (single threshold instead of three)

---

## 📝 File Changes Summary

| File | Lines Changed | Status |
|------|--------------|--------|
| `emg_function.ino` | ~150 lines | ✅ Refined & Simplified |
| `emg_visualizer.py` | ~100 lines | ✅ Updated to ON/OFF |
| `emg_visualizer_simple.py` | ~80 lines | ✅ Redesigned |
| `CHANGELOG.md` | New file | ✅ Created |

---

## 🎓 Key Concepts

### Adaptive Threshold
The system automatically calculates an optimal threshold based on YOUR muscle's baseline:
```
Threshold = Baseline_Mean + (3.0 × Baseline_StdDev)
```

This ensures:
- Personalized detection for each user
- Adapts to different sensor placements
- Accounts for varying signal strengths

### Binary State Detection
```
if (envelope >= threshold):
    state = ON  (muscle is active)
else:
    state = OFF (muscle is relaxed)
```

---

## 🐛 Known Issues
- None currently identified

## 🚀 Future Enhancements
- Adjustable threshold multiplier via serial commands
- Real-time threshold tuning
- Data logging to file
- Multiple muscle channel support

---

**Developed with ❤️ for EMG signal processing**

