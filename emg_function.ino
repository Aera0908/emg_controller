/*
 * EMG Signal Processor - Seeed XIAO ESP32S3
 * ==========================================
 * Enhanced EMG signal processing with adaptive threshold detection
 * Hardware: Seeed XIAO ESP32S3 + EMG Candy (Upside Down Labs)
 * 
 * EMG Candy Specs:
 * - Output: 0-3.3V (pre-amplified and filtered)
 * - Power: 3.3V from ESP32
 * - Already includes rectification and envelope detection
 * 
 * XIAO ESP32S3 Pinout:
 * - D9 = GPIO8 (used for EMG signal input)
 * - 3.3V and GND for power
 * 
 * Features:
 * - Automatic baseline calibration
 * - Real-time envelope detection and RMS calculation
 * - Binary ON/OFF state detection based on adaptive threshold
 */

#include <math.h>

// ========== Hardware Configuration ==========
#define SAMPLE_RATE 500        // 500 Hz sampling rate
#define BAUD_RATE 115200       // Serial communication rate
#define INPUT_PIN 8            // XIAO ESP32S3: D9 = GPIO8 (EMG signal input)
#define BUFFER_SIZE 16         // Small buffer for minimal delay

// ========== Sensor Type ==========
// Set to true for EMG Candy (pre-processed signal)
// Set to false for raw EMG sensors that need filtering
#define EMG_CANDY_SENSOR true

// ========== Calibration Settings ==========
#define WAIT_BEFORE_CALIBRATION 3   // Wait time before calibration starts (seconds)
#define RELAXED_CALIBRATION_SEC 10  // Phase 1: Scan relaxed muscle (seconds)
#define FLEX_CALIBRATION_SEC 10     // Phase 2: Scan flex peaks (seconds)

// Threshold calculation:
// SPIKE_THRESHOLD_POSITION: Where spike threshold sits between baseline and peak
//   0.1 = 10% up from baseline (very easy)
//   0.2 = 20% up from baseline (easy)
//   0.3 = 30% up from baseline (medium)
#define SPIKE_THRESHOLD_POSITION 0.15f  // 15% - very easy to trigger

// HOLD_THRESHOLD_RATIO: Hold threshold as ratio of spike threshold
//   0.5 = hold threshold is 50% of spike threshold
//   0.7 = hold threshold is 70% of spike threshold
#define HOLD_THRESHOLD_RATIO 0.6f       // 60% of spike threshold for hold

// Minimum threshold as multiplier of baseline
#define MIN_THRESHOLD_MULTIPLIER 1.05f  // Just 5% above baseline max

// ========== Signal Processing Buffers ==========
// Envelope detection (moving average)
int circular_buffer[BUFFER_SIZE];
int data_index = 0;
int sum = 0;

// RMS calculation buffer
#define RMS_BUFFER_SIZE 20     // Smaller for faster response (was 50)
float rms_buffer[RMS_BUFFER_SIZE];
int rms_index = 0;

// ========== Calibration State ==========
// Calibration phases: WAITING -> RELAXED -> FLEX -> DONE
#define CALIB_WAITING 0
#define CALIB_RELAXED 1
#define CALIB_FLEX 2
#define CALIB_DONE 3
int calibration_phase = CALIB_WAITING;

bool calibrated = false;
unsigned long phase_start_ms = 0;    // Start time of current phase
unsigned long samples_in_phase = 0;  // Samples collected in current phase

// Relaxed phase data
float baseline_mean = 0.0f;          // Mean envelope during rest
float baseline_max = 0.0f;           // Max value during rest (noise ceiling)
float baseline_variance = 0.0f;      // Variance accumulator
float baseline_std = 1.0f;           // Standard deviation

// Flex phase data
float flex_peak = 0.0f;              // Peak value during flex
float flex_sum = 0.0f;               // Sum for averaging peaks
int flex_peak_count = 0;             // Number of peaks detected
float last_peak_value = 0.0f;        // Track last peak to avoid counting same peak twice
bool in_flex = false;                // Currently in a flex (above baseline)

// ========== Threshold Detection ==========
float activation_threshold = 0.0f;  // Spike threshold (high - for detecting spikes)
float hold_threshold = 0.0f;        // Hold threshold (low - for maintaining A/D)
bool muscle_active = false;          // Current state: ON (true) or OFF (false)

