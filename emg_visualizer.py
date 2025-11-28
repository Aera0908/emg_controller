"""
EMG Signal Visualizer - ON/OFF Detection
=========================================
Real-time visualization of EMG signals from ESP32S3
Shows muscle activation state (ON/OFF) based on adaptive threshold

Author: EMG Project Team
"""

import serial
import serial.tools.list_ports
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.gridspec import GridSpec
from collections import deque
import numpy as np
import sys
import time

# ========== Configuration ==========
BAUD_RATE = 115200
MAX_POINTS = 500  # Display last 50 seconds (500 points at 10 Hz)
UPDATE_INTERVAL = 20  # Update plot every 20ms for smooth animation

class EMGVisualizer:
    """Real-time EMG signal visualizer with ON/OFF state detection"""
    
    def __init__(self, port=None):
        self.port = port
        self.ser = None
        
        # Data buffers (circular queues with maximum length)
        self.time_data = deque(maxlen=MAX_POINTS)
        self.envelope_data = deque(maxlen=MAX_POINTS)
        self.rms_data = deque(maxlen=MAX_POINTS)
        self.threshold_data = deque(maxlen=MAX_POINTS)
        self.state_data = deque(maxlen=MAX_POINTS)
        
        # Status flags
        self.calibrated = False
        self.muscle_on = False
        self.start_time = time.time()
        
        # Spike detection for command recognition
        self.last_spike_time = 0
        self.spike_count = 0
        self.current_command = "IDLE"
        self.command_display_time = 0
        self.prev_muscle_state = False
        
        # Setup plot
        self.setup_plot()
        
    def list_ports(self):
        """List all available serial ports"""
        ports = serial.tools.list_ports.comports()
        print("\n=== Available Serial Ports ===")
        for i, port in enumerate(ports):
            print(f"{i+1}. {port.device} - {port.description}")
        return ports
    
    def connect(self):
        """Connect to ESP32S3"""
        if self.port is None:
            ports = self.list_ports()
            if not ports:
                print("❌ No serial ports found!")
                sys.exit(1)
            
            try:
                choice = int(input("\nSelect port number: ")) - 1
                self.port = ports[choice].device
            except (ValueError, IndexError):
                print("❌ Invalid selection!")
                sys.exit(1)
        
        try:
            print(f"\n🔌 Connecting to {self.port}...")
            self.ser = serial.Serial(self.port, BAUD_RATE, timeout=1)
            time.sleep(2)  # Wait for connection
            
            # Clear buffer
            self.ser.reset_input_buffer()
            
            print("✅ Connected successfully!")
            print("📊 Starting visualization...\n")
            return True
        except serial.SerialException as e:
            print(f"❌ Connection failed: {e}")
            sys.exit(1)
    
    def setup_plot(self):
        """Setup the matplotlib figure and axes"""
        # Set white background with orange accents
        plt.style.use('default')
        
        # Create figure with GridSpec for organized layout
        self.fig = plt.figure(figsize=(16, 10), facecolor='white')
        self.fig.patch.set_facecolor('white')
        
        # Add title and project info at the top (fixed spacing)
        title_text = 'EMG-based Interface Controller'
        info_text = 'Project in DSP | by: Group 6'
        
        self.fig.text(0.5, 0.98, title_text, 
                     fontsize=20, fontweight='bold', 
                     ha='center', va='top',
                     color='#FF6B35')  # Orange color
        
        self.fig.text(0.5, 0.945, info_text, 
                     fontsize=11, 
                     ha='center', va='top',
                     color='#555555')
        
        gs = GridSpec(4, 3, figure=self.fig, 
                     hspace=0.35, wspace=0.3,
                     top=0.91, bottom=0.06, left=0.08, right=0.96)
        
        # Main signal plot (top, spans both columns)
        self.ax_main = self.fig.add_subplot(gs[0:2, :])
        self.ax_main.set_title('EMG Envelope & Activation Threshold', 
                               fontsize=12, fontweight='bold', color='#FF6B35')
        self.ax_main.set_xlabel('Time (seconds)', fontsize=10)
        self.ax_main.set_ylabel('Signal Amplitude', fontsize=10)
        self.ax_main.set_facecolor('#FFFAF7')  # Very light orange/white
        self.ax_main.grid(True, alpha=0.3, color='#FFB088')
        self.ax_main.spines['top'].set_color('#FF6B35')
        self.ax_main.spines['bottom'].set_color('#FF6B35')
        self.ax_main.spines['left'].set_color('#FF6B35')
        self.ax_main.spines['right'].set_color('#FF6B35')
        self.ax_main.spines['top'].set_linewidth(2)
        self.ax_main.spines['bottom'].set_linewidth(2)
        self.ax_main.spines['left'].set_linewidth(2)
        self.ax_main.spines['right'].set_linewidth(2)
        
        # State indicator plot (middle left)
        self.ax_state = self.fig.add_subplot(gs[2, 0])
        self.ax_state.set_title('Muscle State', fontsize=11, fontweight='bold', color='#FF6B35')
        self.ax_state.set_xlim(0, 1)
        self.ax_state.set_ylim(0, 2)
        self.ax_state.set_yticks([0.5, 1.5])
        self.ax_state.set_yticklabels(['OFF', 'ON'])
        self.ax_state.set_xticks([])
        self.ax_state.set_facecolor('#FFFAF7')
        self.ax_state.grid(True, alpha=0.3, axis='y', color='#FFB088')
        for spine in self.ax_state.spines.values():
            spine.set_color('#FF6B35')
            spine.set_linewidth(2)
        
        # Command display panel (middle center)
        self.ax_command = self.fig.add_subplot(gs[2, 1])
        self.ax_command.set_title('Active Command', fontsize=11, fontweight='bold', color='#FF6B35')
        self.ax_command.set_xlim(0, 1)
        self.ax_command.set_ylim(0, 1)
        self.ax_command.set_facecolor('#FFF5EE')
        self.ax_command.axis('off')
        for spine in self.ax_command.spines.values():
            spine.set_color('#FF6B35')
            spine.set_linewidth(2)
            spine.set_visible(True)
        
        # Statistics panel (middle right)
        self.ax_stats = self.fig.add_subplot(gs[2, 2])
        self.ax_stats.set_title('Signal Statistics', fontsize=11, fontweight='bold', color='#FF6B35')
        self.ax_stats.set_facecolor('#FFFAF7')
        self.ax_stats.axis('off')
        
        # Spike pattern info panel (bottom, spans both columns)
        self.ax_info = self.fig.add_subplot(gs[3, :])
        self.ax_info.set_title('Spike Pattern Guide', fontsize=11, fontweight='bold', color='#FF6B35')
        self.ax_info.set_xlim(0, 1)
        self.ax_info.set_ylim(0, 1)
        self.ax_info.set_facecolor('#FFF5EE')  # Light peach/white
        self.ax_info.axis('off')
        for spine in self.ax_info.spines.values():
            spine.set_color('#FF6B35')
            spine.set_linewidth(2)
            spine.set_visible(True)
        
        # Initialize lines for main plot (orange color scheme)
        self.line_envelope, = self.ax_main.plot([], [], color='#FF6B35', linewidth=2.5, 
                                                label='EMG Envelope', alpha=0.9)
        self.line_rms, = self.ax_main.plot([], [], color='#FFB088', linewidth=1.5, 
                                           label='RMS Value', alpha=0.7)
        self.line_threshold, = self.ax_main.plot([], [], color='#C44C2A', linestyle='--', linewidth=2.5, 
                                                 label='Activation Threshold', alpha=0.8)
        
        legend = self.ax_main.legend(loc='upper right', fontsize=10, 
                                     framealpha=0.9, facecolor='white', 
                                     edgecolor='#FF6B35', frameon=True)
        legend.get_frame().set_linewidth(2)
        
        # State indicator bars (OFF=light orange, ON=dark orange)
        self.state_bar = self.ax_state.barh([0.5, 1.5], [0, 0], 
                                           color=['#FFD4B8', '#FF6B35'],
                                           alpha=0.8, height=0.8)
        
        # Command display text
        self.command_text = self.ax_command.text(0.5, 0.5, 'IDLE', 
                                                fontsize=24, 
                                                ha='center', va='center',
                                                fontweight='bold',
                                                color='#999999')
        
        # Statistics text display
        self.stats_text = self.ax_stats.text(0.1, 0.5, '', fontsize=9, 
                                            verticalalignment='center',
                                            fontfamily='monospace',
                                            color='#333333')
        
        # Spike pattern info text
        info_text = """📈 ONE SPIKE = ↑ (w)     |     📉 TWO SPIKES (short time) = ↓ (s)"""
        self.info_text = self.ax_info.text(0.5, 0.5, info_text, 
                                          fontsize=12, 
                                          ha='center', va='center',
                                          fontweight='bold',
                                          color='#FF6B35',
                                          bbox=dict(boxstyle='round,pad=0.8', 
                                                   facecolor='white', 
                                                   edgecolor='#FF6B35',
                                                   linewidth=2))
    
    def update_plot(self, frame):
        """Update plot with new data from serial port"""
        if self.ser is None or not self.ser.is_open:
            return
        
        # Read all available lines from serial buffer
        while self.ser.in_waiting:
            try:
                line = self.ser.readline().decode('utf-8').strip()
                
                # Skip header, separator, and informational lines
                skip_keywords = ['=', '✓', '⏳', 'Keep', 'Baseline', 'Activation', 
                                'Threshold', 'Ready', 'CALIBRATION', 'NOT', 'EMG', 
                                'Do', 'Complete']
                if not line or any(keyword in line for keyword in skip_keywords):
                    continue
                
                # Parse data: Envelope,RMS,Threshold,State
                parts = line.split(',')
                if len(parts) == 4:
                    try:
                        envelope = float(parts[0])
                        rms = float(parts[1])
                        threshold = float(parts[2])
                        state = float(parts[3])
                        
                        # Add to data buffers
                        current_time = time.time() - self.start_time
                        self.time_data.append(current_time)
                        self.envelope_data.append(envelope)
                        self.rms_data.append(rms)
                        self.threshold_data.append(threshold)
                        self.state_data.append(state)
                        
                        # Check if calibration is complete
                        if threshold > 0 and not self.calibrated:
                            self.calibrated = True
                            print("✅ Calibration complete! You can now flex your muscle.")
                        
                        # Determine current state (ON if state value is non-zero)
                        self.muscle_on = (state > 0)
                        
                        # Spike detection for command recognition (rising edge detection)
                        if self.calibrated and self.muscle_on and not self.prev_muscle_state:
                            # Rising edge detected (muscle just turned ON)
                            current_spike_time = current_time
                            
                            # Check if this is a second spike within 1 second
                            if self.spike_count > 0 and (current_spike_time - self.last_spike_time) < 1.0:
                                # Two spikes within short time = DOWN command
                                self.current_command = "DOWN"
                                self.command_display_time = current_time
                                self.spike_count = 0  # Reset counter
                                print("📉 Command: DOWN (double spike detected)")
                            else:
                                # Single spike = UP command
                                self.current_command = "UP"
                                self.command_display_time = current_time
                                self.spike_count = 1
                                print("📈 Command: UP (single spike detected)")
                            
                            self.last_spike_time = current_spike_time
                        
                        # Reset spike counter if too much time has passed
                        if self.spike_count > 0 and (current_time - self.last_spike_time) > 1.5:
                            self.spike_count = 0
                        
                        # Clear command display after 2 seconds
                        if self.current_command != "IDLE" and (current_time - self.command_display_time) > 2.0:
                            self.current_command = "IDLE"
                        
                        # Store previous state for edge detection
                        self.prev_muscle_state = self.muscle_on
                        
                    except ValueError:
                        continue
                        
            except (UnicodeDecodeError, serial.SerialException):
                continue
        
        # Update plots if we have data
        if len(self.time_data) > 0:
            time_array = np.array(self.time_data)
            
            # Update main signal plot
            self.line_envelope.set_data(time_array, np.array(self.envelope_data))
            self.line_rms.set_data(time_array, np.array(self.rms_data))
            
            # Update threshold line (only if calibrated)
            if self.calibrated:
                self.line_threshold.set_data(time_array, np.array(self.threshold_data))
            
            # Auto-scale axes for optimal viewing
            self.ax_main.relim()
            self.ax_main.autoscale_view()
            
            # Update state indicator (ON/OFF bars)
            if len(self.envelope_data) > 0 and len(self.threshold_data) > 0:
                # Determine current state: OFF (0) or ON (1)
                state_idx = 1 if self.muscle_on else 0
                
                # Update bar widths (only one active at a time)
                heights = [0, 0]
                heights[state_idx] = 1
                for bar, height in zip(self.state_bar, heights):
                    bar.set_width(height)
            
            # Update command display with arrows and subtle letters
            if self.current_command == "UP":
                self.command_text.set_text("↑\nw")
                self.command_text.set_color('#FF6B35')  # Orange
            elif self.current_command == "DOWN":
                self.command_text.set_text("↓\ns")
                self.command_text.set_color('#C44C2A')  # Dark orange
            else:
                self.command_text.set_text("•")
                self.command_text.set_color('#CCCCCC')  # Gray
            
            # Update statistics panel
            if len(self.envelope_data) >= 10:
                env_array = np.array(self.envelope_data)
                current_threshold = self.threshold_data[-1] if len(self.threshold_data) > 0 else 0
                
                stats_text = f"""
Envelope:     {env_array[-1]:.2f}
Average:      {np.mean(env_array):.2f}
Max:          {np.max(env_array):.2f}
Min:          {np.min(env_array):.2f}

RMS:          {self.rms_data[-1]:.2f}
Threshold:    {current_threshold:.2f}

State:        {'ON 🔴' if self.muscle_on else 'OFF 🟢'}
Calibrated:   {'✓' if self.calibrated else '...'}
Time:         {time_array[-1]:.1f}s
"""
                self.stats_text.set_text(stats_text)
        
        return self.line_envelope, self.line_rms, self.line_threshold
    
    def run(self):
        """Start the visualization"""
        self.connect()
        
        # Create animation
        ani = animation.FuncAnimation(
            self.fig, 
            self.update_plot,
            interval=UPDATE_INTERVAL,
            blit=False,
            cache_frame_data=False
        )
        
        # Show plot
        plt.tight_layout()
        plt.show()
        
        # Cleanup
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("\n👋 Connection closed.")

def main():
    """Main entry point"""
    print("=" * 50)
    print("  EMG Signal Visualizer")
    print("  ESP32S3 Real-Time Monitor")
    print("=" * 50)
    
    # Check if port specified as argument
    port = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        visualizer = EMGVisualizer(port=port)
        visualizer.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)

if __name__ == "__main__":
    main()

