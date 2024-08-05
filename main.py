import threading
import tkinter as tk
from touch_sdk import Watch
import math
import time
import subprocess
import re
import ttkbootstrap as ttk
import win32api
from queue import Queue
from queue import Empty 

def get_monitor_info():
    monitors = win32api.EnumDisplayMonitors()
    print(f"Number of monitors detected: {len(monitors)}")
    for i, monitor in enumerate(monitors):
        monitor_info = win32api.GetMonitorInfo(monitor[0])
        print(f"Monitor {i}: {monitor_info['Device']}, Work area: {monitor_info['Work']}")
    return monitors

class FullscreenWindow(tk.Toplevel):
    def __init__(self, master, screen_number):
        super().__init__(master)
        self.screen_number = screen_number
        self.title(f"Screen {screen_number}")
        
        monitors = get_monitor_info()
        
        if screen_number < len(monitors):
            monitor = monitors[screen_number]
            monitor_info = win32api.GetMonitorInfo(monitor[0])
            work_area = monitor_info["Work"]
            
            # Set the geometry
            self.geometry(f"{work_area[2]-work_area[0]}x{work_area[3]-work_area[1]}+{work_area[0]}+{work_area[1]}")
            self.attributes('-fullscreen', True)
        else:
            print(f"Warning: Screen {screen_number} not available. Placing window on primary monitor.")
            self.geometry("800x600+100+100")  # Default size on primary monitor
        
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.indicator = self.canvas.create_oval(20, 20, 50, 50, fill='green', state='hidden')

    def set_color(self, color):
        self.canvas.configure(bg=color)

    def show_indicator(self, show=True):
        state = 'normal' if show else 'hidden'
        self.canvas.itemconfigure(self.indicator, state=state)

class JoystickGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Head Tracking and Watch Demo")

        self.geometry("+100+100")  # Adjust as needed
        self.latest_x_tilt = 0
        self.latest_y_tilt = 0



        self.current_colors = [[128, 128, 128], [128, 128, 128]]
        self.target_colors = [[128, 128, 128], [128, 128, 128]]
        self.last_color_update = time.time()
        self.head_position = "Forward"


        self.windows = [
            FullscreenWindow(self, 1),
            FullscreenWindow(self, 2),
        ]

        self.style = ttk.Style()
        self.style.theme_use('cosmo')

        self.canvas = tk.Canvas(self, width=400, height=400, bg='white')
        self.canvas.pack()

        self.deadzone_radius = 10
        self.joystick = self.canvas.create_oval(190, 190, 210, 210, fill='blue')
        self.deadzone = self.canvas.create_oval(
            200 - self.deadzone_radius,
            200 - self.deadzone_radius,
            200 + self.deadzone_radius,
            200 + self.deadzone_radius,
            outline='red'
        )

        self.fwd_back_bar = self.canvas.create_rectangle(170, 100, 230, 100, fill='green')
        self.left_right_bar = self.canvas.create_rectangle(100, 170, 100, 230, fill='yellow')

        self.xy_text = self.canvas.create_text(200, 20, text="X: 0, Y: 0", font=("Helvetica", 16))

        # New progress bars for quaternion values
        self.quaternion_frame = ttk.Frame(self)
        self.quaternion_frame.pack(pady=10)
        self.quaternion_label = ttk.Label(self.quaternion_frame, text="Quaternion Values")
        self.quaternion_label.grid(row=0, column=0, columnspan=4)
        self.quaternion_bars = {
            'X': self.create_progress_bar(self.quaternion_frame, "X", 1),
            'Y': self.create_progress_bar(self.quaternion_frame, "Y", 2),
            'Z': self.create_progress_bar(self.quaternion_frame, "Z", 3),
            'W': self.create_progress_bar(self.quaternion_frame, "W", 4),
        }

        # New progress bars for RPY values
        self.rpy_frame = ttk.Frame(self)
        self.rpy_frame.pack(pady=10)
        self.rpy_label = ttk.Label(self.rpy_frame, text="RPY Values")
        self.rpy_label.grid(row=0, column=0, columnspan=3)
        self.rpy_bars = {}
        self.rpy_value_labels = {}
        self.rpy_value_entries = {}
        for i, key in enumerate(['Roll', 'Pitch', 'Yaw']):
            self.rpy_bars[key] = self.create_progress_bar(self.rpy_frame, key, i+1)
            self.rpy_value_entries[key] = tk.Entry(self.rpy_frame, width=8, justify='center')
            self.rpy_value_entries[key].insert(0, "0.00")
            self.rpy_value_entries[key].config(state='readonly')
            self.rpy_value_entries[key].grid(row=i+1, column=2, padx=5)

        
        self.head_position_label = ttk.Label(self, text="Head Position: Forward")
        self.head_position_label.pack(pady=10)

    def update_head_position(self, position):
        self.head_position_label.config(text=f"Head Position: {position}")

    def create_progress_bar(self, frame, text, row):
        label = ttk.Label(frame, text=text)
        label.grid(row=row, column=0, padx=5)
        progress = ttk.Progressbar(frame, orient="horizontal", length=200, mode="determinate")
        progress.grid(row=row, column=1, padx=5)
        return progress
    
    def update_quaternion_and_rpy(self, data):
        quaternion_keys = ['X', 'Y', 'Z', 'W']
        rpy_keys = ['Roll', 'Pitch', 'Yaw']

        for key in quaternion_keys:
            value = data.get(key)
            if value is not None:
                try:
                    value = float(value)
                    normalized_value = (value + 1) * 50  # normalize to 0-100
                    self.quaternion_bars[key].config(value=normalized_value)
                except ValueError:
                    print(f"Warning: Unable to convert value for {key} to float: {value}")
            """ else:
                print(f"Warning: Value for {key} is None") """

        for key in rpy_keys:
            value = data.get(key)
            if value is not None:
                try:
                    value = float(value)
                    normalized_value = (value + 3) * 16.67  # normalize -3 to 3 range
                    self.rpy_bars[key].config(value=normalized_value)
                except ValueError:
                    print(f"Warning: Unable to convert value for {key} to float: {value}")
            """ else:
                print(f"Warning: Value for {key} is None") """
        
        for key in ['Roll', 'Pitch', 'Yaw']:
            value = data.get(key)
            if value is not None:
                try:
                    value = float(value)
                    normalized_value = (value + 3) * 16.67  # normalize -3 to 3 range
                    self.rpy_bars[key]['value'] = normalized_value
                    self.rpy_value_entries[key].config(state='normal')
                    self.rpy_value_entries[key].delete(0, tk.END)
                    self.rpy_value_entries[key].insert(0, f"{value:.2f}")
                    self.rpy_value_entries[key].config(state='readonly')
                except ValueError:
                    print(f"Warning: Unable to convert value for {key} to float: {value}")
            """ else:
                print(f"Warning: Value for {key} is None") """
        
        if self.head_position == "Forward":
            self.update_color()

    def update_joystick_position(self, x_tilt, y_tilt):
        x_tilt, y_tilt = y_tilt, x_tilt
        x_tilt *= 5
        y_tilt *= 5

        self.canvas.itemconfig(self.xy_text, text=f"X: {x_tilt:.2f}, Y: {y_tilt:.2f}")

        x_center = 200 + (x_tilt * 10)
        y_center = 200 + (y_tilt * 10)

        self.canvas.coords(self.joystick, x_center - 10, y_center - 10, x_center + 10, y_center + 10)

        if abs(x_tilt * 10) < self.deadzone_radius and abs(y_tilt * 10) < self.deadzone_radius:
            x_tilt, y_tilt = 0, 0

        self.canvas.coords(self.fwd_back_bar, 170, 100 - (y_tilt * 10), 230, 100 + (y_tilt * 10))
        self.canvas.coords(self.left_right_bar, 100 - (x_tilt * 10), 170, 100 + (x_tilt * 10), 230)

        # Store the latest tilt values
        self.latest_x_tilt = x_tilt
        self.latest_y_tilt = y_tilt

    def update_head_position(self, head_position):
        self.head_position = head_position
        self.head_position_label.config(text=f"Head Position: {head_position}")

        if head_position == "Forward":
            self.change_background_color(0, self.latest_x_tilt, self.latest_y_tilt)
            self.windows[0].show_indicator(True)
            self.windows[1].show_indicator(False)
            self.target_colors[1] = [128, 128, 128]
        elif head_position == "Up":
            self.change_background_color(1, self.latest_x_tilt, self.latest_y_tilt)
            self.windows[0].show_indicator(False)
            self.windows[1].show_indicator(True)
            self.target_colors[0] = [128, 128, 128]
        elif head_position == "Down":
            self.force_background_color([64, 64, 64])
            self.windows[0].show_indicator(False)
            self.windows[1].show_indicator(False)

        self.update_color()

    def change_background_color(self, window_index, x_tilt, y_tilt):
        x_tilt = max(-1, min(1, x_tilt))
        y_tilt = max(-1, min(1, y_tilt))

        r = int((x_tilt + 1) * 127.5)
        g = int((y_tilt + 1) * 127.5)
        b = 128

        self.target_colors[window_index] = [r, g, b]


    def force_background_color(self, color):
        for i in range(2):
            self.current_colors[i] = color
            self.target_colors[i] = color
        self.apply_colors()

    def update_color(self):
        current_time = time.time()
        dt = current_time - self.last_color_update
        self.last_color_update = current_time

        easing_speed = 5.0

        for i in range(2):
            if self.head_position == "Forward" and i == 0:
                for j in range(3):
                    diff = self.target_colors[i][j] - self.current_colors[i][j]
                    self.current_colors[i][j] += diff * easing_speed * dt
            elif self.head_position == "Up" and i == 1:
                for j in range(3):
                    diff = self.target_colors[i][j] - self.current_colors[i][j]
                    self.current_colors[i][j] += diff * easing_speed * dt
            else:
                # Reset to default color if not the active window
                self.current_colors[i] = [128, 128, 128]

        self.apply_colors()

    def apply_colors(self):
        for i in range(2):
            r, g, b = [int(max(0, min(255, c))) for c in self.current_colors[i]]
            color = f'#{r:02x}{g:02x}{b:02x}'
            self.windows[i].set_color(color)


