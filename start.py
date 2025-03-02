import ui_design_variables as ui
import tkinter as tk
import sys

import asyncio

from bluetooth_device_list import BluetoothDeviceList
from bluetooth_controller import BluetoothController
from random import randint, random
from keyboard import add_hotkey
from PIL import Image, ImageTk
from os import path as os_path
from tkinter.font import Font
from threading import Thread
from pyautogui import click
from time import time


CANCEL_BUTTON = "esc"
DEBUG = False


class NotABotUI:

    # Controls
    start_button_keybind = "escape"
    stop_button_keybind = "escape"

    # Application Logic
    bluetooth_device_list = None
    bluetooth_controller = None
    bluetooth_loop = None
    ekg_loop = None
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


    def __init__(self, root, bluetooth_loop, ekg_loop, heart_beat_loop):
        self.root = root
        self.bluetooth_loop = bluetooth_loop
        self.ekg_loop = ekg_loop
        self.heart_beat_loop = heart_beat_loop

        self.bluetooth_controller = BluetoothController(self, self.bluetooth_loop)
        self.bluetooth_device_list = BluetoothDeviceList(self, self.bluetooth_loop, self.bluetooth_controller)
        
        # Make a custom font
        self.custom_font = Font(family=ui.font, size=ui.lg_font)
        font_path = "path/to/your/font.ttf"  # Update with your actual path

        # Register the font in Tkinter
        if os_path.exists(font_path):
            self.custom_font.actual()
            root.tk.call("font", "create", ui.font, "-family", ui.font, "-size", ui.lg_font)
            root.tk.call("font", "configure", ui.font, "-family", ui.font)

        # Call async functions using the bluetooth_loop like so:
        #  asyncio.run_coroutine_threadsafe(async_function(), self.bluetooth_loop)
        self.create_ui(root)

        # Listeners
        self.listen_for_toggle()


    def create_ui(self, root):
        self.root.title("I <3 Clicking")
        self.root.geometry("280x440")
        self.root.config(bg=ui.background_color)
        self.root.protocol("WM_DELETE_WINDOW", self.close_application)

        # Set the icon
        icon_path = self.resource_path("img/heart.ico")
        png_path = self.resource_path("img/heart.png")

        self.root.iconbitmap(icon_path)
        self.root.iconbitmap(default=icon_path)
        icon_img = ImageTk.PhotoImage(file=png_path)
        self.root.iconphoto(True, icon_img)

        # Create a frame to center the elements
        self.frame = tk.Frame(root)
        self.frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.frame.config(bg=ui.foreground_color)

        # Heart and EKG content
        original_heart_image = Image.open(png_path)
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


        # Buttons & Buttons Logic
        #   Start/Stop Button
        self.start_stop_button = tk.Button(self.frame, text=self.START_TEXT, command=self.toggle_start_stop)
        self.start_stop_button.grid(row=3, column=0, padx=10, pady=4)
        self.start_stop_button.config(height=1, bg=ui.start_button_color, font=(ui.font, ui.xl_font))

        #   Connect Button
        self.bluetooth_devices_button = tk.Button(self.frame, text="Connect Device", command=lambda: asyncio.run_coroutine_threadsafe(self.toggle_bluetooth_devices(), self.bluetooth_loop))
        self.bluetooth_devices_button.grid(row=3, column=1, padx=10, pady=4)
        self.bluetooth_devices_button.config(height=1, bg=ui.bluetooth_button_color, font=(ui.font, ui.xl_font))

        #  Bluetooth Device Texts
        self.bluetooth_text = tk.Message(self.frame, text=f"{self.bluetooth_device_verbiage}{self.bluetooth_controller.selected_device_name}", width=200)
        self.bluetooth_text.grid(row=4, columnspan=2, padx=10, pady=0)
        self.bluetooth_text.config(bg=ui.foreground_color, font=(ui.font, ui.lg_font))


    # Start and stop button control
    def toggle_start_stop(self):
        # When there is no Bluetooth device connected, open the Bluetooth device list
        if not self.bluetooth_controller.is_bluetooth_device_connected and not DEBUG:
            print("No Bluetooth device connected. Please connect a device first.")
            self.bluetooth_device_list.open_bluetooth_devices()

        elif self.is_running:
            self.stop_actions()
        
        else:
            self.start_actions()
    

    # Stops the BPM measuyrement and clicking actions of the application
    def stop_actions(self):
        self.is_running = False
        self.start_stop_button.config(text=self.START_TEXT, bg=ui.start_button_color)
        self.bluetooth_controller.stop_heart_rate_monitor()


    # Start the heart rate monitoring, EKG visualization, and clicking actions
    def start_actions(self):
        self.is_running = True
        self.start_stop_button.config(text=self.STOP_TEXT, bg=ui.stop_button_color)

        if DEBUG:
            asyncio.run_coroutine_threadsafe(self.simulate_heart_rate(), self.bluetooth_loop)
        else:
            asyncio.run_coroutine_threadsafe(self.bluetooth_controller.start_heart_rate_monitor(), self.bluetooth_loop)

        asyncio.run_coroutine_threadsafe(self.start_ekg(), self.ekg_loop)


    # Bluetooth button logic
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
        click()

    
    # Listens for keyboard strokes to start and stop the heart rate monitor / clicker
    def listen_for_toggle(self):
        print(f"Listening for '{self.start_button_keybind}' keybind...")
        if not self.is_closing_application:
            add_hotkey(self.start_button_keybind, self.toggle_start_stop)


    # Used to close the application properly
    def close_application(self):
        self.is_closing_application = True
        self.root.destroy()
        self.bluetooth_loop.call_soon_threadsafe(self.bluetooth_loop.stop)
        exit(0)


    # Begins reading BPM data and plotting EKG data on the graph
    async def start_ekg(self):
        
        self.flatline_ekg()

        if self.current_bpm == 0:
            print("No BPM data available. Please start the heart rate monitor first.")
            self.toggle_start_stop()
            return

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
        await asyncio.sleep(2)  
        print("Starting EKG visualization")

        beat_counter = 0
        start_time = time()
        
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
                beat_start_time = time()
                
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

                # Calculate how long the beat took
                beat_elapsed = time() - beat_start_time

                # If we finished faster than the BPM needed, sleep the difference
                if beat_elapsed < seconds_per_beat:
                    await asyncio.sleep(seconds_per_beat - beat_elapsed)
                
                # # Log performance stats every 10 beats
                if beat_counter % 10 == 0:
                    elapsed = time() - start_time
                    expected = beat_counter * seconds_per_beat
                    print(f"EKG Counter: {beat_counter}, Elapsed: {elapsed:.2f}s, Expected: {expected:.2f}s, Drift: {elapsed-expected:.2f}s")
            
        finally:
            # This block will execute when the loop ends for any reason
            self.flatline_ekg()


    # # # # # # # # #
    # 
    #  Sub Functions
    # 
    # # # # # # # # #


    # Called by the Bluetooth controller when a new heart rate is received
    def heart_rate_handler(self, sender, data):
        heart_rate = data[1]
        print(f"Heart Rate: {heart_rate} bpm")
        self.update_bpm(heart_rate)


    # Updates the BPM data and label
    def update_bpm(self, heart_rate):
        self.current_bpm = heart_rate
        self.bpm_data.append(heart_rate)
        self.bpm_label.config(text=f"BPM: {heart_rate}")
        self.root.update()


    # Debugging function
    # Simulate heart rate data for demonstration purposes
    async def simulate_heart_rate(self):
        heart_rate_change = 3
        heart_rate_change_chance = 0.4
        while self.is_running and not self.is_closing_application:
            last_heart_rate = self.bpm_data[-1] if self.bpm_data else randint(60, 100)
            if random() > heart_rate_change_chance:
                heart_rate = last_heart_rate
            else:
                heart_rate = randint(max(60, last_heart_rate - heart_rate_change), min(100, last_heart_rate + heart_rate_change))
            self.update_bpm(heart_rate)
            await asyncio.sleep(1)


    # Resets the EKG graph to appear as a flatline
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
            if point_idx == 9 or point_idx == 11 or point_idx == 12:
                self.toggle_heart_image()
                await asyncio.sleep(0.01)
            # Perform a click at the peak R wave
            elif point_idx == 10:
                asyncio.run_coroutine_threadsafe(self.click_screen(0), self.heart_beat_loop)
                await asyncio.sleep(0.01)
                self.toggle_heart_image()
                await asyncio.sleep(0.01)
            
            # Calculate exact time for this point
            point_time = beat_start_time + (point_idx * seconds_per_point)
            current_time = time()
            
            # Sleep precisely until next point time
            sleep_time = max(0.001, point_time - current_time)
            await asyncio.sleep(sleep_time)


    def resource_path(self, relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os_path.abspath(".")

        return os_path.join(base_path, relative_path)


if __name__ == "__main__":

    bluetooth_loop = asyncio.new_event_loop()
    bluetooth_loop_thread = Thread(target=bluetooth_loop.run_forever, daemon=True)
    bluetooth_loop_thread.start()
    asyncio.set_event_loop(bluetooth_loop)

    ekg_loop = asyncio.new_event_loop()
    ekg_loop_thread = Thread(target=ekg_loop.run_forever, daemon=True)
    ekg_loop_thread.start()

    heart_beat_loop = asyncio.new_event_loop()
    heart_beat_loop_thread = Thread(target=heart_beat_loop.run_forever, daemon=True)
    heart_beat_loop_thread.start()

    root = tk.Tk()
    app = NotABotUI(
        root,
        bluetooth_loop,
        ekg_loop,
        heart_beat_loop,
    )
    root.mainloop()

