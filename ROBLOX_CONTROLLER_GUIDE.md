# EMG Roblox Controller Guide 🎮

Control Roblox games using EMG muscle signals! This application maps your muscle activations to WASD keyboard controls.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**New dependency:** `pynput` - Used for keyboard simulation

### 2. Run the Controller

**Windows:**
```bash
run_roblox_controller.bat
```

**Or directly:**
```bash
python roblox_emg_controller.py
```

## 🎯 How to Use

### Step 1: Connect to ESP32
1. Connect your Waveshare ESP32-S3 Zero via USB
2. Open the controller application
3. Click **"Refresh Ports"** if your port doesn't appear
4. Select your COM port from the dropdown
5. Click **"Connect"**

### Step 2: Wait for Calibration
- The Arduino automatically calibrates on startup
- Wait 20 seconds, then keep your muscle **completely relaxed** for 10 seconds
- You'll see "✓ Calibration complete!" in the log when done

### Step 3: Enable Controller
1. Click **"Enable Controller"** button
2. Status will change to "Controller: ON" (green)
3. **Important:** Make sure Roblox is open and focused!

### Step 4: Play!
Use these muscle patterns to control movement:

- **Single Quick Flex** → **W** (Move Forward)
- **Double Quick Flex** → **S** (Move Backward)
- **Long Hold (0.5s+)** → **A** (Move Left)
- **Long Hold (2s+)** → **D** (Move Right) - switches from A
- **Release Muscle** → Stop (All keys released)

## 🎮 Control Mapping

| Muscle Pattern | Key | Action |
|---------------|-----|--------|
| Single spike | W | Forward |
| Double spike (quick) | S | Backward |
| Long hold (0.5-2s) | A | Left |
| Long hold (2s+) | D | Right |
| No activation | - | Stop |

## 🖥️ GUI Features

### Connection Panel
- **Port Selection**: Choose your ESP32 COM port
- **Refresh Ports**: Update available ports list
- **Connect/Disconnect**: Toggle serial connection
- **Status Indicator**: Shows connection state

### Control Panel
- **Enable Controller**: Turn keyboard control ON/OFF
- **Request Calibration**: Request recalibration (Arduino auto-calibrates on reset)
- **Controller Status**: Shows if controller is active

### Signal Display
- **Envelope**: Current EMG envelope value
- **RMS**: Root mean square value
- **Threshold**: Activation threshold (from calibration)
- **Muscle State**: ON/OFF indicator
- **Active Key**: Currently pressed key (W/A/S/D)

### Status Log
- Real-time log of all events
- Connection status
- Calibration status
- Key press events
- Pattern detection

## ⚠️ Important Notes

1. **Admin Rights**: On Windows, you may need to run as Administrator for keyboard simulation to work properly

2. **Roblox Focus**: Make sure Roblox window is active/focused when controller is enabled

3. **Calibration**: 
   - Happens automatically on Arduino startup
   - Wait 20 seconds, then relax muscle for 10 seconds
   - Don't move during calibration!

4. **Safety**: 
   - Always disable controller before closing the app
   - The app will automatically release all keys on close
   - Don't use while typing in other applications

5. **Pattern Timing**:
   - Single spike: Quick flex and release (< 1 second)
   - Double spike: Two quick flexes within 1 second
   - Long hold: Keep muscle flexed for 0.5+ seconds

## 🔧 Troubleshooting

### Controller Not Working
- Check if Roblox window is focused
- Verify controller is "ON" (green status)
- Check if calibration completed successfully
- Try disabling and re-enabling controller

### Keys Not Pressing
- Run as Administrator (Windows)
- Check if pynput is installed: `pip install pynput`
- Verify muscle activation is detected (check "Muscle: ON" indicator)

### Connection Issues
- Check USB cable connection
- Verify correct COM port selected
- Try refreshing ports
- Check if Arduino IDE Serial Monitor is closed (can't share port)

### Calibration Issues
- Reset Arduino to restart calibration
- Ensure muscle is completely relaxed during calibration
- Wait full 20 seconds before relaxing
- Keep relaxed for full 10 seconds

## 🎯 Tips for Best Results

1. **Practice Patterns**: Get familiar with single/double spike timing
2. **Consistent Placement**: Keep EMG electrodes in same position
3. **Clean Skin**: Clean electrode placement area for better signal
4. **Adjust Threshold**: If too sensitive/not sensitive, modify `THRESHOLD_MULTIPLIER` in Arduino code
5. **Test First**: Test in a safe Roblox game before competitive play

## 📝 Technical Details

- **Sampling Rate**: 500 Hz (Arduino)
- **Update Rate**: 10 Hz (GUI updates)
- **Pattern Detection**: Edge detection on muscle activation
- **Key Simulation**: Uses pynput library for cross-platform keyboard control

## 🛑 Emergency Stop

If something goes wrong:
1. Click **"Disable Controller"** immediately
2. Or close the application window
3. All keys will be automatically released

---

**Enjoy controlling Roblox with your muscles!** 💪🎮