class MyWatch(Watch):
    def __init__(self, gui, data_queue):
        super().__init__()
        self.gui = gui
        self.data_queue = data_queue
        self.head_position = "Forward"
        self.last_position_change_time = 0
        self.position_change_threshold = 0.5  # seconds
        self.last_x_tilt = 0
        self.last_y_tilt = 0

    def set_head_position(self, position):
        current_time = time.time()
        if position != self.head_position and current_time - self.last_position_change_time > self.position_change_threshold:
            self.head_position = position
            self.last_position_change_time = current_time
            self.data_queue.put(('head_position', (self.last_x_tilt, self.last_y_tilt, self.head_position)))

    def on_sensors(self, sensors):
        acceleration = sensors.acceleration
        self.last_x_tilt = acceleration[0] * 0.1
        self.last_y_tilt = acceleration[1] * 0.09
        self.data_queue.put(('joystick', (self.last_x_tilt, self.last_y_tilt, self.head_position)))

    

def start_watch(watch):
    watch.start()

parsed_values = {
    'X': None,
    'Y': None,
    'Z': None,
    'W': None,
    'Roll': None,
    'Pitch': None,
    'Yaw': None
}


def read_stdout_in_real_time(executable_path, data_queue):
    process = subprocess.Popen([executable_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    # Regular expressions to match the values
    quaternion_pattern = re.compile(r'X=(-?\d+,\d+)\nY=(-?\d+,\d+)\nZ=(-?\d+,\d+)\nW=(-?\d+,\d+)')
    rpy_pattern = re.compile(r'Roll=(-?\d+,\d+)\nPitch=(-?\d+,\d+)\nYaw=(-?\d+,\d+)')

    try:
        while True:
            output = process.stdout.readline()
            if output == b'' and process.poll() is not None:
                break
            if output:
                output = output.decode('utf-8')
                """ print(output) """

                # Check for Raw quaternion vector and parse values
                if "Raw quaternion vector:" in output:
                    next_lines = ''.join([process.stdout.readline().decode('utf-8') for _ in range(4)])
                    quaternion_match = quaternion_pattern.search(next_lines)
                    if quaternion_match:
                        parsed_values = {
                            'X': float(quaternion_match.group(1).replace(',', '.')),
                            'Y': float(quaternion_match.group(2).replace(',', '.')),
                            'Z': float(quaternion_match.group(3).replace(',', '.')),
                            'W': float(quaternion_match.group(4).replace(',', '.'))
                        }
                        data_queue.put(('quaternion', parsed_values))

                elif "RPY values:" in output:
                    next_lines = ''.join([process.stdout.readline().decode('utf-8') for _ in range(3)])
                    rpy_match = rpy_pattern.search(next_lines)
                    if rpy_match:
                        parsed_values = {
                            'Roll': float(rpy_match.group(1).replace(',', '.')),
                            'Pitch': float(rpy_match.group(2).replace(',', '.')),
                            'Yaw': float(rpy_match.group(3).replace(',', '.'))
                        }
                        data_queue.put(('rpy', parsed_values))

                        pitch = parsed_values['Pitch']
                        if pitch < 0.8:
                            head_position = "Up"
                        elif 0.8 <= pitch <= 1.1:
                            head_position = "Forward"

                        else:
                            head_position = "Down"
                        data_queue.put(('head_position', head_position))

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        rc = process.poll()
        print(f'The process exited with return code {rc}')

def update_gui(gui, data_queue):
    latest_head_position = None
    latest_joystick_data = None

    try:
        while True:
            try:
                data_type, data = data_queue.get_nowait()
                if data_type == 'joystick':
                    latest_joystick_data = data
                elif data_type == 'quaternion':
                    gui.update_quaternion_and_rpy(data)
                elif data_type == 'rpy':
                    gui.update_quaternion_and_rpy(data)
                elif data_type == 'head_position':
                    if isinstance(data, str):
                        latest_head_position = data
                    else:
                        latest_joystick_data = data
            except Empty:
                break  # Break the loop if the queue is empty

        # Update joystick and head position after processing all queue items
        if latest_joystick_data:
            gui.update_joystick_position(*latest_joystick_data[:2])  # Only pass x_tilt and y_tilt
        if latest_head_position:
            gui.update_head_position(latest_head_position)

    finally:
        # Schedule the next update
        gui.after(10, update_gui, gui, data_queue)


# Main execution
if __name__ == "__main__":
    executable_path = r'C:\GIT\GalaxyBudsClient\GalaxyBudsClient\bin\Debug\net8.0-windows10.0.19041\GalaxyBudsClient.exe'
    data_queue = Queue()
    joystick_gui = JoystickGUI()
    watch = MyWatch(joystick_gui, data_queue)

    watch_thread = threading.Thread(target=start_watch, args=(watch,))
    watch_thread.start()

    buds_thread = threading.Thread(target=read_stdout_in_real_time, args=(executable_path, data_queue))
    buds_thread.start()

    joystick_gui.after(10, update_gui, joystick_gui, data_queue)
    joystick_gui.mainloop()