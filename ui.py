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


START_TEXT = f"Start ({CANCEL_BUTTON})"
STOP_TEXT = f"Stop ({CANCEL_BUTTON})"


class BlueToothController:
    # Bluetooth Device Information
    device_name = "Not Connected"
    device_address = None
    device_characteristic_uuid = None

    # Controls
    start_button = "escape"
    stop_button = "escape"

    # Application Logic
    is_running = False
    client = None
    bpm_data = []
    
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
        self.bluetooth_text = tk.Message(self.frame, text=f"Bluetooth Device:\n{self.device_name}", width=200)
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


    def toggle_start_stop(self):
        if self.is_running:
            self.start_stop_button.config(text=START_TEXT, bg=self.start_button_color)
            self.is_running = False
        else:
            self.start_stop_button.config(text=STOP_TEXT, bg=self.stop_button_color)
            self.is_running = True
            threading.Thread(target=self.simulate_run_heart_rate_monitor).start()
            # threading.Thread(target=self.run_heart_rate_monitor).start()

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

        self.button_frame = tk.Frame(self.scan_frame, bg=self.background_color)
        self.button_frame.pack(side=tk.TOP, fill=tk.BOTH, padx=10, pady=10)

        self.connect_button = tk.Button(self.button_frame, text="Connect", command=self.connect_bluetooth)
        self.connect_button.config(height=2, bg=self.bluetooth_button_color, font=(self.font, self.xl_font))
        self.connect_button.pack(side=tk.LEFT, padx=10, pady=10)

        self.refresh_button = tk.Button(self.button_frame, text="Refresh", command=self.list_bluetooth_devices)
        self.refresh_button.config(height=2, bg=self.refresh_button_color, font=(self.font, self.xl_font))
        self.refresh_button.pack(side=tk.RIGHT, padx=10, pady=10)

        # Run the scan in a separate thread
        threading.Thread(target=self.run_blue_tooth_scan).start()

    def run_blue_tooth_scan(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.list_bluetooth_devices())
    

    async def list_bluetooth_devices(self):
        # Clear the listbox
        self.device_listbox.delete(0, tk.END)

        # Add a scanning message
        self.device_listbox.insert(tk.END, "Scanning for Bluetooth devices...")

        # Discover Bluetooth devices
        devices = await BleakScanner.discover()
        max_name_length = 10

        # Iterate once to obtain the max name length
        # have to iterate twice b/c 1st name might be shorter than 2nd name
        for device in devices:
            device_name = device.name if device.name is not None else "Unknown Name"
            max_name_length = max(max_name_length, len(device_name) + 2)

        # Iterate again to insert devices into the listbox
        for device in devices:
            self.device_listbox.insert(tk.END, f"{device_name:<{max_name_length}} {device.address}")
        
        # Delete the scanning message
        self.device_listbox.delete(0)

    def connect_bluetooth(self):
        pass


    # Connect to a defined Bluetooth device and keep the connection alive
    async def connect_and_keep_alive(self):
        while True:
            try:
                if self.client is None:
                    self.client = await BleakClient.connect(self.device_address)
                else:
                    if not self.client.is_connected:
                        await self.client.connect()
                await asyncio.sleep(5)
            except Exception as e:
                print(f"Connection error: {e}")
                self.client = None
                await asyncio.sleep(5)


    # Simulate heart rate data for demonstration purposes
    def simulate_run_heart_rate_monitor(self):
        while self.is_running:
            heart_rate = random.randint(60, 100)
            self.plot_heart_rate_data(heart_rate)
            time.sleep(1)


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


if __name__ == "__main__":
    root = tk.Tk()
    app = BlueToothController(root)
    root.mainloop()