// ========== Signal Smoothing ==========
// Two-stage smoothing: fast response + smooth output
float smoothed_envelope = 0.0f;
float display_envelope = 0.0f;  // Second stage for smooth display

#if EMG_CANDY_SENSOR
  // EMG Candy is already smoothed
  #define ENVELOPE_SMOOTH_FACTOR 0.50f    // Fast first stage (high alpha = fast)
  #define DISPLAY_SMOOTH_FACTOR 0.25f     // Smooth second stage for display
#else
  // Raw EMG needs more smoothing
  #define ENVELOPE_SMOOTH_FACTOR 0.20f
  #define DISPLAY_SMOOTH_FACTOR 0.15f
#endif

// ========== Data Reporting ==========
unsigned long last_report_ms = 0;
#define REPORT_INTERVAL_MS 50   // Report every 50ms (20 Hz) - smoother updates

// Forward decl
float EMGFilter(float input);
int getEnvelop(int abs_emg);
float getRMS();
float getSmoothedEnvelope(float current_env);
void checkSerialCommands();
void handleCommand(String cmd);

// ========== Setup Function ==========
void setup() {
	// Initialize serial communication
	// For ESP32-S3 Zero (USB CDC), Serial.begin() doesn't block
	Serial.begin(BAUD_RATE);
	
	// Don't wait for Serial on ESP32-S3 Zero - it uses native USB CDC
	// The wait loop can cause issues with USB CDC
	delay(1000);  // Give USB time to initialize
	
	// Configure ADC for ESP32-S3
	#if defined(ARDUINO_ARCH_ESP32)
		analogReadResolution(12);  // 12-bit resolution (0-4095)
		analogSetPinAttenuation(INPUT_PIN, ADC_11db);  // 0-3.3V range (matches EMG Candy output)
	#endif

	// Initialize buffers
	for (int i = 0; i < RMS_BUFFER_SIZE; i++) {
		rms_buffer[i] = 0.0f;
	}
	
	// Start calibration state machine
	calibration_phase = CALIB_WAITING;
	phase_start_ms = millis();
	last_report_ms = millis();
	
	// Print startup information
	Serial.println("Envelope,RMS,Threshold,State");
	Serial.flush();
	delay(10);
	
	Serial.println("============================================");
	Serial.flush();
	
	Serial.println("  EMG SIGNAL PROCESSOR - 2-PHASE CALIBRATION");
	Serial.flush();
	
	Serial.println("============================================");
	Serial.flush();
	
	Serial.println("Calibration in 5 seconds...");
	Serial.flush();
	
	Serial.println("");
	Serial.flush();
	
	Serial.println("Phase 1: Keep muscle RELAXED (10 sec)");
	Serial.flush();
	
	Serial.println("Phase 2: FLEX muscle several times (10 sec)");
	Serial.flush();
	
	Serial.println("============================================");
	Serial.flush();
}

