# Calibration Update - v2.1

## 🎯 Summary of Changes

### What Changed?

**Calibration Duration:**
- **Before**: 5 seconds
- **After**: **10 seconds**

**Recalibration:**
- **Before**: Every 20 seconds (automatic)
- **After**: **One-time only** at startup (no automatic recalibration)

---

## 📋 Files Updated

✅ **Arduino Code**
- `emg_function.ino`: Changed `CALIBRATION_SECONDS` from 5 to 10
- Added message: "NO automatic recalibration"

✅ **Documentation**
- `README.md`: Updated all calibration references to 10 seconds
- `CHANGELOG.md`: Added calibration update details
- `QUICK_REFERENCE.md`: Updated quick start and troubleshooting
- `IMPROVEMENTS.md`: Added v2.0 notice

---

## 🤔 Why This Change?

### Longer Calibration (10 seconds)
1. **More Stable Baseline**: More samples = better statistical accuracy
2. **Better Standard Deviation**: Captures true variability of relaxed state
3. **Fewer False Positives**: More robust threshold calculation
4. **User Confidence**: Ensures user is truly relaxed before starting

### No Auto-Recalibration
1. **Consistent Behavior**: Threshold stays constant during session
2. **Predictable Detection**: User knows what to expect
3. **No Sudden Changes**: Prevents confusion from shifting thresholds
4. **User Control**: To recalibrate, simply reset/restart device

---

## 📊 Impact on Detection

### Before (5 seconds, auto-recalibration)
```
Initial calibration: 5 seconds
→ Calculate threshold
→ Use for 20 seconds
→ Recalibrate automatically
→ New threshold (may differ)
→ Repeat...
```

**Problems:**
- Threshold could change during use
- If user flexed during recalibration → bad threshold
- Inconsistent behavior

### After (10 seconds, one-time)
```
Initial calibration: 10 seconds
→ Calculate threshold
→ Use for entire session
→ Threshold remains constant
→ To recalibrate: reset device
```

**Benefits:**
- ✅ Stable, consistent threshold
- ✅ Predictable behavior
- ✅ Better baseline measurement
- ✅ User-controlled recalibration

---

## 🔧 Technical Details

### Calibration Algorithm (Unchanged)

```cpp
// Welford's online algorithm for mean and variance
samples_since_start++;
float delta = envelope - baseline_mean;
baseline_mean += delta / samples_since_start;
baseline_variance += delta * (envelope - baseline_mean);

// After 10 seconds (5000 samples at 500 Hz):
baseline_std = sqrt(baseline_variance / (samples_since_start - 1));
activation_threshold = baseline_mean + (3.0 * baseline_std);
```

### Statistics
- **Samples collected**: 5,000 samples (500 Hz × 10 seconds)
- **Previous**: 2,500 samples (500 Hz × 5 seconds)
- **Improvement**: 2× more data for threshold calculation

---

## 👤 User Experience

### Startup Sequence

```
1. Device starts
   ↓
2. "CALIBRATION STARTING (10 seconds)"
   ↓
3. User keeps muscle relaxed for 10 seconds
   ↓
4. "✓ CALIBRATION COMPLETE"
   ↓
5. Threshold displayed
   ↓
6. Ready for use (threshold stays constant)
```

### If Threshold Seems Wrong

**Option 1: Adjust Multiplier**
```cpp
#define THRESHOLD_MULTIPLIER 2.5f  // More sensitive
#define THRESHOLD_MULTIPLIER 4.0f  // Less sensitive
```

**Option 2: Recalibrate**
- Press reset button on ESP32S3
- Keep muscle relaxed for full 10 seconds
- New threshold will be calculated

---

## 📝 Updated Code Comments

```cpp
// ========== Calibration Settings ==========
#define CALIBRATION_SECONDS 10  // Calibration duration (seconds) - ONE TIME ONLY
#define THRESHOLD_MULTIPLIER 3.0f  // Threshold = mean + (k × std_dev)
```

Startup message now shows:
```
============================================
  EMG SIGNAL PROCESSOR INITIALIZED
============================================
⏳ CALIBRATION STARTING (10 seconds)
   Keep muscle COMPLETELY RELAXED!
   Do NOT move, flex, or tense!
   NO automatic recalibration
============================================
```

---

