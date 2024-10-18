import tkinter as tk
from tkinter import ttk, messagebox, font
import ttkbootstrap as ttkb
import threading
import pyautogui
import keyboard
import time
import random
from pystray import Icon, MenuItem as item
from PIL import Image
import ctypes

# Constants for default values
DEFAULT_INTERVAL = 0.01
DEFAULT_HOTKEY = "alt+c"
DEFAULT_RANDOM_MEAN = 1.0
DEFAULT_RANDOM_STDEV = 0.5
DEFAULT_CLICK_TYPE = "left"
DEFAULT_MAX_CLICKS = 0  # 0 means unlimited
DEFAULT_START_DELAY = 0
DEFAULT_POSITION = (None, None)

# Load the user32.dll
user32 = ctypes.windll.user32

# Mouse event flags
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010

class AutoClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Clicker")
        self.root.geometry("400x830")
        self.root.resizable(False, False)

        # Style
        self.style = ttkb.Style()
        self.style.theme_use("flatly")

        # Variables
        self.clicking = False
        self.hotkey = DEFAULT_HOTKEY
        self.click_count = 0
        self.pulse_animation_id = None
        self.min_font_size = 20
        self.max_font_size = 28
        self.animation_steps = 8
        self.animation_speed = 50  # milliseconds
        self.growing = True

        # Setup
        self.setup_defaults()
        self.setup_gui()
        self.bind_hotkey()

    def setup_defaults(self):
        self.interval = DEFAULT_INTERVAL
        self.use_random = False
        self.random_mean = DEFAULT_RANDOM_MEAN
        self.random_stdev = DEFAULT_RANDOM_STDEV
        self.click_type = DEFAULT_CLICK_TYPE
        self.max_clicks = DEFAULT_MAX_CLICKS
        self.click_position = DEFAULT_POSITION

    def setup_gui(self):
        main_frame = ttk.Frame(self.root, padding="20 20 20 0")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create sections
        self.create_click_settings(main_frame)
        self.create_position_settings(main_frame)
        self.create_advanced_settings(main_frame)
        self.create_control_buttons(main_frame)
        self.create_status_label(main_frame)

    def create_click_settings(self, parent):
        frame = ttk.LabelFrame(parent, text="Click Settings", padding="10")
        frame.pack(fill=tk.X, pady=10)
        
        self.entry_interval = self.create_entry(frame, "Interval (s):", str(DEFAULT_INTERVAL), 0)
        self.click_type_var = self.create_combobox(frame, "Click Type:", ["left", "right", "double"], DEFAULT_CLICK_TYPE, 1)
        self.entry_max_clicks = self.create_entry(frame, "Max Clicks:", str(DEFAULT_MAX_CLICKS), 2)

    def create_entry(self, frame, label_text, default_value, row):
        ttk.Label(frame, text=label_text).grid(row=row, column=0, sticky="w", pady=5)
        entry = ttk.Entry(frame, width=10)
        entry.grid(row=row, column=1, sticky="w", pady=5)
        entry.insert(0, default_value)
        return entry

    def create_combobox(self, frame, label_text, values, default_value, row):
        ttk.Label(frame, text=label_text).grid(row=row, column=0, sticky="w", pady=5)
        var = tk.StringVar(value=default_value)
        combobox = ttk.Combobox(frame, textvariable=var, values=values, width=8)
        combobox.grid(row=row, column=1, sticky="w", pady=5)
        return var

    def create_position_settings(self, parent):
        frame = ttk.LabelFrame(parent, text="Position Settings", padding="10")
        frame.pack(fill=tk.X, pady=10)
        self.entry_x = self.create_entry(frame, "X:", "", 0)
        self.entry_y = self.create_entry(frame, "Y:", "", 1)
        ttk.Button(frame, text="Capture Position", command=self.capture_mouse_position, style="Accent.TButton").grid(row=2, column=0, columnspan=2, pady=10)

    def create_advanced_settings(self, parent):
        frame = ttk.LabelFrame(parent, text="Advanced Settings", padding="10")
        frame.pack(fill=tk.X, pady=10)

        self.entry_hotkey = self.create_entry(frame, "Hotkey:", self.hotkey, 0)
        self.var_random = tk.IntVar()
        self.check_random = ttk.Checkbutton(frame, text="Use Random Interval", variable=self.var_random, command=self.update_random_fields_state)
        self.check_random.grid(row=1, column=0, columnspan=2, sticky="w", pady=5)
        self.entry_random_mean = self.create_entry(frame, "Random Mean:", str(DEFAULT_RANDOM_MEAN), 2)
        self.entry_random_stdev = self.create_entry(frame, "Random Std Dev:", str(DEFAULT_RANDOM_STDEV), 3)
        self.update_random_fields_state()

    def create_control_buttons(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=20)

        ttk.Button(frame, text="Start", command=self.start_clicking, style="Accent.TButton").pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(frame, text="Stop", command=self.stop_clicking, style="Accent.TButton").pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(frame, text="Apply Settings", command=self.apply_settings).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

    def create_status_label(self, parent):
        self.status_frame = ttk.Frame(parent, style="TFrame", padding=10)
        self.status_frame.pack(fill=tk.X, pady=10)
        
        indicator_frame = ttk.Frame(self.status_frame, width=40, height=40)
        indicator_frame.pack_propagate(False)
        indicator_frame.pack(side=tk.LEFT)
        self.indicator_font = font.Font(family="Helvetica", size=self.min_font_size)
        self.status_indicator = ttk.Label(indicator_frame, text="⬤", font=self.indicator_font)
        self.status_indicator.place(relx=0.5, rely=0.5, anchor="center")
        
        status_text_frame = ttk.Frame(self.status_frame)
        status_text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        self.status_label = ttk.Label(status_text_frame, text="Stopped", font=("Helvetica", 14, "bold"))
        self.status_label.pack(anchor="w")
        self.click_count_label = ttk.Label(status_text_frame, text="Clicks: 0", font=("Helvetica", 12))
        self.click_count_label.pack(anchor="w")

    def capture_mouse_position(self):
        x, y = pyautogui.position()
        self.entry_x.delete(0, tk.END)
        self.entry_x.insert(0, str(x))
        self.entry_y.delete(0, tk.END)
        self.entry_y.insert(0, str(y))

    def update_random_fields_state(self):
        state = tk.NORMAL if self.var_random.get() else tk.DISABLED
        self.entry_random_mean.config(state=state)
        self.entry_random_stdev.config(state=state)

    def apply_settings(self):
        try:
            self.interval = float(self.entry_interval.get())
            new_hotkey = self.entry_hotkey.get().strip()
            if new_hotkey != self.hotkey:
                keyboard.remove_hotkey(self.hotkey)
                self.hotkey = new_hotkey
                self.bind_hotkey()

            self.use_random = self.var_random.get() == 1
            if self.use_random:
                self.random_mean = float(self.entry_random_mean.get())
                self.random_stdev = float(self.entry_random_stdev.get())

            self.max_clicks = int(self.entry_max_clicks.get())
            self.click_type = self.click_type_var.get()

            x = self.entry_x.get()
            y = self.entry_y.get()
            self.click_position = (int(x), int(y)) if x and y else (None, None)

            messagebox.showinfo("Auto Clicker", "Settings applied successfully.")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numbers.")

    def bind_hotkey(self):
        keyboard.add_hotkey(self.hotkey, self.toggle_clicking)

    def toggle_clicking(self):
        if self.clicking:
            self.stop_clicking()
        else:
            self.start_clicking()

    def start_clicking(self):
        self.clicking = True
        self.click_count = 0
        self.update_status("Running")
        self.update_click_count()
        threading.Thread(target=self.perform_clicking, daemon=True).start()

    def perform_clicking(self):
        click_funcs = {
            "left": self.left_click,
            "right": self.right_click,
            "double": self.double_click
        }
        click_func = click_funcs[self.click_type]
        
        start_time = time.perf_counter()
        click_counter = 0
        
        while self.clicking and (self.max_clicks == 0 or self.click_count < self.max_clicks):
            current_time = time.perf_counter()
            elapsed = current_time - start_time
            
            if elapsed >= self.interval * click_counter:
                x, y = self.click_position if self.click_position != (None, None) else pyautogui.position()
                click_func(x, y)
                click_counter += 1
                self.click_count += 1
                
                if self.interval < 0.1:
                    if click_counter % 10 == 0:
                        self.root.after(0, self.update_click_count)
                else:
                    self.root.after(0, self.update_click_count)
            
            # Yield to other threads briefly
            time.sleep(0)
        
        self.stop_clicking()

    def left_click(self, x, y):
        user32.SetCursorPos(x, y)
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def right_click(self, x, y):
        user32.SetCursorPos(x, y)
        user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

    def double_click(self, x, y):
        self.left_click(x, y)
        self.left_click(x, y)

    def stop_clicking(self):
        self.clicking = False
        self.update_status("Stopped")

    def update_status(self, status):
        color = self.style.colors.success if status == "Running" else self.style.colors.danger
        self.status_indicator.configure(foreground=color)
        self.status_label.configure(text=status)
        if status == "Running":
            self.start_pulse_animation()
        else:
            self.stop_pulse_animation()

    def start_pulse_animation(self):
        def pulse():
            current_size = self.indicator_font.cget("size")
            if self.growing:
                new_size = min(self.max_font_size, current_size + 1)
                if new_size == self.max_font_size:
                    self.growing = False
            else:
                new_size = max(self.min_font_size, current_size - 1)
                if new_size == self.min_font_size:
                    self.growing = True
            self.indicator_font.configure(size=new_size)
            if self.clicking:
                self.pulse_animation_id = self.root.after(self.animation_speed, pulse)
        self.stop_pulse_animation()
        self.growing = True
        pulse()

    def stop_pulse_animation(self):
        if self.pulse_animation_id:
            self.root.after_cancel(self.pulse_animation_id)
            self.pulse_animation_id = None
        self.indicator_font.configure(size=self.min_font_size)

    def update_click_count(self):
        self.click_count_label.configure(text=f"Clicks: {self.click_count}")

    def minimize_to_tray(self):
        icon_image = Image.new("RGB", (64, 64), (255, 0, 0))
        menu = (item('Show', self.show_window), item('Quit', self.quit_window))
        icon = Icon("Auto Clicker", icon_image, "Auto Clicker", menu)
        self.root.withdraw()
        icon.run()

    def show_window(self, icon, item):
        icon.stop()
        self.root.after(0, self.root.deiconify)

    def quit_window(self, icon, item):
        icon.stop()
        self.root.destroy()

# Run the application
if __name__ == "__main__":
    root = ttkb.Window(themename="flatly")
    app = AutoClicker(root)
    root.mainloop()
