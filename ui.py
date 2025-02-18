import ui_design_variables as ui
import matplotlib.pyplot as plt
import tkinter.font as tkFont
import tkinter as tk

import matplotlib
import threading
import pyautogui
import keyboard
import asyncio
import random
import time
import os

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from global_vars import CANCEL_BUTTON
from matplotlib import font_manager
from tkinter import TclError
from bluetooth_device_list import BluetoothDeviceList
from bluetooth_controller import BluetoothController


# The minus symbol is missing from my font pack
matplotlib.rcParams['axes.unicode_minus'] = False


class NotABotUI:

    # Controls
    start_button_keybind = "escape"
    stop_button_keybind = "escape"

    # Application Logic
    bluetooth_device_list = None
    bluetooth_controller = None
    bluetooth_loop = None

    is_closing_application = False
    bpm_data = []
    threads = []  # List to keep track of threads
    tasks = []  # List to keep track of asyncio tasks

    # Application Variables
    START_TEXT = f"Start ({CANCEL_BUTTON})"
    STOP_TEXT = f"Stop ({CANCEL_BUTTON})"
    bluetooth_device_verbiage = "Bluetooth Device:\n"


    def __init__(self, root, bluetooth_loop):
        self.root = root
        self.bluetooth_loop = bluetooth_loop

        self.bluetooth_controller = BluetoothController(self, self.bluetooth_loop)
        self.bluetooth_device_list = BluetoothDeviceList(self, self.bluetooth_loop, self.bluetooth_controller)
        
        # Make a custom font
        self.custom_font = tkFont.Font(family=ui.font, size=ui.lg_font)
        font_path = "path/to/your/font.ttf"  # Update with your actual path

        # Register the font in Tkinter
        if os.path.exists(font_path):
            self.custom_font.actual()
            root.tk.call("font", "create", ui.font, "-family", ui.font, "-size", ui.lg_font)
            root.tk.call("font", "configure", ui.font, "-family", ui.font)

        # Call async functions using the bluetooth_loop like so:
        #  asyncio.run_coroutine_threadsafe(async_function(), self.bluetooth_loop)
        self.create_ui(root)

        # Listeners
        self.listen_for_toggle()


    def create_ui(self, root):
        self.root.title("Bluetooth Controller")
        self.root.geometry("1000x700")
        self.root.config(bg=ui.background_color)
        self.root.protocol("WM_DELETE_WINDOW", self.close_application)

        # Create a frame to center the elements
        self.frame = tk.Frame(root)
        self.frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.frame.config(bg=ui.foreground_color)

        # Buttons & Buttons Logic
        #   Start/Stop Button
        self.start_stop_button = tk.Button(self.frame, text=self.START_TEXT, command=self.toggle_start_stop)
        self.start_stop_button.grid(row=0, column=0, padx=10, pady=10)
        self.start_stop_button.config(height=2, bg=ui.start_button_color, font=(ui.font, ui.xl_font))

        #   Connect Button
        self.bluetooth_devices_button = tk.Button(self.frame, text="Connect Device", command=self.toggle_bluetooth_devices)
        self.bluetooth_devices_button.grid(row=0, column=1, padx=10, pady=10)
        self.bluetooth_devices_button.config(height=2, bg=ui.bluetooth_button_color, font=(ui.font, ui.xl_font))

        #  Bluetooth Device Texts
        self.bluetooth_text = tk.Message(self.frame, text=f"{self.bluetooth_device_verbiage}{self.bluetooth_controller.selected_device_name}", width=200)
        self.bluetooth_text.grid(row=0, column=2, padx=10, pady=10)
        self.bluetooth_text.config(bg=ui.foreground_color, font=(ui.font, ui.lg_font))

        # Matplotlib figure and axis
        self.fig, self.ax = plt.subplots()
        self.fig.patch.set_facecolor(ui.graph_background_color)

        # Matplotlib graph title and labels
        matplotlib_font = font_manager.FontProperties(fname="./font/Dogica.ttf")

        self.ax.title.set_fontproperties(matplotlib_font)
        self.ax.title.set_fontsize(ui.lg_font)
        
        self.ax.xaxis.label.set_fontproperties(matplotlib_font)
        self.ax.xaxis.label.set_fontsize(ui.lg_font)
        
        self.ax.yaxis.label.set_fontproperties(matplotlib_font)
        self.ax.yaxis.label.set_fontsize(ui.lg_font)
        
        self.ax.set_facecolor(ui.graph_foreground_color)
        
        self.line, = self.ax.plot([], [], color=ui.heart_rate_line_color)

        for label in self.ax.get_xticklabels():
            label.set_fontproperties(matplotlib_font)
            label.set_fontsize(ui.sm_font)
        
        for label in self.ax.get_yticklabels():
            label.set_fontproperties(matplotlib_font)
            label.set_fontsize(ui.sm_font)

        # Matplotlib graph title and labels
        self.ax.set_title('Heart Rate BPM')
        self.ax.set_xlabel('Time (Seconds)')
        self.ax.set_ylabel('BPM')

        # Canvas graph and plotted lines
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas.get_tk_widget().grid(row=1, columnspan=3, padx=10, pady=10)
        self.canvas.get_tk_widget().config(bg="#8B4513")


    # Stops and start the BPM measurement and subsequent actions
    def toggle_start_stop(self):
        # When there is no Bluetooth device connected, open the Bluetooth device list
        if not self.bluetooth_controller.is_bluetooth_device_connected:
            print("No Bluetooth device connected. Please connect a device first.")
            self.bluetooth_device_list.open_bluetooth_devices()

        elif self.bluetooth_controller.is_heart_rate_monitor_running:
            self.start_stop_button.config(text=self.START_TEXT, bg=ui.start_button_color)
            self.bluetooth_controller.stop_heart_rate_monitor()
        
        else:
            self.start_stop_button.config(text=self.STOP_TEXT, bg=ui.stop_button_color)
            self.bluetooth_controller.start_heart_rate_monitor()


    # Toggles the connect bluetooth connection / bluetooth device list
    def toggle_bluetooth_devices(self):
        if self.bluetooth_controller.is_bluetooth_device_connected:
            self.bluetooth_controller.disconnect_bluetooth_device()
        else:
            self.bluetooth_device_list.open_bluetooth_devices()

    # Performs the actual actions of the application based on BPM
    async def perform_action_per_bpm(self, heart_rate):
        action_delay = 60 / heart_rate

        # Simulate a screen click
        def click_screen():
            time.sleep(action_delay)
            pyautogui.click()

        click_screen()


    # Listens for keyboard strokes to start and stop the heart rate monitor / clicker
    def listen_for_toggle(self):
        print(f"Listening for '{self.start_button_keybind}' keybind...")
        if not self.is_closing_application:
            keyboard.add_hotkey(self.start_button_keybind, self.toggle_start_stop)


    # Used to close the application properly
    def close_application(self):
        self.is_closing_application = True
        self.root.destroy()
        self.bluetooth_loop.call_soon_threadsafe(self.bluetooth_loop.stop)
        exit(0)


    # # # # # # # # #
    # 
    #  Sub Functions
    # 
    # # # # # # # # #

    def heart_rate_handler(self, sender, data):
        heart_rate = data[1]
        print(f"Heart Rate: {heart_rate} bpm")
        self.plot_heart_rate_data(heart_rate)
        self.perform_action_per_bpm(heart_rate)

    # Plots heart rate data on the graph
    def plot_heart_rate_data(self, heart_rate):
        self.bpm_data.append(heart_rate)

        # Limit the number of data points to 100
        if len(self.bpm_data) > 60:
            self.bpm_data.pop(0)
        
        self.line.set_xdata(range(len(self.bpm_data)))
        self.line.set_ydata(self.bpm_data)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()


    # Simulate heart rate data for demonstration purposes
    def simulate_run_heart_rate_monitor(self):
        while self.is_running and not self.is_closing_application:
            heart_rate = random.randint(60, 100)
            self.plot_heart_rate_data(heart_rate)
            time.sleep(1)


if __name__ == "__main__":
    bluetooth_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(bluetooth_loop)

    bluetooth_loop_thread = threading.Thread(target=bluetooth_loop.run_forever, daemon=True)
    bluetooth_loop_thread.start()

    root = tk.Tk()
    app = NotABotUI(root, asyncio.get_event_loop())
    root.mainloop()
