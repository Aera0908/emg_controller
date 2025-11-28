# EMG ON/OFF Detection - Quick Reference

## 🎯 What Changed?

### Before (v1.0)
- **States**: Relaxed / Active / Stressed (3 levels)
- **Thresholds**: 3 different thresholds
- **Data Output**: 6 fields
- **Complexity**: Higher

### After (v2.0)
- **States**: OFF / ON (2 levels)
- **Threshold**: 1 adaptive threshold
- **Data Output**: 4 fields
- **Complexity**: Lower, easier to understand

---

## 🚀 Quick Start

1. **Upload** `emg_function.ino` to ESP32S3
2. **Keep muscle relaxed** for 10 seconds (one-time calibration)
3. **Run visualizer**:
   ```bash
   python emg_visualizer.py
   ```
4. **Flex muscle** to see ON/OFF detection

**Note**: Calibration happens once at startup. To recalibrate, reset the device.

---

## 📊 Understanding the Display

### Main Visualizer

```
┌─────────────────────────────────────────┐
│  EMG Envelope & Activation Threshold   │
│                                         │
│  ─── Blue Line: Your muscle signal     │
│  - - Red Line: Activation threshold    │
│  ─── Cyan Line: RMS (smoothed)         │
│                                         │
└─────────────────────────────────────────┘
┌──────────────┐  ┌──────────────────────┐
│ Muscle State │  │    Statistics        │
│              │  │  Current: 45.23      │
│  🟢 OFF      │  │  Threshold: 67.50    │
│  ⬜ ON       │  │  State: OFF 🟢       │
└──────────────┘  └──────────────────────┘
```

### When Muscle Activates

```
┌─────────────────────────────────────────┐
│  EMG Envelope & Activation Threshold   │
│                                         │
│       📈 Signal crosses threshold       │
│  ─── Blue Line: Your muscle signal     │
│  - - Red Line: Activation threshold    │
│  ─── Cyan Line: RMS (smoothed)         │
│                                         │
└─────────────────────────────────────────┘
┌──────────────┐  ┌──────────────────────┐
│ Muscle State │  │    Statistics        │
│              │  │  Current: 89.45      │
│  ⬜ OFF      │  │  Threshold: 67.50    │
│  🔴 ON       │  │  State: ON 🔴        │
└──────────────┘  └──────────────────────┘
```

---

## 🎛️ Adjusting Sensitivity

### Too Sensitive (activates when relaxed)?

**Increase** threshold multiplier:
```cpp
#define THRESHOLD_MULTIPLIER 4.0f  // Was 3.0f
```

### Not Sensitive Enough (doesn't detect contraction)?

**Decrease** threshold multiplier:
```cpp
#define THRESHOLD_MULTIPLIER 2.5f  // Was 3.0f
```

### Formula

```
Activation Threshold = Baseline Mean + (Multiplier × Std Dev)
```

**Example:**
- Baseline Mean = 50 units
- Std Dev = 10 units
- Multiplier = 3.0

→ Threshold = 50 + (3.0 × 10) = **80 units**

---

## 🔧 Common Issues

### Issue: Muscle shown as ON when relaxed
**Solution**: Increase `THRESHOLD_MULTIPLIER` to 3.5 or 4.0

### Issue: Muscle stays OFF even when flexing hard
**Solution**: 
1. Decrease `THRESHOLD_MULTIPLIER` to 2.5 or 2.0
2. Check electrode placement
3. Recalibrate (reset device)

### Issue: Want different calibration time
**Solution**: Adjust calibration duration:
```cpp
#define CALIBRATION_SECONDS 5   // Reduce for faster (default: 10)
#define CALIBRATION_SECONDS 15  // Increase for more stable baseline
```
**Recommendation**: Keep at 10 seconds for best results.

### Issue: Detection is too jerky/jumpy
**Solution**: Increase smoothing:
```cpp
#define ENVELOPE_SMOOTH_FACTOR 0.10f  // Was 0.15f (lower = smoother)
```

