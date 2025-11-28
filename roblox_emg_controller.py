"""
EMG Roblox Controller - WASD Control
======================================
Control Roblox game movement using EMG signals from ESP32-S3
Maps muscle activation patterns to WASD keyboard inputs

Hardware: Seeed XIAO ESP32S3 + EMG Candy (Upside Down Labs)

Group: DRIX REYES
Members: Gerold John Khaw, Miguel Mayor, Justin Nillasca, 
         Lawrence Retirado, Drix Reyes, Aira Ynte
Course: Digital Signal Processing
Section: CPE-4B
"""

import serial
import serial.tools.list_ports
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from pynput import keyboard
from pynput.keyboard import Key, Controller as KeyController
import sys
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from collections import deque
import numpy as np

# ========== Configuration ==========
BAUD_RATE = 115200
UPDATE_INTERVAL = 0.1  # Update every 100ms (10 Hz)

class EMGRobloxController:
    """EMG-based Roblox game controller with GUI"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("EMG Roblox Controller")
        self.root.geometry("1000x900")
        self.root.resizable(True, True)
        
        # Modern color scheme
        self.colors = {
            'bg': '#F5F7FA',
            'card_bg': '#FFFFFF',
            'primary': '#6366F1',
            'primary_hover': '#4F46E5',
            'success': '#10B981',
            'danger': '#EF4444',
            'warning': '#F59E0B',
            'text': '#1F2937',
            'text_light': '#6B7280',
            'border': '#E5E7EB',
            'accent': '#8B5CF6'
        }
        
        # Configure root background
        self.root.configure(bg=self.colors['bg'])
        
        # Serial connection
        self.ser = None
        self.port = None
        self.connected = False
        
        # Control state
        self.controller_enabled = False
        self.calibrated = False
        self.muscle_active = False
        
        # EMG data
        self.envelope = 0.0
        self.rms = 0.0
        self.threshold = 0.0
        self.state = 0.0
        self.invert_signal = False  # Invert signal if it spikes down on flex
        self.baseline_for_invert = 2048  # Mid-point for 12-bit ADC
        
        # Threshold settings
        # HOLD_THRESHOLD_RATIO: Hold detection uses a lower threshold
        # Lower ratio = easier to maintain A/D hold
        self.HOLD_THRESHOLD_RATIO = 0.4  # 40% of spike threshold for hold detection (easier A/D)
        self.hold_threshold = 0.0  # Will be calculated from threshold
        
        # Muscle state tracking
        self.muscle_spiking = False   # Above spike threshold (for detecting spikes)
        self.muscle_holding = False   # Above hold threshold (for maintaining A/D)
        self.prev_spike_state = False
        self.prev_hold_state = False
        
        # Graph data buffers
        self.MAX_GRAPH_POINTS = 200  # Display last 20 seconds (at 10 Hz)
        self.graph_time_data = deque(maxlen=self.MAX_GRAPH_POINTS)
        self.graph_envelope_data = deque(maxlen=self.MAX_GRAPH_POINTS)
        self.graph_threshold_data = deque(maxlen=self.MAX_GRAPH_POINTS)
        self.graph_hold_threshold_data = deque(maxlen=self.MAX_GRAPH_POINTS)  # Hold threshold
        self.graph_start_time = time.time()
        
        # Keyboard controller
        self.keyboard_controller = KeyController()
        self.pressed_keys = set()  # Track currently pressed keys
        
        # Key repeat for continuous input (games need repeated key presses)
        self.key_repeat_active = False
        self.key_repeat_char = None
        self.key_repeat_thread = None
        
        # Spike detection for pattern recognition
        self.spike_times = []  # Track spike timestamps for pattern detection
        self.last_spike_time = 0
        self.spike_count = 0
        self.prev_muscle_state = False
        self.hold_start_time = 0  # Track when hold started
        self.hold_key = None  # Track which key is being held
        
        # Control mapping
        self.current_direction = None  # 'W', 'S', 'A', 'D', or None
        
        # Pattern detection thresholds (time-based)
        self.INSTANT_THRESHOLD = 0.4  # Seconds - spikes within this are "instant"
        self.DELAYED_THRESHOLD = 1.0  # Seconds - spikes within this but > instant are "delayed"
        self.HOLD_TIME_THRESHOLD = 0.3  # Seconds - hold for this long to switch to A/D (reduced for easier A/D)
        
        # Threading
        self.serial_thread = None
        self.running = False
        
        # Setup GUI
        self.setup_gui()
        
    def setup_gui(self):
        """Setup the modern GUI interface"""
        # Main container with padding
        main_frame = tk.Frame(self.root, bg=self.colors['bg'], padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Header section
        header_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        header_frame.pack(fill=tk.X, pady=(0, 25))
        
        # Title and credits button row
        header_top = tk.Frame(header_frame, bg=self.colors['bg'])
        header_top.pack(fill=tk.X)
        
        title_label = tk.Label(header_top, text="EMG Roblox Controller", 
                              font=("Segoe UI", 24, "bold"), 
                              bg=self.colors['bg'], fg=self.colors['text'])
        title_label.pack(side=tk.LEFT)
        
        # Credits button (top right)
        credits_btn = self.create_button(header_top, "Credits", self.show_credits,
                                         style="default", width=8)
        credits_btn.pack(side=tk.RIGHT)
        
        subtitle_label = tk.Label(header_frame, text="Muscle-controlled WASD movement", 
                                 font=("Segoe UI", 11), 
                                 bg=self.colors['bg'], fg=self.colors['text_light'])
        subtitle_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Top row: Connection, Controller, Active Key (side by side)
        top_row = tk.Frame(main_frame, bg=self.colors['bg'])
        top_row.pack(fill=tk.X, pady=(0, 15))
        
        # Connection card
        conn_card = self.create_card(top_row)
        conn_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        conn_header = tk.Label(conn_card, text="Connection", 
                              font=("Segoe UI", 12, "bold"), 
                              bg=self.colors['card_bg'], fg=self.colors['text'])
        conn_header.pack(anchor=tk.W, pady=(0, 15))
        
        conn_content = tk.Frame(conn_card, bg=self.colors['card_bg'])
        conn_content.pack(fill=tk.X)
        
        port_label = tk.Label(conn_content, text="Port", 
                             font=("Segoe UI", 9), 
                             bg=self.colors['card_bg'], fg=self.colors['text_light'])
        port_label.pack(anchor=tk.W, pady=(0, 5))
        
        port_row = tk.Frame(conn_content, bg=self.colors['card_bg'])
        port_row.pack(fill=tk.X, pady=(0, 10))
        
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(port_row, textvariable=self.port_var, 
                                       state="readonly", font=("Segoe UI", 9),
                                       height=8)
        self.port_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        
        self.refresh_btn = self.create_button(port_row, "↻", self.refresh_ports, 
                                              style="default", width=3, height=1)
        self.refresh_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        self.connect_btn = self.create_button(port_row, "Connect", self.toggle_connection,
                                             style="primary", width=8)
        self.connect_btn.pack(side=tk.LEFT)
        
        self.connection_status = tk.Label(conn_content, text="● Disconnected", 
                                         font=("Segoe UI", 10, "bold"),
                                         bg=self.colors['card_bg'], fg=self.colors['danger'],
                                         width=20, anchor=tk.W)
        self.connection_status.pack(anchor=tk.W, pady=(5, 0))
        
        # Controller card
        control_card = self.create_card(top_row)
        control_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 10))
        
        control_header = tk.Label(control_card, text="Controller", 
                                font=("Segoe UI", 12, "bold"), 
                                bg=self.colors['card_bg'], fg=self.colors['text'])
        control_header.pack(anchor=tk.W, pady=(0, 15))
        
        control_content = tk.Frame(control_card, bg=self.colors['card_bg'])
        control_content.pack(fill=tk.X)
        
        btn_row = tk.Frame(control_content, bg=self.colors['card_bg'])
        btn_row.pack(fill=tk.X, pady=(0, 10))
        
        self.enable_btn = self.create_button(btn_row, "Enable Controller", 
                                            self.toggle_controller, 
                                            style="success", state="disabled")
        self.enable_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        self.calibrate_btn = self.create_button(btn_row, "Calibrate", 
                                                self.request_calibration, 
                                                state="disabled")
        self.calibrate_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        self.reset_btn = self.create_button(btn_row, "Reset", 
                                            self.reset_calibration, 
                                            state="disabled")
        self.reset_btn.pack(side=tk.LEFT)
        
        # Invert signal checkbox
        options_row = tk.Frame(control_content, bg=self.colors['card_bg'])
        options_row.pack(fill=tk.X, pady=(8, 5))
        
        self.invert_var = tk.BooleanVar(value=False)
        self.invert_checkbox = tk.Checkbutton(
            options_row, text="Invert Signal", 
            variable=self.invert_var,
            command=self.toggle_invert,
            font=("Segoe UI", 9),
            bg=self.colors['card_bg'], fg=self.colors['text'],
            activebackground=self.colors['card_bg'],
            selectcolor=self.colors['bg']
        )
        self.invert_checkbox.pack(side=tk.LEFT)
        
        self.invert_status = tk.Label(options_row, text="(Use if flex spikes DOWN)", 
                                     font=("Segoe UI", 8),
                                     bg=self.colors['card_bg'], fg=self.colors['text_light'])
        self.invert_status.pack(side=tk.LEFT, padx=(5, 0))
        
        self.controller_status = tk.Label(control_content, text="● Controller OFF", 
                                         font=("Segoe UI", 10, "bold"),
                                         bg=self.colors['card_bg'], fg=self.colors['danger'],
                                         width=18, anchor=tk.W)
        self.controller_status.pack(anchor=tk.W)
        
        # Active key card
        key_card = self.create_card(top_row)
        key_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(10, 0), ipadx=20)
        
        key_header = tk.Label(key_card, text="Direction", 
                             font=("Segoe UI", 12, "bold"), 
                             bg=self.colors['card_bg'], fg=self.colors['text'])
        key_header.pack(anchor=tk.W, pady=(0, 15))
        
        # Arrow display (large arrow symbol)
        self.active_key_display = tk.Label(key_card, text="•", 
                                          font=("Segoe UI", 52, "bold"),
                                          bg=self.colors['card_bg'], fg=self.colors['text_light'],
                                          width=3)
        self.active_key_display.pack(pady=(5, 0))
        
        # Subtle small letter label underneath
        self.active_key_label = tk.Label(key_card, text="", 
                                        font=("Segoe UI", 9),
                                        bg=self.colors['card_bg'], fg=self.colors['text_light'],
                                        width=10)
        self.active_key_label.pack(pady=(2, 5))
        
        # Second row: EMG Signal and Graph (side by side)
        signal_graph_row = tk.Frame(main_frame, bg=self.colors['bg'])
        signal_graph_row.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Signal card (left side) - fixed width to prevent layout shifts
        signal_card = self.create_card(signal_graph_row)
        signal_card.pack(side=tk.LEFT, fill=tk.Y, expand=False, padx=(0, 10))
        signal_card.configure(width=320)
        signal_card.pack_propagate(False)  # Keep fixed size
        
        signal_header = tk.Label(signal_card, text="EMG Signal", 
                                font=("Segoe UI", 12, "bold"), 
                                bg=self.colors['card_bg'], fg=self.colors['text'])
        signal_header.pack(anchor=tk.W, pady=(0, 15))
        
        signal_content = tk.Frame(signal_card, bg=self.colors['card_bg'])
        signal_content.pack(fill=tk.BOTH, expand=True)
        
        # Signal metrics - fixed width containers
        metrics_frame = tk.Frame(signal_content, bg=self.colors['card_bg'])
        metrics_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.envelope_label = self.create_metric_label(metrics_frame, "Envelope", "0.00", width=8)
        self.rms_label = self.create_metric_label(metrics_frame, "RMS", "0.00", width=8)
        self.threshold_label = self.create_metric_label(metrics_frame, "Threshold", "0.00", width=8)
        
        # Muscle state indicator
        state_frame = tk.Frame(signal_content, bg=self.colors['card_bg'])
        state_frame.pack(fill=tk.X, pady=(10, 0))
        
        state_label = tk.Label(state_frame, text="Muscle State", 
                              font=("Segoe UI", 9), 
                              bg=self.colors['card_bg'], fg=self.colors['text_light'])
        state_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.muscle_state_label = tk.Label(state_frame, text="● OFF", 
                                          font=("Segoe UI", 14, "bold"),
                                          bg=self.colors['card_bg'], fg=self.colors['success'],
                                          width=10, anchor=tk.W)
        self.muscle_state_label.pack(anchor=tk.W)
        
        # Graph card (right side)
        graph_card = self.create_card(signal_graph_row)
        graph_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        graph_header = tk.Label(graph_card, text="EMG Signal Graph", 
                               font=("Segoe UI", 12, "bold"), 
                               bg=self.colors['card_bg'], fg=self.colors['text'])
        graph_header.pack(anchor=tk.W, pady=(0, 10))
        
        # Create matplotlib figure
        self.setup_graph(graph_card)
        
        # Bottom: Control mapping, Serial Monitor, and Status Log
        bottom_row = tk.Frame(main_frame, bg=self.colors['bg'])
        bottom_row.pack(fill=tk.BOTH, expand=True)
        
        # Mapping card (left)
        mapping_card = self.create_card(bottom_row)
        mapping_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        mapping_header = tk.Label(mapping_card, text="Control Mapping", 
                                 font=("Segoe UI", 12, "bold"), 
                                 bg=self.colors['card_bg'], fg=self.colors['text'])
        mapping_header.pack(anchor=tk.W, pady=(0, 10))
        
        mapping_text = """Single Flex → ↑ (Forward) [Holds]