## 🧪 Testing Recommendations

### For Best Results:
1. ✅ **Sit comfortably** before starting device
2. ✅ **Relax completely** for full 10 seconds
3. ✅ **Don't talk or move** during calibration
4. ✅ **Verify threshold** makes sense (check serial output)
5. ✅ **Test with gradual contractions** to find your ON point

### If Testing Different Settings:
1. Modify `THRESHOLD_MULTIPLIER` if needed
2. Upload new code
3. Reset device
4. Recalibrate (10 seconds relaxed)
5. Test detection
6. Repeat until optimal

---

## 🎓 For Instructors/Reviewers

### Why This Approach?

**Statistical Justification:**
- 10 seconds at 500 Hz = 5,000 samples
- Central Limit Theorem: More samples → better mean/std estimates
- 3σ threshold captures 99.7% of relaxed state
- One-time calibration ensures reproducible results

**User Experience:**
- Simple, predictable behavior
- User understands: "Calibrate once at start"
- No mysterious threshold changes during use
- Clear recalibration process (reset device)

**Practical Benefits:**
- Consistent demonstration results
- Easier to document threshold values
- Better for comparative studies
- Suitable for clinical/research applications

---

## 📊 Expected Results

### Typical Threshold Values

**Example calibration output:**
```
Baseline: 48.25 ± 8.15 units
Activation Threshold: 72.70 units
```

**Explanation:**
- Baseline mean: 48.25 (average relaxed signal)
- Standard deviation: 8.15 (natural variation)
- Threshold: 48.25 + (3.0 × 8.15) = 72.70

**During use:**
- Signal below 72.70 → OFF (relaxed)
- Signal above 72.70 → ON (active)

---

## 🔄 Migration from v2.0

If you have the previous version:

1. **Update Arduino code**: Upload new `emg_function.ino`
2. **No Python changes needed**: Visualizers work the same
3. **Just remember**: Keep relaxed for 10 seconds (not 5)

---

## ⚙️ Configuration Options

```cpp
// Conservative (less false positives, may miss weak contractions)
#define CALIBRATION_SECONDS 15
#define THRESHOLD_MULTIPLIER 4.0f

// Balanced (recommended for most users)
#define CALIBRATION_SECONDS 10
#define THRESHOLD_MULTIPLIER 3.0f

// Sensitive (catches weak contractions, may have false positives)
#define CALIBRATION_SECONDS 10
#define THRESHOLD_MULTIPLIER 2.0f

// Quick testing (not recommended for final use)
#define CALIBRATION_SECONDS 5
#define THRESHOLD_MULTIPLIER 3.0f
```

---

## 🆘 Troubleshooting

### "10 seconds is too long!"
- **Why 10?** More samples = more accurate threshold
- **Can I reduce it?** Yes, but less reliable
- **Recommendation**: Keep at 10 for best results

### "Threshold seems too high/low after calibration"
**Possible causes:**
1. Moved during calibration → Recalibrate (reset device)
2. Electrode placement changed → Adjust electrodes, recalibrate
3. Need different sensitivity → Adjust `THRESHOLD_MULTIPLIER`

### "Can I add back auto-recalibration?"
- Not recommended - causes inconsistent behavior
- If you really need it, you can add custom logic
- Better approach: Manual recalibration (reset when needed)

---

## 📈 Benefits Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Calibration Time** | 5 seconds | 10 seconds |
| **Sample Count** | 2,500 | 5,000 |
| **Recalibration** | Every 20s (auto) | Manual (reset) |
| **Consistency** | Variable | Stable |
| **Predictability** | Lower | Higher |
| **User Control** | Automatic | Manual |
| **Threshold Quality** | Good | Better |

---

## ✅ Checklist for Users

Before using the updated system:

- [ ] Uploaded new `emg_function.ino` to ESP32S3
- [ ] Read updated `README.md` for new instructions
- [ ] Understand calibration is now 10 seconds
- [ ] Know how to recalibrate (reset device)
- [ ] Tested threshold with muscle contractions
- [ ] Adjusted `THRESHOLD_MULTIPLIER` if needed

---

**Version**: v2.1  
**Date**: October 17, 2025  
**Change**: Extended calibration to 10 seconds, removed auto-recalibration  
**Reason**: Better baseline measurement and consistent behavior

