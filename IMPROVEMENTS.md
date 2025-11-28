# EMG Signal Processing Improvements 🚀

> **⚠️ NOTE: This document describes v1.0 improvements.**  
> **For the latest v2.0 changes (ON/OFF detection), see `CHANGELOG.md`**

---

## What Was Improved (v1.0)

### 1. **Longer Calibration Time** ⏱️
- **Before:** 3 seconds
- **After:** 5 seconds (now 10 seconds in v2.0)
- **Why:** More samples = more accurate baseline measurement

### 2. **DC Offset Removal** 🔧
- Calculates and removes DC bias from ADC readings
- First 100 samples used to measure offset
- Results in cleaner, centered signal

### 3. **Improved Signal Processing** 📊

#### Full-Wave Rectification
- Proper absolute value (full-wave rectification) applied
- Better envelope detection

#### Exponential Moving Average (EMA)
- Smooths envelope to reduce noise
- Smooth factor: 0.15 (85% previous, 15% current)
- More stable readings without lag

### 4. **Three-Level Threshold System** 🎯
- **Before:** 2 levels (Relaxed, Stressed)
- **After:** 3 levels (Relaxed, Active, Stressed)

**New Thresholds:**
```
Relaxed:   baseline + 1.5 × std
Active:    baseline + 2.5 × std
Stressed:  baseline + 4.0 × std
```

**Why:** More intuitive detection of muscle activity levels

### 5. **Better Threshold Calculation** 📈
- More conservative multipliers (less false positives)
- Minimum standard deviation enforced (5.0 units)
- Prevents overly sensitive detection

### 6. **Enhanced Calibration Messages** 📢
```
CALIBRATION STARTING...
Keep muscle COMPLETELY RELAXED for 5 seconds!
Do NOT move, flex, or tense your muscle!
```

Shows:
- DC offset value
- Baseline mean ± std
- All three thresholds

### 7. **Improved Python Visualizer** 🎨
- Now displays 3 threshold lines:
  - Green dashed = Relaxed
  - Yellow dashed = Active
  - Red dashed = Stressed
- Better color coding
- Thicker main signal line for clarity

---

## How It Works Now

### Calibration Phase (0-5 seconds):
1. **Samples 1-100:** Calculate DC offset
2. **Samples 100-2500:** Measure relaxed baseline
3. **At 5 seconds:** Calculate thresholds
4. **Result:** Three clear detection zones

### Detection Phase (After calibration):
```
Signal < Relaxed:     "Relaxed" (no activity)
Relaxed < Signal < Active:  "Relaxed" (minimal activity)  
Active < Signal < Stressed:  "Active" (moderate contraction)
Signal > Stressed:           "Stressed" (strong contraction)
```

---

## Key Parameters

You can adjust these in the code:

```cpp
#define CALIBRATION_SECONDS 5    // Calibration duration
#define RELAXED_K 1.5f           // Relaxed threshold multiplier
#define ACTIVE_K 2.5f            // Active threshold multiplier
#define STRESSED_K 4.0f          // Stressed threshold multiplier
#define ENVELOPE_SMOOTH_FACTOR 0.15f  // Smoothing (0.1-0.3 recommended)
```

---

## What To Expect

### ✅ Better Results:
- More stable readings
- Less noise
- Clearer state transitions
- Easier to detect different contraction levels

### ⚠️ Important:
- **MUST stay completely relaxed during 5-second calibration!**
- Any movement or tension will affect baseline
- If thresholds seem wrong, press RESET and recalibrate

---

## Troubleshooting

### "Thresholds too high - can't trigger Active/Stressed"
**Solution:** You moved during calibration
- Press RESET button
- Keep muscle 100% relaxed for full 5 seconds
- Try again

### "Too sensitive - triggers on tiny movements"
**Solution:** Increase threshold multipliers
```cpp
#define RELAXED_K 2.0f    // Was 1.5
#define ACTIVE_K 3.5f     // Was 2.5  
#define STRESSED_K 5.0f   // Was 4.0
```

### "Not sensitive enough"
**Solution:** Decrease threshold multipliers
```cpp
#define RELAXED_K 1.0f    // Was 1.5
#define ACTIVE_K 2.0f     // Was 2.5
#define STRESSED_K 3.0f   // Was 4.0
```

### "Signal too jumpy/noisy"
**Solution:** Increase smoothing
```cpp
#define ENVELOPE_SMOOTH_FACTOR 0.10f  // Was 0.15 (more smoothing)
```

### "Signal too slow to respond"
**Solution:** Decrease smoothing
```cpp
#define ENVELOPE_SMOOTH_FACTOR 0.25f  // Was 0.15 (faster response)
```

---

## Testing Your System

1. **Upload improved code** to ESP32S3
2. **Run Python visualizer**: `python emg_visualizer.py`
3. **Calibrate properly** (5 seconds, completely relaxed)
4. **Test muscle contractions:**
   - Light flex → Should cross "Relaxed" line
   - Medium flex → Should reach "Active" line
   - Hard flex → Should hit "Stressed" line

---

## Technical Details

### Signal Flow:
```
ADC Reading
    ↓
Remove DC Offset
    ↓
Band-Pass Filter (74.5-149.5 Hz)
    ↓
Full-Wave Rectification (abs)
    ↓
Moving Average Envelope (128 samples)
    ↓
Exponential Smoothing (EMA)
    ↓
Threshold Detection
    ↓
State Output
```

### Sampling:
- **ADC:** 500 Hz (every 2ms)
- **Output:** 50 Hz (every 20ms)
- **Filter:** Butterworth IIR, 4 cascaded biquads

---

## Summary

**Before:** Basic 2-level detection with short calibration
**After:** Professional 3-level detection with proper signal conditioning

Your EMG system now has **research-grade signal processing**! 🎓

---

**Questions?** Check the code comments or adjust the parameters mentioned above.

