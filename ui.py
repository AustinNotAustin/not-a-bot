import matplotlib.pyplot as plt
import tkinter as tk
import threading
import asyncio
import random
import time

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from bleak import BleakClient, BleakScanner
from global_vars import CANCEL_BUTTON
from matplotlib import font_manager
from tkinter import TclError


START_TEXT = f"Start ({CANCEL_BUTTON})"
STOP_TEXT = f"Stop ({CANCEL_BUTTON})"


class BlueToothController:
    # Bluetooth Device Information
    selected_device_name = "Not Connected"
    selected_device_address = None
    selected_device_characteristic_uuid = None

    # Bluetooth Variables
    HEART_RATE_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
    HEART_RATE_CHAR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

    # Controls
    start_button = "escape"
    stop_button = "escape"

    # Application Logic
    is_closing_application = False
    is_running = False
    client = None
    bpm_data = []
    threads = []  # List to keep track of threads

    # Application Variables
    SCANNING_RETRY_SLEEP = 2
    BLUETOOTH_KEEP_ALIVE_SLEEP = 5
    bluetooth_device_verbiage = "Bluetooth Device:\n"
    
    # Design Variables
    font = "Dogica"
    xl_font = 12
    lg_font = 10
    md_font = 8
    sm_font = 6
    xs_font = 4
    background_color = "#DEB887"
    foreground_color = "#F5DEB3"
    start_button_color= "#6B8E23"
    stop_button_color = "#A0522D"
    bluetooth_button_color = "#4682B4"
    graph_background_color = "#D2B48C"
    graph_foreground_color = "#FAEBD7"
    heart_rate_line_color = "#FF7F50"
    refresh_button_color = "#A9A9A9"


    def __init__(self, root):
        self.root = root
        self.root.title("Bluetooth Controller")
        self.root.geometry("900x600")
        self.root.config(bg=self.background_color)
        self.root.protocol("WM_DELETE_WINDOW", self.close_application)

        # Create a frame to center the elements
        self.frame = tk.Frame(root)
        self.frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.frame.config(bg=self.foreground_color)

        # Buttons & Buttons Logic
        #   Start/Stop Button
        self.start_stop_button = tk.Button(self.frame, text=START_TEXT, command=self.toggle_start_stop)
        self.start_stop_button.grid(row=0, column=0, padx=10, pady=10)
        self.start_stop_button.config(height=2, bg=self.start_button_color, font=(self.font, self.xl_font))

        #   Connect Button
        self.bluetooth_devices_button = tk.Button(self.frame, text="Connect Device", command=self.open_bluetooth_devices)
        self.bluetooth_devices_button.grid(row=0, column=1, padx=10, pady=10)
        self.bluetooth_devices_button.config(height=2, bg=self.bluetooth_button_color, font=(self.font, self.xl_font))

        #  Bluetooth Device Texts
        self.bluetooth_text = tk.Message(self.frame, text=f"{self.bluetooth_device_verbiage}{self.selected_device_name}", width=200)
        self.bluetooth_text.grid(row=0, column=2, padx=10, pady=10)
        self.bluetooth_text.config(bg=self.foreground_color, font=(self.font, self.lg_font))

        # Matplotlib figure and axis
        self.fig, self.ax = plt.subplots()
        self.fig.patch.set_facecolor(self.graph_background_color)

        # Matplotlib graph title and labels
        matplotlib_font = font_manager.FontProperties(fname="./font/Dogica.ttf")

        self.ax.title.set_fontproperties(matplotlib_font)
        self.ax.title.set_fontsize(self.lg_font)
        
        self.ax.xaxis.label.set_fontproperties(matplotlib_font)
        self.ax.xaxis.label.set_fontsize(self.lg_font)
        
        self.ax.yaxis.label.set_fontproperties(matplotlib_font)
        self.ax.yaxis.label.set_fontsize(self.lg_font)
        
        self.ax.set_facecolor(self.graph_foreground_color)
        
        self.line, = self.ax.plot([], [], color=self.heart_rate_line_color)

        for label in self.ax.get_xticklabels():
            label.set_fontproperties(matplotlib_font)
            label.set_fontsize(self.sm_font)
        
        for label in self.ax.get_yticklabels():
            label.set_fontproperties(matplotlib_font)
            label.set_fontsize(self.sm_font)

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
        if self.is_running:
            self.start_stop_button.config(text=START_TEXT, bg=self.start_button_color)
            self.is_running = False
            self.stop_heart_rate_monitor()
        elif self.client is not None:
            self.start_stop_button.config(text=STOP_TEXT, bg=self.stop_button_color)
            self.is_running = True
            self.start_thread(self.run_heart_rate_monitor)
            # threading.Thread(target=self.run_heart_rate_monitor, daemon=True).start()
        else:
            print("No Bluetooth device connected. Please connect a device first.")
            self.open_bluetooth_devices()

        self.line.set_xdata(range(len(self.bpm_data)))
        self.line.set_ydata(self.bpm_data)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()
    

    # Opens a new window to list available Bluetooth devices
    def open_bluetooth_devices(self):
        self.scan_window = tk.Toplevel(self.root)
        self.scan_window.title("Available Bluetooth Devices")
        self.scan_window.config(bg=self.background_color)

        # Create a frame to center the elements
        self.scan_frame = tk.Frame(self.scan_window, bg=self.background_color)
        self.scan_frame.pack(fill=tk.BOTH, expand=True)

        self.device_listbox = tk.Listbox(self.scan_frame, width=40, height=30)
        self.device_listbox.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.device_listbox.config(bg=self.foreground_color, font=(self.font, self.xl_font))

        self.device_listbox.bind("<<ListboxSelect>>", self.on_device_select)

        self.button_frame = tk.Frame(self.scan_frame, bg=self.background_color)
        self.button_frame.pack(side=tk.TOP, fill=tk.BOTH, padx=10, pady=10)

        self.connect_button = tk.Button(self.button_frame, text="Connect", command=lambda: self.start_thread(self.connect_bluetooth))
        self.connect_button.config(height=2, bg=self.bluetooth_button_color, font=(self.font, self.xl_font))
        self.connect_button.pack(side=tk.LEFT, padx=10, pady=10)

        self.refresh_button = tk.Button(self.button_frame, text="Refresh", command=lambda: self.start_thread(self.run_blue_tooth_scan))
        self.refresh_button.config(height=2, bg=self.refresh_button_color, font=(self.font, self.xl_font))
        self.refresh_button.pack(side=tk.RIGHT, padx=10, pady=10)

        # Start the Bluetooth scan
        self.start_thread(self.run_blue_tooth_scan)


    # Scans for Bluetooth devices and lists them by calling list_bluetooth_devices
    def run_blue_tooth_scan(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.list_bluetooth_devices())


    async def connect_bluetooth(self):
        print(f"Connecting to {self.selected_device_name}  ({self.selected_device_address})...")
        while self.client is None:
            try:
                print("Attempting to connect...")
                self.client = BleakClient(self.selected_device_address)
                await self.client.connect()

                self.start_thread(self.bluetooth_keep_alive)
                self.bluetooth_text.config(text=f"{self.bluetooth_device_verbiage}{self.selected_device_name}")
                self.scan_window.destroy()
            except Exception as e:
                print(f"Connection error: {e}. Retrying in {self.SCANNING_RETRY_SLEEP} seconds...")
                await asyncio.sleep(self.SCANNING_RETRY_SLEEP)


    # Connect to a defined Bluetooth device and keep the connection alive
    async def bluetooth_keep_alive(self):
        while not self.is_closing_application:
            try:
                if not self.client.is_connected:
                    await self.client.connect()
            except Exception as e:
                print(f"Connection error: {e}")
                self.client = None
            # Sleep before trying a keep alive again
            await asyncio.sleep(self.BLUETOOTH_KEEP_ALIVE_SLEEP)


    # Begins reading heart rate data from the Bluetooth device
    async def run_heart_rate_monitor(self):
        # Fetch services and characteristics
        self.selected_device_characteristic_uuid = await self.search_for_characteristic_uuid()
        
        if not self.selected_device_characteristic_uuid:
            print("No characteristic UUID found. Does the device support Heart Rate Measurement?")
            return

        def heart_rate_handler(sender, data):
            heart_rate = data[1]
            self.plot_heart_rate_data(heart_rate)
            print(f"Heart Rate: {heart_rate} bpm")

        await self.client.start_notify(self.selected_device_characteristic_uuid, heart_rate_handler)
        try:
            while await self.client.is_connected() and self.is_running and not self.is_closing_application:
                await asyncio.sleep(self.BLUETOOTH_KEEP_ALIVE_SLEEP)
        finally:
            await self.client.stop_notify(self.selected_device_characteristic_uuid)


    def stop_heart_rate_monitor(self):
        self.is_running = False
        asyncio.run_coroutine_threadsafe(self.client.stop_notify(self.selected_device_characteristic_uuid), asyncio.get_event_loop())


    # Used to close the application properly
    def close_application(self):
        self.is_closing_application = True
        self.root.destroy()
        exit(0)


    # # # # # # # # #
    # 
    #  Sub Functions
    # 
    # # # # # # # # #

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


    # Starts any thread as a target and adds it to a list of threads for tracking
    # Currently isn't used, but might be needed to ensure threads are killed later
    def start_thread(self, target):
        print(f"Starting thread for {target.__name__}")

        if asyncio.iscoroutinefunction(target):
            loop = asyncio.new_event_loop()
            threading.Thread(target=self.run_async, args=(target, loop), daemon=True).start()
        else:
            thread = threading.Thread(target=target, daemon=True)
            thread.start()
            self.threads.append(thread)


    # Runs an async function in a new event loop
    def run_async(self, target, loop):
        asyncio.set_event_loop(loop)
        loop.run_until_complete(target())
    

    # Called by self.run_blue_tooth_scan to list Bluetooth devices
    async def list_bluetooth_devices(self):
        try:
            # Clear the listbox
            if not self.is_closing_application:
                self.device_listbox.delete(0, tk.END)

            # Add a scanning message
            if not self.is_closing_application:
                self.device_listbox.insert(tk.END, "Scanning for Bluetooth devices...")

            # Discover Bluetooth devices
            devices = await BleakScanner.discover()
            max_name_length = 10

            # Iterate once to obtain the max name length
            # have to iterate twice b/c 1st name might be shorter than 2nd name
            for device in devices:
                selected_device_name = device.name if device.name is not None else "Unknown Name"
                max_name_length = max(max_name_length, len(selected_device_name) + 2)

            # Iterate again to insert devices into the listbox
            for device in devices:
                if not self.is_closing_application:                
                    selected_device_name = device.name if device.name is not None else "Unknown Name"
                    self.device_listbox.insert(tk.END, f"{selected_device_name:<{max_name_length}} {device.address}")
            
            # Delete the scanning message
            if not self.is_closing_application:
                self.device_listbox.delete(0)
        except TclError as e:
            # We expect this error when the window is closed before completing.
            print(f"TclError encountered: {e}")
            return


    # Returns the characteristic UUID for the heart rate service or None
    async def search_for_characteristic_uuid(self):
        services = await self.client.get_services()
        for service in services:
            if service.uuid.lower() == self.HEART_RATE_SERVICE_UUID.lower():
                for char in service.characteristics:
                    if char.uuid.lower() == self.HEART_RATE_CHAR_UUID.lower():
                        return char.uuid
        
        return None


    # Called when a device is selected from the Bluetooth devices listbox
    def on_device_select(self, event):
        selected_index = self.device_listbox.curselection()
        if selected_index:
            device_info = self.device_listbox.get(selected_index)
            device_name, device_address = device_info.rsplit(" ", 1)
            self.selected_device_name = device_name
            self.selected_device_address = device_address


if __name__ == "__main__":
    root = tk.Tk()
    app = BlueToothController(root)
    root.mainloop()
