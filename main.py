import threading
import tkinter as tk
from touch_sdk import Watch
from pythonosc import udp_client
import math
import time

class JoystickGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Virtual Joystick")

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

    #render joystick gui and define deadzone
    def update_joystick(self, x_tilt, y_tilt):
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

class MyWatch(Watch):
    def __init__(self, gui, osc_client):
        super().__init__()
        self.gui = gui
        self.osc_client = osc_client
        self.last_tap_time = 0
        self.tap_count = 0
        self.is_holding_forward = False
        self.last_x_tilt = 0
        self.last_y_tilt = 0

    #on tap figure direction and osc control command to vrchat
    def on_tap(self):
        print('tap')
        #double tap logic
        current_time = time.time()
        if current_time - self.last_tap_time <= 0.7:
            self.tap_count += 1
            if self.tap_count == 2 and self.is_holding_forward:
                self.tap_count = 0
                print("Double tap detected, not sending neutral")
                return
        else:
            self.tap_count = 1

        self.last_tap_time = current_time
        x_tilt, y_tilt = self.get_current_tilt()
        x_tilt = float(x_tilt)
        y_tilt = float(y_tilt)
        x_tilt2 = x_tilt * 5
        y_tilt2 = y_tilt * 5
        if abs(x_tilt2 * 10) < self.gui.deadzone_radius and abs(y_tilt2 * 10) < self.gui.deadzone_radius:
            x_tilt, y_tilt = 0.0001, 0.0001
        self.send_osc_messages(x_tilt, y_tilt)

    #define and send osc message
    def send_osc_messages(self, x_tilt, y_tilt):
        x_tilt, y_tilt = y_tilt, x_tilt

        x_tilt = self.apply_scaling(x_tilt)
        x_tilt *= -1

        if abs(x_tilt) > abs(y_tilt):
            self.osc_client.send_message("/input/LookHorizontal", x_tilt)
            y_tilt = 0.0001
        else:
            self.osc_client.send_message("/input/Vertical", y_tilt)
            x_tilt = 0.0001

        #if not double tapped send neutral to stop moving
        if not self.is_holding_forward:
            threading.Timer(0.4, self.send_neutral).start()

    def get_current_tilt(self):
        return self.last_x_tilt, self.last_y_tilt

    #scaling for sensitivity
    def apply_scaling(self, value):
        steepness = 1.6
        scaled_value = (1 / (1 + math.exp(-steepness * value))) * 2 - 1
        return scaled_value

    def send_neutral(self):
        self.osc_client.send_message("/input/Vertical", 0.0001)
        self.osc_client.send_message("/input/LookHorizontal", 0.0001)

    def on_sensors(self, sensors):
        acceleration = sensors.acceleration
        x = acceleration[0]
        y = acceleration[1] 
        x *= 0.1
        y *= 0.09

        self.last_x_tilt = x
        self.last_y_tilt = y
        self.gui.update_joystick(x, y)


        if x > 0.5:
            self.is_holding_forward = True
        else:
            self.is_holding_forward = False

    def on_touch_down(self, x, y):
        print('touch down', x, y)

    def on_touch_up(self, x, y):
        print('touch up', x, y)

    def on_touch_move(self, x, y):
        print('touch move', x, y)

    def on_touch_cancel(self, x, y):
        print('touch cancel', x, y)

def start_watch(watch):
    watch.start()

joystick_gui = JoystickGUI()

osc_client = udp_client.SimpleUDPClient("127.0.0.1", 9000)

watch = MyWatch(joystick_gui, osc_client)

watch_thread = threading.Thread(target=start_watch, args=(watch,))
watch_thread.start()

joystick_gui.mainloop()