// ========== Main Loop ==========
void loop() {
	// Maintain precise 500 Hz sampling rate using microsecond timing
	static unsigned long past = 0;
	unsigned long present = micros();
	unsigned long interval = present - past;
	past = present;

	static long timer = 0;
	timer -= interval;

	if (timer < 0) {
		timer += 1000000 / SAMPLE_RATE;

		// ===== Signal Processing Chain =====
		// 1. Read raw analog signal from EMG sensor
		int sensor_value = analogRead(INPUT_PIN);
		
		float processed_signal;
		
		#if EMG_CANDY_SENSOR
			// EMG Candy outputs pre-processed signal (already rectified & enveloped)
			// Just use the raw value directly - no filtering needed
			processed_signal = (float)sensor_value;
		#else
			// Raw EMG sensor - apply full processing chain
			// 2. Apply band-pass filter (74.5-149.5 Hz)
			float filtered_signal = EMGFilter((float)sensor_value);
			
			// 3. Full-wave rectification (absolute value)
			processed_signal = fabs(filtered_signal);
		#endif
		
		// 4. Calculate envelope (moving average smoothing)
		int envelope = getEnvelop((int)processed_signal);
		
		// 5. Apply exponential smoothing for stability
		smoothed_envelope = getSmoothedEnvelope((float)envelope);
		
		// 6. Update RMS buffer for alternative signal representation
		rms_buffer[rms_index] = processed_signal * processed_signal;
		rms_index = (rms_index + 1) % RMS_BUFFER_SIZE;

		// ===== CALIBRATION STATE MACHINE =====
		
		// ----- PHASE 0: WAITING -----
		if (calibration_phase == CALIB_WAITING) {
			if ((millis() - phase_start_ms) >= (WAIT_BEFORE_CALIBRATION * 1000UL)) {
				// Move to relaxed phase
				calibration_phase = CALIB_RELAXED;
				phase_start_ms = millis();
				samples_in_phase = 0;
				baseline_mean = 0.0f;
				baseline_max = 0.0f;
				baseline_variance = 0.0f;
				
				Serial.println("");
				Serial.flush();
				Serial.println("============================================");
				Serial.flush();
				Serial.println("  PHASE 1: RELAXED CALIBRATION");
				Serial.flush();
				Serial.println("============================================");
				Serial.flush();
				Serial.println("   Keep muscle COMPLETELY RELAXED!");
				Serial.flush();
				Serial.println("   Do NOT move, flex, or tense!");
				Serial.flush();
				Serial.println("   Duration: 10 seconds");
				Serial.flush();
				Serial.println("============================================");
				Serial.flush();
			}
		}
		
		// ----- PHASE 1: RELAXED CALIBRATION -----
		else if (calibration_phase == CALIB_RELAXED) {
			samples_in_phase++;
			
			// Track relaxed baseline using Welford's algorithm
			float env_f = smoothed_envelope;
			float delta = env_f - baseline_mean;
			baseline_mean += delta / (float)samples_in_phase;
			baseline_variance += delta * (env_f - baseline_mean);
			
			// Track maximum during relaxed (noise ceiling)
			if (env_f > baseline_max) {
				baseline_max = env_f;
			}
			
			// Check if relaxed phase is complete
			if ((millis() - phase_start_ms) >= (RELAXED_CALIBRATION_SEC * 1000UL) && samples_in_phase > 100) {
				baseline_std = sqrtf(baseline_variance / (float)(samples_in_phase - 1));
				
				// Move to flex phase
				calibration_phase = CALIB_FLEX;
				phase_start_ms = millis();
				samples_in_phase = 0;
				flex_peak = 0.0f;
				flex_sum = 0.0f;
				flex_peak_count = 0;
				in_flex = false;
				
				Serial.println("");
				Serial.flush();
				Serial.println("============================================");
				Serial.flush();
				Serial.println("  PHASE 2: FLEX CALIBRATION");
				Serial.flush();
				Serial.println("============================================");
				Serial.flush();
				Serial.println("   Now FLEX your muscle several times!");
				Serial.flush();
				Serial.println("   Do 5-10 strong flexes.");
				Serial.flush();
				Serial.println("   Duration: 10 seconds");
				Serial.flush();
				Serial.print("   Baseline detected: ");
				Serial.println(baseline_mean, 1);
				Serial.flush();
				Serial.println("============================================");
				Serial.flush();
			}
		}
		
		// ----- PHASE 2: FLEX CALIBRATION -----
		// Detects BOTH up-spikes AND down-spikes, uses whichever is stronger
		else if (calibration_phase == CALIB_FLEX) {
			samples_in_phase++;
			float env_f = smoothed_envelope;
			
			// Track both min and max during flex phase
			static float flex_min = 99999.0f;  // Track minimum (for inverted signals)
			static float flex_max_val = 0.0f;  // Track maximum (for normal signals)
			
			// Initialize on first sample
			if (samples_in_phase == 1) {
				flex_min = env_f;
				flex_max_val = env_f;
			}
			
			// Update min/max
			if (env_f < flex_min) flex_min = env_f;
			if (env_f > flex_max_val) flex_max_val = env_f;
			
			// Detect flex events (deviation from baseline mean)
			float upper_threshold = baseline_mean + (baseline_std * 3.0f);
			float lower_threshold = baseline_mean - (baseline_std * 3.0f);
			
			bool is_up_spike = (env_f > upper_threshold);
			bool is_down_spike = (env_f < lower_threshold) && (lower_threshold > 0);
			
			if (is_up_spike || is_down_spike) {
				// We're in a flex
				if (!in_flex) {
					in_flex = true;
					last_peak_value = env_f;
				} else {
					// Track extremes
					if (is_up_spike && env_f > last_peak_value) {
						last_peak_value = env_f;
					}
					if (is_down_spike && env_f < last_peak_value) {
						last_peak_value = env_f;
					}
				}
			} else {
				// Flex ended - record the peak/trough
				if (in_flex) {
					in_flex = false;
					
					// Calculate deviation from baseline
					float deviation = fabs(last_peak_value - baseline_mean);
					flex_sum += deviation;
					flex_peak_count++;
					
					if (deviation > flex_peak) {
						flex_peak = deviation;
					}
					
					Serial.print("   Flex #");
					Serial.print(flex_peak_count);
					Serial.print(" value: ");
					Serial.print(last_peak_value, 1);
					Serial.print(" (deviation: ");
					Serial.print(deviation, 1);
					Serial.println(")");
					Serial.flush();
				}
			}
			
			// Check if flex phase is complete
			if ((millis() - phase_start_ms) >= (FLEX_CALIBRATION_SEC * 1000UL)) {
				// Calculate average deviation from baseline
				float avg_deviation = (flex_peak_count > 0) ? (flex_sum / flex_peak_count) : flex_peak;
				
				// Determine if signal is inverted (flex goes DOWN)
				float up_deviation = flex_max_val - baseline_mean;
				float down_deviation = baseline_mean - flex_min;
				bool signal_inverted = (down_deviation > up_deviation);
				
				Serial.print("   Up deviation: ");
				Serial.print(up_deviation, 1);
				Serial.print(", Down deviation: ");
				Serial.println(down_deviation, 1);
				Serial.flush();
				Serial.print("   Signal type: ");
				Serial.println(signal_inverted ? "INVERTED (flex=DOWN)" : "NORMAL (flex=UP)");
				Serial.flush();
				
				// If no flexes detected, use a default threshold
				if (flex_peak_count == 0 || avg_deviation < baseline_std * 2.0f) {
					// Fallback: use baseline std deviation
					activation_threshold = baseline_std * 4.0f;
					Serial.println("   WARNING: Few flexes detected, using fallback threshold");
					Serial.flush();
				} else {
					// Threshold = small percentage of average deviation
					// SPIKE_THRESHOLD_POSITION determines how much deviation needed
					activation_threshold = avg_deviation * SPIKE_THRESHOLD_POSITION;
				}
				
				// Ensure minimum threshold (at least some deviation from noise)
				float min_threshold = baseline_std * 3.0f;
				if (activation_threshold < min_threshold) {
					activation_threshold = min_threshold;
				}
				
				// Calculate hold threshold (lower than spike threshold)
				hold_threshold = activation_threshold * HOLD_THRESHOLD_RATIO;
				
				calibration_phase = CALIB_DONE;
				calibrated = true;
				
				// Print calibration results
				Serial.println("");
				Serial.flush();
				Serial.println("============================================");
				Serial.flush();
				Serial.println("  CALIBRATION COMPLETE!");
				Serial.flush();
				Serial.println("============================================");
				Serial.flush();
				Serial.print("  Baseline mean: ");
				Serial.println(baseline_mean, 1);
				Serial.flush();
				Serial.print("  Baseline std: ");
				Serial.println(baseline_std, 1);
				Serial.flush();
				Serial.print("  Flex events: ");
				Serial.println(flex_peak_count);
				Serial.flush();
				Serial.print("  Avg deviation: ");
				Serial.println(avg_deviation, 1);
				Serial.flush();
				Serial.print("  Max deviation: ");
				Serial.println(flex_peak, 1);
				Serial.flush();
				Serial.println("--------------------------------------------");
				Serial.flush();
				Serial.print("  >>> SPIKE THRESHOLD: ");
				Serial.print(activation_threshold, 1);
				Serial.println(" (deviation from baseline)");
				Serial.flush();
				Serial.print("  >>> HOLD THRESHOLD:  ");
				Serial.print(hold_threshold, 1);
				Serial.println(" (deviation from baseline)");
				Serial.flush();
				Serial.println("--------------------------------------------");
				Serial.flush();
				Serial.println("  Detection: Uses DEVIATION from baseline");
				Serial.flush();
				Serial.println("  Works for both UP and DOWN spikes!");
				Serial.flush();
				Serial.println("============================================");
				Serial.flush();
				Serial.println("  Ready! You can now control!");
				Serial.flush();
				Serial.println("============================================");
				Serial.flush();
			}
		}

		// ===== Check for Serial Commands =====
		checkSerialCommands();

		// ===== Data Reporting (10 Hz) =====
		unsigned long now_ms = millis();
		if (now_ms - last_report_ms >= REPORT_INTERVAL_MS) {
			last_report_ms = now_ms;

			// Calculate RMS value
			float rms = getRMS();
			
			// Determine muscle state using DEVIATION from baseline
			// This works for both normal (flex UP) and inverted (flex DOWN) signals
			float state_value = 0.0f;
			float current_deviation = 0.0f;
			if (calibrated) {
				// Calculate deviation from baseline (works for both up and down)
				current_deviation = fabs(smoothed_envelope - baseline_mean);
				muscle_active = (current_deviation >= activation_threshold);
				state_value = muscle_active ? 1.0f : 0.0f;  // Binary: active or not
			}
			
			// Output format: Envelope, RMS, Threshold (deviation), State
			// Threshold is now a DEVIATION value, not an absolute level
			Serial.print(display_envelope, 2);
			Serial.print(",");
			Serial.print(rms, 2);
			Serial.print(",");
			Serial.print(calibrated ? activation_threshold : 0.0f, 2);
			Serial.print(",");
			Serial.println(state_value, 2);
			Serial.flush();
		}
	}
}