Double Flex → ↓ (Backward) [Holds]
Single + Hold → ← (Left) [Holds]
Double + Hold → → (Right) [Holds]
Triple Instant Flex → Stop
Release → Stop"""
        
        mapping_label = tk.Label(mapping_card, text=mapping_text, 
                               font=("Segoe UI", 9), 
                               bg=self.colors['card_bg'], fg=self.colors['text'],
                               justify=tk.LEFT, anchor=tk.W)
        mapping_label.pack(anchor=tk.W, padx=5)
        
        # Serial Monitor card (middle)
        serial_card = self.create_card(bottom_row)
        serial_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 10))
        
        serial_header = tk.Label(serial_card, text="Serial Monitor", 
                                 font=("Segoe UI", 12, "bold"), 
                                 bg=self.colors['card_bg'], fg=self.colors['text'])
        serial_header.pack(anchor=tk.W, pady=(0, 10))
        
        # Serial output display
        serial_container = tk.Frame(serial_card, bg=self.colors['card_bg'])
        serial_container.pack(fill=tk.BOTH, expand=True)
        
        self.serial_text = tk.Text(serial_container, height=8, wrap=tk.WORD, 
                                  font=("Consolas", 8),
                                  bg='#1E1E1E', fg='#D4D4D4',
                                  relief=tk.FLAT, borderwidth=0,
                                  padx=10, pady=10)
        self.serial_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        serial_scrollbar = ttk.Scrollbar(serial_container, orient=tk.VERTICAL, 
                                        command=self.serial_text.yview)
        serial_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.serial_text.configure(yscrollcommand=serial_scrollbar.set)
        
        # Status Log card (right)
        log_card = self.create_card(bottom_row)
        log_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        log_header = tk.Label(log_card, text="Status Log", 
                             font=("Segoe UI", 12, "bold"), 
                             bg=self.colors['card_bg'], fg=self.colors['text'])
        log_header.pack(anchor=tk.W, pady=(0, 10))
        
        log_container = tk.Frame(log_card, bg=self.colors['card_bg'])
        log_container.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(log_container, height=8, wrap=tk.WORD, 
                               font=("Consolas", 9),
                               bg='#FAFBFC', fg=self.colors['text'],
                               relief=tk.FLAT, borderwidth=0,
                               padx=10, pady=10)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(log_container, orient=tk.VERTICAL, 
                                 command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # Initial port refresh
        self.refresh_ports()
        
        # Log initial message
        self.log("Controller initialized. Connect to ESP32 to begin.")
    
    def show_credits(self):
        """Show credits in a popup window"""
        credits_window = tk.Toplevel(self.root)
        credits_window.title("Credits")
        credits_window.geometry("500x300")
        credits_window.resizable(False, False)
        credits_window.configure(bg=self.colors['bg'])
        
        # Center the window
        credits_window.transient(self.root)
        credits_window.grab_set()
        
        # Main frame
        main_frame = tk.Frame(credits_window, bg=self.colors['bg'], padx=30, pady=30)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(main_frame, text="Credits", 
                              font=("Segoe UI", 20, "bold"), 
                              bg=self.colors['bg'], fg=self.colors['text'])
        title_label.pack(pady=(0, 20))
        
        # Group name
        group_label = tk.Label(main_frame, text="Group: DRIX REYES", 
                              font=("Segoe UI", 14, "bold"),
                              bg=self.colors['bg'], fg=self.colors['primary'])
        group_label.pack(pady=(0, 15))
        
        # Members
        members_label = tk.Label(main_frame, 
                                text="Members:\n\nGerold John Khaw\nMiguel Mayor\nJustin Nillasca\nLawrence Retirado\nDrix Reyes\nAira Ynte",
                                font=("Segoe UI", 11),
                                bg=self.colors['bg'], fg=self.colors['text'],
                                justify=tk.LEFT)
        members_label.pack(pady=(0, 15))
        
        # Course info
        course_label = tk.Label(main_frame, 
                               text="Course: Digital Signal Processing\nSection: CPE-4B",
                               font=("Segoe UI", 10),
                               bg=self.colors['bg'], fg=self.colors['text_light'])
        course_label.pack(pady=(10, 0))
        
        # Close button
        close_btn = self.create_button(main_frame, "Close", credits_window.destroy,
                                       style="primary", width=10)
        close_btn.pack(pady=(20, 0))
    
    def create_card(self, parent):
        """Create a modern card container"""
        card = tk.Frame(parent, bg=self.colors['card_bg'], 
                       relief=tk.FLAT, padx=20, pady=20)
        # Add subtle shadow effect with border
        card.configure(highlightbackground=self.colors['border'], 
                      highlightthickness=1)
        return card
    
    def create_button(self, parent, text, command, style="default", 
                     state="normal", width=None, height=None):
        """Create a modern styled button"""
        if style == "primary":
            bg = self.colors['primary']
            fg = '#FFFFFF'
            hover_bg = self.colors['primary_hover']
            disabled_bg = '#9CA3AF'
        elif style == "success":
            bg = self.colors['success']
            fg = '#FFFFFF'
            hover_bg = '#059669'
            disabled_bg = '#9CA3AF'
        else:
            bg = self.colors['card_bg']
            fg = self.colors['text']
            hover_bg = self.colors['border']
            disabled_bg = '#F3F4F6'
        
        if state == "disabled":
            bg = disabled_bg
            fg = '#9CA3AF' if style != "default" else '#D1D5DB'
        
        btn = tk.Button(parent, text=text, command=command,
                       font=("Segoe UI", 9, "bold"),
                       bg=bg, fg=fg, 
                       relief=tk.FLAT,
                       cursor="hand2" if state == "normal" else "arrow",
                       padx=15, pady=8,
                       state=state,
                       width=width,
                       height=height if height else None,
                       activebackground=hover_bg if state == "normal" else bg,
                       activeforeground=fg if style != "default" else self.colors['text'],
                       disabledforeground=fg)
        
        # Store original colors for hover effects
        btn.original_bg = bg
        btn.original_hover = hover_bg
        
        # Hover effects
        def on_enter(e):
            if btn['state'] == 'normal':
                btn.config(bg=btn.original_hover)
        
        def on_leave(e):
            if btn['state'] == 'normal':
                btn.config(bg=btn.original_bg)
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn
    
    def create_metric_label(self, parent, label, value, width=8):
        """Create a metric display label with fixed width"""
        container = tk.Frame(parent, bg=self.colors['card_bg'], width=80)
        container.pack(side=tk.LEFT, padx=(0, 20))
        container.pack_propagate(False)  # Prevent container from shrinking
        
        label_widget = tk.Label(container, text=label, 
                               font=("Segoe UI", 8),
                               bg=self.colors['card_bg'], fg=self.colors['text_light'],
                               anchor=tk.W)
        label_widget.pack(anchor=tk.W, fill=tk.X)
        
        value_widget = tk.Label(container, text=value, 
                              font=("Segoe UI", 14, "bold"),
                              bg=self.colors['card_bg'], fg=self.colors['text'],
                              width=width, anchor=tk.W)
        value_widget.pack(anchor=tk.W, fill=tk.X)
        
        return value_widget
    
    def setup_graph(self, parent):
        """Setup the matplotlib graph for EMG visualization"""
        # Create matplotlib figure - taller for better visibility
        self.fig = Figure(figsize=(10, 4), facecolor=self.colors['card_bg'], dpi=80)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#FAFBFC')
        
        # Configure axes
        self.ax.set_xlabel('Time (seconds)', fontsize=9, color=self.colors['text_light'])
        self.ax.set_ylabel('Amplitude', fontsize=9, color=self.colors['text_light'])
        self.ax.set_title('EMG Signal - Spike & Hold Thresholds', fontsize=10, 
                         fontweight='bold', color=self.colors['text'], pad=10)
        
        # Style the axes
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_color(self.colors['border'])
        self.ax.spines['bottom'].set_color(self.colors['border'])
        self.ax.tick_params(colors=self.colors['text_light'], labelsize=8)
        self.ax.grid(True, alpha=0.3, color=self.colors['border'])
        
        # Initialize plot lines
        self.line_envelope, = self.ax.plot([], [], color=self.colors['primary'], 
                                           linewidth=2, label='EMG Signal', alpha=0.9)
        self.line_threshold, = self.ax.plot([], [], color=self.colors['danger'], 
                                            linestyle='--', linewidth=2, 
                                            label='Spike Threshold', alpha=0.8)
        self.line_hold_threshold, = self.ax.plot([], [], color=self.colors['warning'], 
                                                  linestyle=':', linewidth=2, 
                                                  label='Hold Threshold', alpha=0.8)
        
        # Add legend
        self.ax.legend(loc='upper right', fontsize=8, framealpha=0.9, 
                      facecolor=self.colors['card_bg'], 
                      edgecolor=self.colors['border'])
        
        # Embed in tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, parent)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tight layout with padding
        self.fig.tight_layout(pad=1.5)
        
    def refresh_ports(self):
        """Refresh available serial ports"""
        ports = serial.tools.list_ports.comports()
        port_list = [port.device for port in ports]
        self.port_combo['values'] = port_list
        if port_list and not self.port_var.get():
            self.port_var.set(port_list[0])
    
    def log(self, message):
        """Add message to log"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        # Limit log size to prevent memory issues
        if int(self.log_text.index('end-1c').split('.')[0]) > 100:
            self.log_text.delete('1.0', '20.0')
        self.root.update_idletasks()
    
    def toggle_connection(self):
        """Connect or disconnect from serial port"""
        if not self.connected:
            self.connect()
        else:
            self.disconnect()
    
    def connect(self):
        """Connect to ESP32"""
        port = self.port_var.get()
        if not port:
            messagebox.showerror("Error", "Please select a serial port!")
            return
        
        try:
            self.ser = serial.Serial(port, BAUD_RATE, timeout=1)
            time.sleep(2)  # Wait for connection
            self.ser.reset_input_buffer()
            
            self.port = port
            self.connected = True
            
            # Update UI
            self.connect_btn.config(text="Disconnect", bg=self.colors['danger'], 
                                   activebackground='#DC2626', 
                                   fg='#FFFFFF')
            self.connect_btn.original_bg = self.colors['danger']
            self.connect_btn.original_hover = '#DC2626'
            self.connection_status.config(text=f"● Connected: {port}", 
                                         fg=self.colors['success'])
            self.enable_btn.config(state="normal", bg=self.colors['success'],
                                  fg='#FFFFFF', cursor="hand2")
            self.enable_btn.original_bg = self.colors['success']
            self.enable_btn.original_hover = '#059669'
            self.calibrate_btn.config(state="normal", bg=self.colors['card_bg'],
                                    fg=self.colors['text'], cursor="hand2")
            self.calibrate_btn.original_bg = self.colors['card_bg']
            self.calibrate_btn.original_hover = self.colors['border']
            self.reset_btn.config(state="normal", bg=self.colors['card_bg'],
                                 fg=self.colors['text'], cursor="hand2")
            self.reset_btn.original_bg = self.colors['card_bg']
            self.reset_btn.original_hover = self.colors['border']
            
            # Reset graph data
            self.graph_time_data.clear()
            self.graph_envelope_data.clear()
            self.graph_threshold_data.clear()
            self.graph_hold_threshold_data.clear()
            self.graph_start_time = time.time()
            
            # Start serial reading thread
            self.running = True
            self.serial_thread = threading.Thread(target=self.serial_read_loop, daemon=True)
            self.serial_thread.start()
            
            self.log(f"Connected to {port}")
            
        except serial.SerialException as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {e}")
            self.log(f"Connection failed: {e}")
    
    def disconnect(self):
        """Disconnect from ESP32"""
        self.running = False
        
        # Release all keys
        self.release_all_keys()
        
        if self.controller_enabled:
            self.toggle_controller()
        
        if self.ser and self.ser.is_open:
            self.ser.close()
        
        self.connected = False
        self.ser = None
        
        # Update UI
        self.connect_btn.config(text="Connect", bg=self.colors['primary'],
                               activebackground=self.colors['primary_hover'],
                               fg='#FFFFFF')
        self.connect_btn.original_bg = self.colors['primary']
        self.connect_btn.original_hover = self.colors['primary_hover']
        self.connection_status.config(text="● Disconnected", fg=self.colors['danger'])
        self.enable_btn.config(state="disabled", bg='#9CA3AF', fg='#D1D5DB',
                               cursor="arrow")
        self.calibrate_btn.config(state="disabled", bg='#F3F4F6', fg='#D1D5DB',
                                  cursor="arrow")
        self.reset_btn.config(state="disabled", bg='#F3F4F6', fg='#D1D5DB',
                            cursor="arrow")
        
        self.log("Disconnected from ESP32")
    
    def toggle_controller(self):
        """Enable or disable controller"""
        if not self.controller_enabled:
            if not self.calibrated:
                response = messagebox.askyesno(
                    "Not Calibrated", 
                    "Controller is not calibrated. Do you want to enable anyway?"
                )
                if not response:
                    return
            
            self.controller_enabled = True
            self.enable_btn.config(text="Disable Controller", bg=self.colors['danger'],
                                  activebackground='#DC2626', fg='#FFFFFF')
            self.enable_btn.original_bg = self.colors['danger']
            self.enable_btn.original_hover = '#DC2626'
            self.controller_status.config(text="● Controller ON", fg=self.colors['success'])
            self.log("Controller ENABLED - Keys will be sent to Roblox")
        else:
            self.controller_enabled = False
            self.enable_btn.config(text="Enable Controller", bg=self.colors['success'],
                                  activebackground='#059669', fg='#FFFFFF')
            self.enable_btn.original_bg = self.colors['success']
            self.enable_btn.original_hover = '#059669'
            self.controller_status.config(text="● Controller OFF", fg=self.colors['danger'])
            self.release_all_keys()
            self.log("Controller DISABLED - All keys released")
    
    def toggle_invert(self):
        """Toggle signal inversion"""
        self.invert_signal = self.invert_var.get()
        if self.invert_signal:
            self.log("Signal INVERSION enabled - flex DOWN will register as UP")
            self.invert_status.config(text="✓ Inverted", fg=self.colors['success'])
        else:
            self.log("Signal INVERSION disabled - normal mode")
            self.invert_status.config(text="(Use if flex spikes DOWN)", fg=self.colors['text_light'])
    
    def request_calibration(self):
        """Request recalibration from Arduino"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to ESP32 first!")
            return
        
        # Send calibration command to ESP32
        try:
            self.ser.write(b"CALIBRATE\n")
            self.ser.flush()
            self.log("Calibration command sent to ESP32")
            messagebox.showinfo("Calibration", 
                               "Calibration command sent!\n"
                               "Keep muscle COMPLETELY RELAXED for 10 seconds.")
        except Exception as e:
            self.log(f"Error sending calibration command: {e}")
            messagebox.showerror("Error", f"Failed to send calibration command: {e}")
    
    def reset_calibration(self):
        """Reset calibration on ESP32"""
        if not self.connected:
            return
        
        try:
            self.ser.write(b"RESET\n")
            self.ser.flush()
            self.log("Reset command sent to ESP32")
        except Exception as e:
            self.log(f"Error sending reset command: {e}")
    
    def request_status(self):
        """Request status from ESP32"""
        if not self.connected:
            return
        
        try:
            self.ser.write(b"STATUS\n")
            self.ser.flush()
            self.log("Status command sent to ESP32")
        except Exception as e:
            self.log(f"Error sending status command: {e}")
    
    
    def append_serial(self, text):
        """Append text to serial monitor (thread-safe, simplified)"""
        try:
            if not hasattr(self, 'serial_text') or not self.serial_text.winfo_exists():
                return
            
            # Insert text
            self.serial_text.insert(tk.END, text + "\n")
            
            # Auto-scroll to bottom
            self.serial_text.see(tk.END)
            
            # Limit serial monitor size (keep last 300 lines)
            line_count = int(self.serial_text.index('end-1c').split('.')[0])
            if line_count > 300:
                self.serial_text.delete('1.0', f'{line_count - 300}.0')
        except:
            # Silently handle errors to prevent crashes
            pass
    
    def release_all_keys(self):
        """Release all currently pressed keys"""
        # Stop key repeat first
        self.stop_key_repeat()
        
        keys_to_release = list(self.pressed_keys)
        for key in keys_to_release:
            try:
                self.keyboard_controller.release(key)
                self.pressed_keys.discard(key)
                self.log(f"Released: {key}")
            except Exception as e:
                self.log(f"Error releasing {key}: {e}")
        self.current_direction = None
        # Don't clear hold_key here - let the control logic handle it
    
    def press_key(self, key_char):
        """Press a key (W, A, S, or D)"""
        # Release any other keys first
        for key in list(self.pressed_keys):
            if key != key_char:
                try:
                    self.keyboard_controller.release(key)
                    self.pressed_keys.discard(key)
                except:
                    pass
        
        # Press the new key if not already pressed
        if key_char not in self.pressed_keys:
            try:
                self.keyboard_controller.press(key_char)
                self.pressed_keys.add(key_char)
                self.current_direction = key_char.upper()
                self.log(f"KEY PRESSED: {key_char.upper()}")
                # Start key repeat thread
                self.start_key_repeat(key_char)
            except Exception as e:
                self.log(f"ERROR pressing {key_char}: {e}")
    
    def start_key_repeat(self, key_char):
        """Start repeating key presses for continuous input"""
        # Stop any existing repeat
        self.stop_key_repeat()
        
        self.key_repeat_active = True
        self.key_repeat_char = key_char
        
        def repeat_loop():
            """Continuously press key until stopped"""
            while self.key_repeat_active and key_char in self.pressed_keys:
                try:
                    # Release and re-press to simulate continuous input
                    self.keyboard_controller.release(key_char)
                    time.sleep(0.01)  # Small gap
                    self.keyboard_controller.press(key_char)
                    time.sleep(0.05)  # 50ms = 20 key presses per second
                except:
                    break
        
        self.key_repeat_thread = threading.Thread(target=repeat_loop, daemon=True)
        self.key_repeat_thread.start()
    
    def stop_key_repeat(self):
        """Stop key repeat thread"""
        self.key_repeat_active = False
        if hasattr(self, 'key_repeat_thread') and self.key_repeat_thread:
            self.key_repeat_thread = None
    
    def map_signal_to_controls(self):
        """
        Map EMG signal to WASD controls with TWO-LEVEL THRESHOLD
        
        Spike Threshold (high): For detecting new spikes
        Hold Threshold (low, 50% of spike): For maintaining A/D commands
        
        Control Mapping:
        - 1 spike → W (Forward) - holds indefinitely until 3 spikes to stop
        - 2 spikes → S (Backward) - holds until new command
        - 1 spike + hold muscle → A (Left) - holds while muscle held
        - 2 spikes + hold muscle → D (Right) - holds while muscle held  
        - 3 spikes → STOP all movement
        - New command automatically replaces current command (no need to stop first)
        """
        if not self.controller_enabled:
            return
        
        if not self.calibrated:
            if hasattr(self, '_last_calib_warning') and time.time() - self._last_calib_warning < 5:
                return
            self._last_calib_warning = time.time()
            self.log(f"Waiting for calibration... (threshold={self.threshold:.2f})")
            return
        
        current_time = time.time()
        
        # Spike detection uses HIGH threshold
        spike_just_detected = self.muscle_spiking and not self.prev_spike_state
        spike_just_ended = not self.muscle_spiking and self.prev_spike_state
        
        # Hold detection uses LOW threshold (easier to maintain)
        hold_active = self.muscle_holding
        hold_just_released = not self.muscle_holding and self.prev_hold_state
        
        # Initialize tracking variables if not exist
        if not hasattr(self, 'indefinite_hold'):
            self.indefinite_hold = False  # True for W/S (holds until new command)
        if not hasattr(self, 'pending_spike_count'):
            self.pending_spike_count = 0  # Count spikes before deciding action
        if not hasattr(self, 'first_spike_time'):
            self.first_spike_time = 0
        if not hasattr(self, 'action_decided'):
            self.action_decided = False  # Whether we've decided on an action
        
        SPIKE_WINDOW = 0.5  # Window to count spikes (0.5 second - must be fast!)
        HOLD_DELAY = 0.25   # Time after first spike to detect hold (reduced for easier A/D)
        
        # ===== New spike detected - always count it =====
        if spike_just_detected:
            self.spike_times.append(current_time)
            self.spike_times = [t for t in self.spike_times if current_time - t < SPIKE_WINDOW]
            
            # 3 spikes = STOP
            if len(self.spike_times) >= 3:
                self.log(">>> STOP! (3 spikes)")
                self.release_all_keys()
                self.hold_key = None
                self.indefinite_hold = False
                self.pending_spike_count = 0
                self.action_decided = False
                self.spike_times = []
                return
            
            # Start new pattern (even if currently holding a command)
            self.pending_spike_count = len(self.spike_times)
            self.action_decided = False  # Allow new action decision
            
            if self.pending_spike_count == 1:
                self.first_spike_time = current_time
            
            self.log(f">>> SPIKE #{self.pending_spike_count} (Env={self.envelope:.0f})")
        
        # ===== Check for action decision =====
        if self.pending_spike_count > 0 and not self.action_decided:
            time_since_first = current_time - self.first_spike_time
            
            # After HOLD_DELAY, decide based on whether still holding
            if time_since_first > HOLD_DELAY:
                if hold_active:
                    # User is HOLDING → A or D (hold for 1 sec to lock)
                    if self.pending_spike_count == 1:
                        self.log(">>> A (Left) - hold 1s to lock")
                        self.press_key('a')
                        self.hold_key = 'a'
                        self.indefinite_hold = False
                        self.hold_lock_time = current_time  # Track when hold started
                    elif self.pending_spike_count >= 2:
                        self.log(">>> D (Right) - hold 1s to lock")
                        self.press_key('d')
                        self.hold_key = 'd'
                        self.indefinite_hold = False
                        self.hold_lock_time = current_time  # Track when hold started
                    self.action_decided = True
                    self.pending_spike_count = 0
                else:
                    # User RELEASED → W or S (indefinite)
                    if self.pending_spike_count == 1:
                        self.log(">>> W (Forward) - holds until new command")
                        self.press_key('w')
                        self.hold_key = 'w'
                        self.indefinite_hold = True
                    elif self.pending_spike_count >= 2:
                        self.log(">>> S (Backward) - holds until new command")
                        self.press_key('s')
                        self.hold_key = 's'
                        self.indefinite_hold = True
                    self.action_decided = True
                    self.pending_spike_count = 0
                    self.spike_times = []
        
        # ===== A/D Lock Check: After 0.6 seconds of holding, lock it =====
        HOLD_LOCK_DURATION = 0.6  # Hold for 0.6 second to lock A/D (reduced for easier locking)
        if self.hold_key in ['a', 'd'] and not self.indefinite_hold:
            if hasattr(self, 'hold_lock_time'):
                if hold_active and (current_time - self.hold_lock_time) >= HOLD_LOCK_DURATION:
                    self.indefinite_hold = True
                    self.log(f">>> {self.hold_key.upper()} LOCKED! (held 1s)")
        
        # ===== Release A/D when muscle releases (only if not locked) =====
        if hold_just_released and self.hold_key in ['a', 'd'] and not self.indefinite_hold:
            self.log("Released A/D (not locked)")
            self.release_all_keys()
            self.hold_key = None
            self.action_decided = False
        
        # Clean up old spikes (keep 2 second history for triple-spike detection)
        if len(self.spike_times) > 0:
            self.spike_times = [t for t in self.spike_times if current_time - t < 2.0]
    
    def serial_read_loop(self):
        """Read serial data in background thread"""
        while self.running and self.connected:
            try:
                if self.ser and self.ser.in_waiting:
                    line = self.ser.readline().decode('utf-8').strip()
                    
                    if not line:
                        continue
                    
                    # Check if this is EMG data (CSV format: Envelope,RMS,Threshold,State)
                    is_emg_data = False
                    if ',' in line:
                        parts = line.split(',')
                        if len(parts) == 4:
                            try:
                                # Try to parse as numbers
                                float(parts[0])
                                float(parts[1])
                                float(parts[2])
                                float(parts[3])
                                is_emg_data = True
                            except ValueError:
                                is_emg_data = False
                    
                    # Show ALL non-EMG data in serial monitor (like Arduino IDE)
                    if not is_emg_data:
                        line_copy = line
                        self.root.after(0, lambda l=line_copy: self.append_serial(l))
                    
                    # Process EMG data
                    if is_emg_data:
                        # EMG data: Envelope, RMS, Threshold (deviation), State (binary)
                        parts = line.split(',')
                        try:
                            raw_envelope = float(parts[0])
                            self.rms = float(parts[1])
                            self.threshold = float(parts[2])  # Now a deviation value
                            self.state = float(parts[3])      # Binary: 1=active, 0=inactive
                            
                            # Track baseline using exponential moving average (when not active)
                            if not hasattr(self, 'tracked_baseline'):
                                self.tracked_baseline = raw_envelope
                            if self.state == 0:  # Only update baseline when relaxed
                                self.tracked_baseline = 0.95 * self.tracked_baseline + 0.05 * raw_envelope
                            
                            # Apply signal inversion if enabled (just for display)
                            if self.invert_signal:
                                self.envelope = 2 * self.tracked_baseline - raw_envelope
                            else:
                                self.envelope = raw_envelope
                            
                            # Check calibration
                            if self.threshold > 0 and not self.calibrated:
                                self.calibrated = True
                                # Hold threshold as ratio of spike threshold (deviation)
                                self.hold_threshold = self.threshold * self.HOLD_THRESHOLD_RATIO
                                self.root.after(0, lambda: self.log("✓ Calibration complete!"))
                                self.root.after(0, lambda t=self.threshold, h=self.hold_threshold: 
                                    self.log(f"   Spike threshold: {t:.1f} (deviation)"))
                                self.root.after(0, lambda h=self.hold_threshold: 
                                    self.log(f"   Hold threshold: {h:.1f} (deviation)"))
                            
                            # Update hold threshold whenever spike threshold changes
                            if self.threshold > 0:
                                self.hold_threshold = self.threshold * self.HOLD_THRESHOLD_RATIO
                            
                            # MUSCLE STATE DETECTION (using deviation)
                            prev_active = self.muscle_active
                            self.prev_spike_state = self.muscle_spiking
                            self.prev_hold_state = self.muscle_holding
                            
                            # Use ESP32's state for spike detection (it uses deviation internally)
                            self.muscle_spiking = (self.state > 0)
                            self.muscle_active = self.muscle_spiking
                            
                            # Calculate current deviation for hold detection
                            current_deviation = abs(raw_envelope - self.tracked_baseline)
                            self.muscle_holding = (current_deviation >= self.hold_threshold) if self.hold_threshold > 0 else False
                            
                            # Debug: Log threshold states
                            if self.threshold > 0:
                                spike_ratio = self.envelope / self.threshold
                                hold_ratio = self.envelope / self.hold_threshold if self.hold_threshold > 0 else 0
                                if spike_ratio > 0.7 and not self.muscle_spiking:
                                    if not hasattr(self, '_last_ratio_log') or time.time() - self._last_ratio_log > 1:
                                        self._last_ratio_log = time.time()
                                        self.root.after(0, lambda r=spike_ratio, e=self.envelope, t=self.threshold: 
                                            self.log(f"Near spike: {r*100:.0f}% (Env={e:.1f}, Thr={t:.1f})"))
                            
                            # Add to graph buffers
                            current_time_rel = time.time() - self.graph_start_time
                            self.graph_time_data.append(current_time_rel)
                            self.graph_envelope_data.append(self.envelope)
                            
                            # Threshold lines: show as baseline ± deviation
                            # For display, we show upper threshold (baseline + deviation)
                            spike_level = (self.tracked_baseline + self.threshold) if self.threshold > 0 else 0
                            hold_level = (self.tracked_baseline + self.hold_threshold) if self.hold_threshold > 0 else 0
                            self.graph_threshold_data.append(spike_level)
                            self.graph_hold_threshold_data.append(hold_level)
                            
                            # Update GUI (thread-safe)
                            self.root.after(0, self.update_gui)
                            self.root.after(0, self.update_graph)
                            
                            # Map to controls
                            if self.controller_enabled:
                                self.root.after(0, self.map_signal_to_controls)
                                
                        except ValueError:
                            # If parsing failed, show in serial monitor anyway
                            line_copy = line
                            self.root.after(0, lambda l=line_copy: self.append_serial(l))
                            
            except (UnicodeDecodeError, serial.SerialException) as e:
                if self.running:
                    error_msg = f"Serial error: {e}"
                    self.root.after(0, lambda msg=error_msg: self.log(msg))
                time.sleep(0.1)
            except Exception as e:
                if self.running:
                    error_msg = f"Unexpected error: {e}"
                    self.root.after(0, lambda msg=error_msg: self.log(msg))
                time.sleep(0.1)
            
            time.sleep(0.01)  # Small delay to prevent CPU spinning
    
    def update_gui(self):
        """Update GUI elements with current data"""
        # Update signal metric labels
        self.envelope_label.config(text=f"{self.envelope:.2f}")
        self.rms_label.config(text=f"{self.rms:.2f}")
        self.threshold_label.config(text=f"{self.threshold:.2f}")
        
        # Update muscle state
        if self.muscle_active:
            self.muscle_state_label.config(text="● ON", fg=self.colors['danger'])
        else:
            self.muscle_state_label.config(text="● OFF", fg=self.colors['success'])
        
        # Update active key display with arrows and subtle letters
        # Arrow mapping: W=↑, S=↓, A=←, D=→
        arrow_map = {'W': '↑', 'S': '↓', 'A': '←', 'D': '→'}
        if self.current_direction:
            key_upper = self.current_direction.upper()
            arrow = arrow_map.get(key_upper, '•')
            self.active_key_display.config(text=arrow, fg=self.colors['primary'])
            self.active_key_label.config(text=key_upper.lower(), fg=self.colors['text_light'])
        else:
            self.active_key_display.config(text="•", fg=self.colors['text_light'])
            self.active_key_label.config(text="", fg=self.colors['text_light'])
    
    def update_graph(self):
        """Update the EMG signal graph"""
        if len(self.graph_time_data) == 0:
            return
        
        try:
            # Convert to numpy arrays for plotting
            time_array = np.array(self.graph_time_data)
            envelope_array = np.array(self.graph_envelope_data)
            threshold_array = np.array(self.graph_threshold_data)
            hold_threshold_array = np.array(self.graph_hold_threshold_data)
            
            # Update plot data
            self.line_envelope.set_data(time_array, envelope_array)
            
            # Only show thresholds if calibrated
            if self.calibrated and len(threshold_array) > 0:
                self.line_threshold.set_data(time_array, threshold_array)
                self.line_hold_threshold.set_data(time_array, hold_threshold_array)
            else:
                self.line_threshold.set_data([], [])
                self.line_hold_threshold.set_data([], [])
            
            # Auto-scale axes
            if len(time_array) > 0:
                self.ax.set_xlim(max(0, time_array[-1] - 20), max(20, time_array[-1] + 1))
                
                # Set y-axis limits based on data
                if len(envelope_array) > 0:
                    y_min = 0  # Always start at 0
                    y_max = max(np.max(envelope_array) * 1.2, 
                               np.max(threshold_array) * 1.2 if self.calibrated else np.max(envelope_array) * 1.2)
                    self.ax.set_ylim(y_min, max(y_max, 50))  # Ensure minimum range
            
            # Redraw canvas
            self.canvas.draw_idle()
            
        except Exception as e:
            # Silently handle graph update errors to avoid disrupting the main app
            pass
    
    def on_closing(self):
        """Handle window closing"""
        if self.controller_enabled:
            self.release_all_keys()
        self.disconnect()
        self.root.destroy()

def main():
    """Main entry point"""
    root = tk.Tk()
    app = EMGRobloxController(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()

