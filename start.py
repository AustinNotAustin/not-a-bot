import ui_design_variables as ui
import matplotlib.pyplot as plt
import tkinter.font as tkFont
import tkinter as tk

import matplotlib
import threading
import pyautogui
import keyboard
import datetime
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
    current_bpm = 0

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
        self.root.geometry("340x590")
        self.root.config(bg=ui.background_color)
        self.root.protocol("WM_DELETE_WINDOW", self.close_application)

        # Create a frame to center the elements
        self.frame = tk.Frame(root)
        self.frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.frame.config(bg=ui.foreground_color)

        # Heart and EKG content
        original_heart_image = Image.open("./img/heart.png")
        self.small_heart_image = original_heart_image.resize((150, 150), Image.NEAREST)
        self.big_heart_image = original_heart_image.resize((160, 160), Image.NEAREST)
        self.is_big_heart = True

        # Fixed frame for the heart to prevent window re-sizing
        self.heart_frame = tk.Frame(self.frame, width=160, height=160, bg=ui.foreground_color)
        self.heart_frame.grid(row=0, columnspan=3, padx=10, pady=0)
        self.heart_frame.grid_propagate(False)

        self.heart_image = ImageTk.PhotoImage(self.big_heart_image)
        self.heart_label = tk.Label(self.heart_frame, image=self.heart_image, bg=ui.foreground_color)
        self.heart_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)  # Center in the frame

        # BPM Display Label
        self.bpm_label = tk.Label(
            self.frame,
            text=f"BPM: {self.current_bpm}",
            bg=ui.foreground_color,
            font=(ui.font, ui.lg_font)
        )
        self.bpm_label.grid(row=1, column=0, padx=10, pady=0)

        # EKG Canvas
        self.ekg_canvas = tk.Canvas(
            self.frame, 
            width=240, 
            height=160, 
            bg=ui.graph_background_color
        )
        self.ekg_canvas.grid(row=2, columnspan=3, padx=10, pady=0)
        self.ekg_data = []

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


        # Buttons & Buttons Logic
        #   Start/Stop Button
        self.start_stop_button = tk.Button(self.frame, text=self.START_TEXT, command=self.toggle_start_stop)
        self.start_stop_button.grid(row=3, column=0, padx=10, pady=10)
        self.start_stop_button.config(height=2, bg=ui.start_button_color, font=(ui.font, ui.xl_font))

        #   Connect Button
        self.bluetooth_devices_button = tk.Button(self.frame, text="Connect Device", command=lambda: asyncio.run_coroutine_threadsafe(self.toggle_bluetooth_devices(), self.bluetooth_loop))
        self.bluetooth_devices_button.grid(row=3, column=1, padx=10, pady=10)
        self.bluetooth_devices_button.config(height=2, bg=ui.bluetooth_button_color, font=(ui.font, ui.xl_font))

        #  Bluetooth Device Texts
        self.bluetooth_text = tk.Message(self.frame, text=f"{self.bluetooth_device_verbiage}{self.bluetooth_controller.selected_device_name}", width=200)
        self.bluetooth_text.grid(row=4, columnspan=2, padx=10, pady=10)
        self.bluetooth_text.config(bg=ui.foreground_color, font=(ui.font, ui.lg_font))


    def flatline_ekg(self):
        print("Cleaning up EKG visualization...")
        # Clear the canvas
        self.ekg_canvas.delete("ekg")

        # Reset the baseline
        canvas_width = self.ekg_canvas.winfo_width() or 300
        canvas_height = self.ekg_canvas.winfo_height() or 200

        self.ekg_canvas.create_line(
            0, canvas_height / 1.5, 
            canvas_width, canvas_height / 1.5, 
            fill=ui.heart_rate_line_color, 
            width=3, 
            tags="ekg"
        )
        
        # Make sure the heart is in its default state
        if not self.is_big_heart:
            self.toggle_heart_image()  # Return to big heart state
        
        print("EKG visualization cleanup complete")


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
    

    # Simulate a screen click
    async def click_screen(self, action_delay):
        await asyncio.sleep(action_delay)
        pyautogui.click()
    

    # Beats the heart back and forth
    def toggle_heart_image(self):
        # Save the previous image to prevent garbage collection
        self.previous_heart_image = self.heart_image
        
        if self.is_big_heart:
            self.heart_image = ImageTk.PhotoImage(self.small_heart_image)
            self.is_big_heart = False
        else:
            self.heart_image = ImageTk.PhotoImage(self.big_heart_image)
            self.is_big_heart = True
        
        # Update the label with the new image
        self.heart_label.config(image=self.heart_image)
        self.root.update()  # Force a UI update


    # Performs the actual actions of the application based on BPM
    # DEPRECATED: This was used before the EKG was added when only the BPM chart was there
    def perform_action_per_bpm(self, heart_rate):
        action_delay = 60 / heart_rate

        asyncio.run_coroutine_threadsafe(self.click_screen(action_delay), self.bluetooth_loop)


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
            
            self.simulate_ekg()


    def simulate_ekg(self):
        self.current_bpm = 100
        asyncio.run_coroutine_threadsafe(self.start_ekg(), self.bluetooth_loop)


    async def start_ekg(self):
        # Define the EKG waveform pattern
        ekg_points = [
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,       # Delays and pre-wave 
            0.04,                               # Peak P Wave
            0.0, 0.0,                           # Post P/Pre Q
            -0.05,                              # Peak Q Dip
            0.35,                               # Peak R Wave
            -0.095,                             # Peak S Dip
            0.0, 0.0,                           # Post S/Pre T
            0.06,                               # Peak T Wave
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0        # Post wave delays
        ]


        # Calculate settings once
        points_per_beat = len(ekg_points)

        # Pre-calculate all point coordinates - do this only once!
        canvas_width = self.ekg_canvas.winfo_width() or 300
        canvas_height = self.ekg_canvas.winfo_height() or 200
        
        x_scale = canvas_width / points_per_beat
        y_scale = 300
        y_offset = canvas_height / 1.5

        precomputed_coords = []
        for i, amp in enumerate(ekg_points):
            x = int(i * x_scale)
            y = y_offset - (amp * y_scale)
            precomputed_coords.append((x, y))

        print("Preparing EKG simulation...")
        self.flatline_ekg()
        await asyncio.sleep(2)  
        print("Starting EKG visualization")

        beat_counter = 0
        start_time = time.time()
        
        # Hold the line object reference to update it
        line_id = None
        
        try:

            while self.is_running and not self.is_closing_application:

                # Calculate settings once
                seconds_per_beat = 60 / self.current_bpm  # 0.6 seconds per beat at 100 BPM
                points_per_beat = len(ekg_points)
                seconds_per_point = seconds_per_beat / points_per_beat  # Time to show each point

                # Start with clean canvas for each beat
                self.ekg_canvas.delete("ekg")
                
                # Calculate the beat start time
                beat_start_time = start_time + (beat_counter * seconds_per_beat)
                
                # Draw the EKG line point by point within a single beat
                await self.draw_ekg_line(
                    points_per_beat,
                    precomputed_coords,
                    beat_start_time,
                    seconds_per_point,
                    line_id,
                )
                
                # Update counter for performance tracking
                beat_counter += 1
                
                # Log performance stats every 10 beats
                if beat_counter % 10 == 0:
                    elapsed = time.time() - start_time
                    expected = beat_counter * seconds_per_beat
                    print(f"EKG Counter: {beat_counter}, Elapsed: {elapsed:.2f}s, Expected: {expected:.2f}s, Drift: {elapsed-expected:.2f}s")
            
        finally:
            # This block will execute when the loop ends for any reason
            self.flatline_ekg()


    # Draws the EKG line on the canvas
    async def draw_ekg_line(self, points_per_beat, precomputed_coords, beat_start_time, seconds_per_point, line_id=None):
        for point_idx in range(1, points_per_beat + 1):
            # Clear previous line
            if line_id:
                self.ekg_canvas.delete(line_id)
            
            # Create points up to current index
            points_to_draw = []
            for i in range(min(point_idx, len(precomputed_coords))):
                points_to_draw.append(precomputed_coords[i][0])  # x coord
                points_to_draw.append(precomputed_coords[i][1])  # y coord
            
            # Draw the line
            if len(points_to_draw) >= 4:  # Need at least 2 points for a line
                line_id = self.ekg_canvas.create_line(
                    points_to_draw,
                    fill=ui.heart_rate_line_color,
                    width=3,
                    tags="ekg",
                )
            
            # Beat the heart at the QRS Complex
            if point_idx == 9:
                print("Heart beat 1 - toggling heart image")
                self.toggle_heart_image()
            # Perform a click at the peak R wave
            elif point_idx == 10:
                print("Heart beat 2 - toggling heart image and clicking")
                asyncio.run_coroutine_threadsafe(self.click_screen(0), self.bluetooth_loop)
                self.toggle_heart_image()
            elif point_idx == 11:
                print("Heart beat 3 - toggling heart image")
                self.toggle_heart_image()
            elif point_idx == 12:
                print("Heart beat 4 - toggling heart image")
                self.toggle_heart_image()
            
            # Calculate exact time for this point
            point_time = beat_start_time + (point_idx * seconds_per_point)
            current_time = time.time()
            
            # Sleep precisely until next point time
            sleep_time = max(0.001, point_time - current_time)
            await asyncio.sleep(sleep_time)
                    



if __name__ == "__main__":
    bluetooth_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(bluetooth_loop)

    bluetooth_loop_thread = threading.Thread(target=bluetooth_loop.run_forever, daemon=True)
    bluetooth_loop_thread.start()

    root = tk.Tk()
    app = NotABotUI(root, asyncio.get_event_loop())
    root.mainloop()