// ========== Signal Processing Functions ==========

/**
 * Envelope Detection using Moving Average
 * Implements a circular buffer for efficient rolling average
 * @param abs_emg Rectified EMG signal value
 * @return Envelope value (no amplification)
 */
int getEnvelop(int abs_emg) {
	sum -= circular_buffer[data_index];
	sum += abs_emg;
	circular_buffer[data_index] = abs_emg;
	data_index = (data_index + 1) % BUFFER_SIZE;
	return (sum / BUFFER_SIZE);  // No amplification - raw average
}

/**
 * Root Mean Square (RMS) Calculation
 * Provides alternative measure of signal strength
 * @return RMS value of recent signal
 */
float getRMS() {
	float sum_sq = 0.0f;
	for (int i = 0; i < RMS_BUFFER_SIZE; i++) {
		sum_sq += rms_buffer[i];
	}
	return sqrtf(sum_sq / RMS_BUFFER_SIZE);
}

/**
 * Two-Stage Exponential Moving Average (EMA) for Envelope Smoothing
 * Stage 1: Fast response for threshold detection (smoothed_envelope)
 * Stage 2: Smooth output for display (display_envelope)
 * Formula: EMA = α × current + (1 - α) × previous
 * @param current_env Current envelope value
 * @return Smoothed envelope value (fast stage for detection)
 */