---

## 📈 Data Format

### Serial Output (CSV)
```
Envelope, RMS, Threshold, State
45.23, 38.67, 67.50, 0.00
89.45, 76.32, 67.50, 87.75
```

**Fields:**
1. **Envelope** (float): Current signal amplitude
2. **RMS** (float): Root mean square value
3. **Threshold** (float): Activation threshold (0 during calibration)
4. **State** (float): 0 = OFF, >0 = ON

---

## 🎨 Visualizer Options

### Main Visualizer (`emg_visualizer.py`)
- **Best for**: Detailed analysis, demos, presentations
- **Features**: Full statistics, larger graphs
- **Use when**: You need detailed information

### Simple Visualizer (`emg_visualizer_simple.py`)
- **Best for**: Quick testing, cleaner view
- **Features**: Essential information only
- **Use when**: You want minimal distraction

---

## 💡 Tips

### For Best Results:
1. ✅ Clean skin with alcohol before placing electrodes
2. ✅ Keep relaxed during entire calibration period
3. ✅ Test with different contraction strengths
4. ✅ Recalibrate if you move electrodes

### For Demos:
1. 🎨 Use **main visualizer** for full-screen presentations
2. 📊 Maximize window for better visibility
3. 🔊 Explain threshold concept before starting
4. 💪 Show gradual increase from relaxed to contracted

### For Development:
1. 🔧 Start with default `THRESHOLD_MULTIPLIER = 3.0`
2. 📝 Log several trials to find optimal settings
3. 🧪 Test with different users
4. 📊 Compare RMS vs Envelope for your use case

---

## 🎓 Understanding the Algorithm

### Step 1: Calibration (10 seconds, one-time)
```
Collect baseline data while muscle is relaxed
→ Calculate mean and standard deviation using Welford's algorithm
→ Set threshold = mean + 3σ
→ This happens ONCE at startup (no automatic recalibration)
```

### Step 2: Real-Time Detection
```
For each sample:
  1. Read sensor
  2. Apply band-pass filter (74.5-149.5 Hz)
  3. Calculate envelope (moving average)
  4. Apply smoothing (exponential moving average)
  5. Compare to threshold:
     - If envelope ≥ threshold: State = ON
     - If envelope < threshold: State = OFF
```

### Why This Works
- **Adaptive**: Threshold adjusts to each person
- **Robust**: Uses statistics (mean + 3σ captures 99.7% of relaxed state)
- **Fast**: Simple comparison operation
- **Reliable**: Smoothing reduces noise

---

## 🔬 Advanced: Understanding σ (Sigma)

### What is 3σ?

In statistics, σ (sigma) = standard deviation

**For normal distribution:**
- 1σ = 68% of data
- 2σ = 95% of data
- 3σ = 99.7% of data

**In EMG context:**
- Baseline mean = average signal when relaxed
- 3σ = captures all relaxed state variations
- Mean + 3σ = threshold above normal noise

**Example:**
```
Calibration data: [45, 48, 50, 52, 49, 47, 51, 46, 50, 48]

Mean = 48.6
Std Dev (σ) = 2.1
3σ = 6.3

Threshold = 48.6 + 6.3 = 54.9

→ Any signal above 54.9 = muscle activation
→ Signal below 54.9 = relaxed state
```

---

## 📚 Resources

- **Full Documentation**: `README.md`
- **Change History**: `CHANGELOG.md`
- **Setup Guide**: `SETUP_GUIDE.md`
- **Troubleshooting**: See README.md § Troubleshooting

---

## 🆘 Need Help?

1. Check `README.md` troubleshooting section
2. Verify electrode placement
3. Try recalibration
4. Adjust `THRESHOLD_MULTIPLIER`
5. Contact your instructor

---

**Last Updated**: October 17, 2025  
**Version**: 2.0  
**Project**: EMG ON/OFF Detection System

