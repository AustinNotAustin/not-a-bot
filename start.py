import ui_design_variables as ui
import matplotlib.pyplot as plt
import tkinter.font as tkFont
import tkinter as tk
import numpy as np

import matplotlib
import threading
import pyautogui
import keyboard
import asyncio
import random
import time
import os

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from bluetooth_device_list import BluetoothDeviceList
from bluetooth_controller import BluetoothController
from matplotlib import font_manager
from PIL import Image, ImageTk


# The minus symbol is missing from my font pack
matplotlib.rcParams['axes.unicode_minus'] = False
CANCEL_BUTTON = "esc"
DEBUG = True


class NotABotUI:

    # Controls
    start_button_keybind = "escape"
    stop_button_keybind = "escape"

    # Application Logic
    bluetooth_device_list = None
    bluetooth_controller = None
    bluetooth_loop = None

    is_closing_application = False
    is_running = False # Used for development/debug purposes
    bpm_data = []
    ekg_data = []
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
        self.root.geometry("820x990")
        self.root.config(bg=ui.background_color)
        self.root.protocol("WM_DELETE_WINDOW", self.close_application)

        # Create a frame to center the elements
        self.frame = tk.Frame(root)
        self.frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.frame.config(bg=ui.foreground_color)

        # Heart and EKG content
        original_heart_image = Image.open("./img/heart.png")
        heart_image = original_heart_image.resize((200, 200), Image.NEAREST)
        beating_heart_image = original_heart_image.resize((210, 210), Image.NEAREST)
        self.heart_image = ImageTk.PhotoImage(heart_image)
        heart_label = tk.Label(self.frame, image=self.heart_image, bg=ui.foreground_color)
        heart_label.grid(row=0, columnspan=3, padx=10, pady=10)

        # EKG plot
        self.ekg_fig, self.ekg_ax = plt.subplots()
        self.ekg_fig.patch.set_facecolor(ui.graph_background_color)
        self.ekg_ax.set_facecolor(ui.graph_foreground_color)
        self.ekg_ax.set_title('EKG')
        self.ekg_ax.set_xlabel('Time (Seconds)')
        self.ekg_ax.set_ylabel('Amplitude')
        self.ekg_ax.set_ylim(-0.15, 0.4)
        self.ekg_line, = self.ekg_ax.plot([], [], color=ui.heart_rate_line_color)

        self.ekg_canvas = FigureCanvasTkAgg(self.ekg_fig, master=self.frame)
        self.ekg_canvas.get_tk_widget().config(bg=ui.foreground_color)
        self.ekg_canvas.get_tk_widget().grid(row=1, columnspan=3, padx=10, pady=10)

        # Matplotlib figure and axis
        self.fig, self.ax = plt.subplots()
        self.fig.patch.set_facecolor(ui.graph_background_color)

        # Matplotlib graph title and labels
        matplotlib_font = font_manager.FontProperties(fname=ui.font_path)

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
        self.canvas.get_tk_widget().config(bg="#8B4513")
        # self.canvas.get_tk_widget().grid(row=1, columnspan=2, padx=10, pady=10)


        # Buttons & Buttons Logic
        #   Start/Stop Button
        self.start_stop_button = tk.Button(self.frame, text=self.START_TEXT, command=self.toggle_start_stop)
        self.start_stop_button.grid(row=2, column=0, padx=10, pady=10)
        self.start_stop_button.config(height=2, bg=ui.start_button_color, font=(ui.font, ui.xl_font))

        #   Connect Button
        self.bluetooth_devices_button = tk.Button(self.frame, text="Connect Device", command=lambda: asyncio.run_coroutine_threadsafe(self.toggle_bluetooth_devices(), self.bluetooth_loop))
        self.bluetooth_devices_button.grid(row=2, column=1, padx=10, pady=10)
        self.bluetooth_devices_button.config(height=2, bg=ui.bluetooth_button_color, font=(ui.font, ui.xl_font))

        #  Bluetooth Device Texts
        self.bluetooth_text = tk.Message(self.frame, text=f"{self.bluetooth_device_verbiage}{self.bluetooth_controller.selected_device_name}", width=200)
        self.bluetooth_text.grid(row=3, columnspan=2, padx=10, pady=10)
        self.bluetooth_text.config(bg=ui.foreground_color, font=(ui.font, ui.lg_font))


    # Stops and start the BPM measurement and subsequent actions
    def toggle_start_stop(self):
        # Development purposes
        if DEBUG:
            self.toggle_simulate_run_heart_rate_monitor()

        # When there is no Bluetooth device connected, open the Bluetooth device list
        elif not self.bluetooth_controller.is_bluetooth_device_connected:
            print("No Bluetooth device connected. Please connect a device first.")
            self.bluetooth_device_list.open_bluetooth_devices()

        elif self.bluetooth_controller.is_heart_rate_monitor_running:
            self.stop_actions()
        
        else:
            self.start_stop_button.config(text=self.STOP_TEXT, bg=ui.stop_button_color)
            asyncio.run_coroutine_threadsafe(self.bluetooth_controller.start_heart_rate_monitor(), self.bluetooth_loop)
    

    # Stops the BPM measuyrement and clicking actions of the application
    def stop_actions(self):
        self.start_stop_button.config(text=self.START_TEXT, bg=ui.start_button_color)
        self.bluetooth_controller.stop_heart_rate_monitor()


    # Toggles the connect bluetooth connection / bluetooth device list
    async def toggle_bluetooth_devices(self):
        print("Toggling Bluetooth devices...")
        if self.bluetooth_controller.is_bluetooth_device_connected:
            await self.bluetooth_controller.disconnect_bluetooth_device()
        else:
            self.bluetooth_device_list.open_bluetooth_devices()

    # Performs the actual actions of the application based on BPM
    def perform_action_per_bpm(self, heart_rate):
        action_delay = 60 / heart_rate

        # Simulate a screen click
        async def click_screen():
            await asyncio.sleep(action_delay)
            pyautogui.click()

        asyncio.run_coroutine_threadsafe(click_screen(), self.bluetooth_loop)


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
        self.ax.set_ylim(40,160)
        self.canvas.draw()


    # Simulate heart rate data for demonstration purposes
    async def simulate_heart_rate(self):
        heart_rate_change = 3
        heart_rate_change_chance = 0.4
        while self.is_running and not self.is_closing_application:
            last_heart_rate = self.bpm_data[-1] if self.bpm_data else random.randint(60, 100)
            if random.random() > heart_rate_change_chance:
                heart_rate = last_heart_rate
            else:
                heart_rate = random.randint(max(60, last_heart_rate - heart_rate_change), min(100, last_heart_rate + heart_rate_change))
            self.plot_heart_rate_data(heart_rate)
            await asyncio.sleep(.1)

    def toggle_simulate_run_heart_rate_monitor(self):
        if self.is_running:
            self.is_running = False
            self.start_stop_button.config(text=self.START_TEXT, bg=ui.start_button_color)
        else:
            self.is_running = True
            self.start_stop_button.config(text=self.STOP_TEXT, bg=ui.stop_button_color)
            asyncio.run_coroutine_threadsafe(self.simulate_heart_rate(), self.bluetooth_loop)
            
            asyncio.run_coroutine_threadsafe(self.simulate_ekg(), self.bluetooth_loop)


    async def simulate_ekg(self):
        self.current_bpm = 100
        """Generates a more realistic EKG waveform based on BPM"""
        if not hasattr(self, "time_index"):
            self.time_index = 0  # Keep track of time for continuity

        while self.is_running and not self.is_closing_application:
            bpm = max(40, min(self.current_bpm, 180))  # Clamp BPM to reasonable range
            beat_interval = 60 / bpm  # Convert BPM to seconds per beat
            sample_rate = 100  # Samples per second

            # Maintain continuous time axis
            t = np.linspace(self.time_index, self.time_index + beat_interval, int(sample_rate * beat_interval))
            self.time_index += beat_interval  # Move time forward for the next beat

            # Relative time for each wave in the cycle
            p_wave_offset = 0.2
            q_wave_offset = 0.4
            r_wave_offset = 0.405
            s_wave_offset = 0.41
            t_wave_offset = 0.62

            # New offsets based on BPM
            adjusted_p_offset = p_wave_offset * beat_interval
            adjusted_q_offset = q_wave_offset * beat_interval
            adjusted_r_offset = r_wave_offset * beat_interval
            adjusted_s_offset = s_wave_offset * beat_interval
            adjusted_t_offset = t_wave_offset * beat_interval

            # Simulated EKG signal: P-wave, QRS complex, T-wave
            ekg_wave = (
                # amplitude * exp(-sharpness * ((time % period) - offset) ** 2)
                0.03 * np.exp(-400 * ((t % beat_interval) - beat_interval * adjusted_p_offset) ** 2)          # P wave
                + -0.3 * np.exp(-1500 * ((t % beat_interval) - beat_interval * adjusted_q_offset) ** 2)       # Q dip
                + 1.15 * np.exp(-2400 * ((t % beat_interval) - beat_interval * adjusted_r_offset) ** 2)       # R peak
                + -0.55 * np.exp(-1800 * ((t % beat_interval) - beat_interval * adjusted_s_offset) ** 2)     # S dip
                + 0.04 * np.exp(-400 * ((t % beat_interval) - beat_interval * adjusted_t_offset) ** 2)       # T wave
            )
            
            sleep_interval = beat_interval / len(ekg_wave)
            print(f"beat_interval: {beat_interval}")
            print(f"len(ekg_wave): {len(ekg_wave)}")
            print(f"sleep_interval: {sleep_interval}")

            for value in ekg_wave:
                self.ekg_data.append(value)
                if len(self.ekg_data) > self.current_bpm:
                    self.ekg_data.pop(0)

                self.ekg_line.set_xdata(range(len(self.ekg_data)))
                self.ekg_line.set_ydata(self.ekg_data)
                self.ekg_ax.relim()
                self.ekg_ax.autoscale_view()
                self.ekg_canvas.draw()
                await asyncio.sleep(sleep_interval)  # Sync with BPM



if __name__ == "__main__":
    bluetooth_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(bluetooth_loop)

    bluetooth_loop_thread = threading.Thread(target=bluetooth_loop.run_forever, daemon=True)
    bluetooth_loop_thread.start()

    root = tk.Tk()
    app = NotABotUI(root, asyncio.get_event_loop())
    root.mainloop()