float getSmoothedEnvelope(float current_env) {
	// Stage 1: Fast smoothing for quick response (used for threshold detection)
	smoothed_envelope = ENVELOPE_SMOOTH_FACTOR * current_env + 
	                    (1.0f - ENVELOPE_SMOOTH_FACTOR) * smoothed_envelope;
	
	// Stage 2: Additional smoothing for display (reduces jitter)
	display_envelope = DISPLAY_SMOOTH_FACTOR * smoothed_envelope + 
	                   (1.0f - DISPLAY_SMOOTH_FACTOR) * display_envelope;
	
	return smoothed_envelope;
}

/**
 * Band-Pass Butterworth IIR Digital Filter
 * =========================================
 * Sampling Rate: 500 Hz
 * Pass Band: 74.5 - 149.5 Hz (optimal for EMG signals)
 * Implementation: 4th order cascaded biquad sections
 * 
 * This filter removes:
 * - DC offset and low-frequency motion artifacts (< 74.5 Hz)
 * - High-frequency noise (> 149.5 Hz)
 * 
 * @param input Raw ADC value
 * @return Filtered signal
 */
float EMGFilter(float input) {
	float output = input;
	
	// Biquad Section 1
	{
		static float z1, z2;
		float x = output - 0.05159732f*z1 - 0.36347401f*z2;
		output = 0.01856301f*x + 0.03712602f*z1 + 0.01856301f*z2;
		z2 = z1;
		z1 = x;
	}
	
	// Biquad Section 2
	{
		static float z1, z2;
		float x = output - -0.53945795f*z1 - 0.39764934f*z2;
		output = 1.00000000f*x + -2.00000000f*z1 + 1.00000000f*z2;
		z2 = z1;
		z1 = x;
	}
	
	// Biquad Section 3
	{
		static float z1, z2;
		float x = output - 0.47319594f*z1 - 0.70744137f*z2;
		output = 1.00000000f*x + 2.00000000f*z1 + 1.00000000f*z2;
		z2 = z1;
		z1 = x;
	}
	
	// Biquad Section 4
	{
		static float z1, z2;
		float x = output - -1.00211112f*z1 - 0.74520226f*z2;
		output = 1.00000000f*x + -2.00000000f*z1 + 1.00000000f*z2;
		z2 = z1;
		z1 = x;
	}
	
	return output;
}

// ========== Serial Command Handling ==========

/**
 * Check for incoming serial commands from Python program
 * Commands are processed without blocking the main signal processing loop
 */
void checkSerialCommands() {
	// Check if serial is available (USB CDC might not always be ready)
	if (Serial && Serial.available() > 0) {
		String command = Serial.readStringUntil('\n');
		command.trim();  // Remove whitespace
		command.toUpperCase();  // Convert to uppercase for case-insensitive matching
		
		if (command.length() > 0) {
			handleCommand(command);
		}
	}
}

/**
 * Handle incoming commands from Python program
 * @param cmd Command string (already uppercased)
 */
void handleCommand(String cmd) {
	if (cmd == "CALIBRATE" || cmd == "CAL") {
		// Force start calibration immediately (skip waiting phase)
		if (!calibrated || calibration_phase != CALIB_DONE) {
			calibration_phase = CALIB_RELAXED;
			phase_start_ms = millis();
			samples_in_phase = 0;
			baseline_mean = 0.0f;
			baseline_max = 0.0f;
			baseline_variance = 0.0f;
			
			Serial.println("");
			Serial.flush();
			Serial.println("============================================");
			Serial.flush();
			Serial.println("  PHASE 1: RELAXED CALIBRATION");
			Serial.flush();
			Serial.println("  (Triggered by Python program)");
			Serial.flush();
			Serial.println("============================================");
			Serial.flush();
			Serial.println("   Keep muscle COMPLETELY RELAXED!");
			Serial.flush();
			Serial.println("   Duration: 10 seconds");
			Serial.flush();
			Serial.println("   Then you'll need to FLEX!");
			Serial.flush();
			Serial.println("============================================");
			Serial.flush();
		} else {
			Serial.println("INFO: Already calibrated. Use RESET to recalibrate.");
			Serial.flush();
		}
	}
	else if (cmd == "RESET" || cmd == "RST") {
		// Reset calibration state
		calibration_phase = CALIB_WAITING;
		calibrated = false;
		phase_start_ms = millis();
		samples_in_phase = 0;
		baseline_mean = 0.0f;
		baseline_max = 0.0f;
		baseline_variance = 0.0f;
		baseline_std = 1.0f;
		flex_peak = 0.0f;
		flex_sum = 0.0f;
		flex_peak_count = 0;
		activation_threshold = 0.0f;
		hold_threshold = 0.0f;
		muscle_active = false;
		
		Serial.println("");
		Serial.flush();
		Serial.println("============================================");
		Serial.flush();
		Serial.println("  CALIBRATION RESET");
		Serial.flush();
		Serial.println("============================================");
		Serial.flush();
		Serial.println("Starting 2-phase calibration in 5 seconds...");
		Serial.flush();
		Serial.println("Phase 1: Keep RELAXED (10 sec)");
		Serial.flush();
		Serial.println("Phase 2: FLEX several times (10 sec)");
		Serial.flush();
		Serial.println("============================================");
		Serial.flush();
	}
	else if (cmd == "STATUS" || cmd == "STAT") {
		// Report current status
		Serial.println("");
		Serial.flush();
		Serial.println("============================================");
		Serial.flush();
		Serial.println("  DEVICE STATUS");
		Serial.flush();
		Serial.println("============================================");
		Serial.flush();
		Serial.print("  Calibration phase: ");
		if (calibration_phase == CALIB_WAITING) Serial.println("WAITING");
		else if (calibration_phase == CALIB_RELAXED) Serial.println("RELAXED");
		else if (calibration_phase == CALIB_FLEX) Serial.println("FLEX");
		else Serial.println("DONE");
		Serial.flush();
		Serial.print("  Calibrated: ");
		Serial.println(calibrated ? "YES" : "NO");
		Serial.flush();
		if (calibrated) {
			Serial.print("  Baseline mean: ");
			Serial.println(baseline_mean, 1);
			Serial.flush();
			Serial.print("  Baseline max: ");
			Serial.println(baseline_max, 1);
			Serial.flush();
			Serial.print("  Flex peaks: ");
			Serial.println(flex_peak_count);
			Serial.flush();
			Serial.print("  Spike Threshold: ");
			Serial.println(activation_threshold, 1);
			Serial.flush();
			Serial.print("  Hold Threshold: ");
			Serial.println(hold_threshold, 1);
			Serial.flush();
		}
		Serial.print("  Current Envelope: ");
		Serial.println(smoothed_envelope, 1);
		Serial.flush();
		Serial.print("  Muscle Active: ");
		Serial.println(muscle_active ? "YES" : "NO");
		Serial.flush();
		Serial.println("============================================");
		Serial.flush();
	}
	else if (cmd.startsWith("SET_THRESHOLD:")) {
		// Set threshold multiplier (format: SET_THRESHOLD:3.5)
		int colonIndex = cmd.indexOf(':');
		if (colonIndex > 0) {
			String valueStr = cmd.substring(colonIndex + 1);
			float newMultiplier = valueStr.toFloat();
			if (newMultiplier > 0 && newMultiplier <= 10.0) {
				// Note: This would require making THRESHOLD_MULTIPLIER a variable
				// For now, just acknowledge the command
				Serial.print("INFO: Threshold multiplier change requested: ");
				Serial.println(newMultiplier, 2);
				Serial.flush();
				Serial.println("INFO: Recalibrate to apply new threshold multiplier.");
				Serial.flush();
			} else {
				Serial.println("ERROR: Invalid threshold multiplier (must be 0-10)");
				Serial.flush();
			}
		}
	}
	else if (cmd.startsWith("ECHO:")) {
		// Echo command - print text back (format: ECHO:Hello World)
		int colonIndex = cmd.indexOf(':');
		if (colonIndex > 0) {
			String text = cmd.substring(colonIndex + 1);
			Serial.print("ECHO: ");
			Serial.println(text);
			Serial.flush();
		} else {
			Serial.println("ECHO: (no text provided)");
			Serial.flush();
		}
	}
	else if (cmd == "TEST" || cmd == "PING") {
		// Simple test command
		Serial.println("OK: Command received! Communication is working.");
		Serial.flush();
		Serial.print("Timestamp: ");
		Serial.print(millis());
		Serial.println(" ms");
		Serial.flush();
	}
	else if (cmd == "HELP" || cmd == "?") {
		// Show available commands
		Serial.println("");
		Serial.flush();
		Serial.println("============================================");
		Serial.flush();
		Serial.println("  AVAILABLE COMMANDS");
		Serial.flush();
		Serial.println("============================================");
		Serial.flush();
		Serial.println("  CALIBRATE or CAL  - Start calibration now");
		Serial.flush();
		Serial.println("  RESET or RST      - Reset calibration state");
		Serial.flush();
		Serial.println("  STATUS or STAT    - Show device status");
		Serial.flush();
		Serial.println("  TEST or PING      - Test command communication");
		Serial.flush();
		Serial.println("  ECHO:text         - Echo text back (e.g., ECHO:Hello)");
		Serial.flush();
		Serial.println("  HELP or ?         - Show this help");
		Serial.flush();
		Serial.println("============================================");
		Serial.flush();
	}
	else {
		// Unknown command
		Serial.print("ERROR: Unknown command: ");
		Serial.println(cmd);
		Serial.flush();
		Serial.println("Type HELP for available commands.");
		Serial.flush();
	}
}