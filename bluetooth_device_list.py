import ui_design_variables as ui
import tkinter as tk

import asyncio

from bleak import BleakScanner


'''
Used specifically to open a new window to list available Bluetooth devices
Includes a Connect and Refresh button

'''
class BluetoothDeviceList:

    parent_ui_instance = None
    bluetooth_loop = None
    bluetooth_controller = None

    is_bluetooth_window_open = False


    def __init__(self, parent_instance, bluetooth_loop, bluetooth_controller):
        self.parent_instance = parent_instance
        self.bluetooth_loop = bluetooth_loop
        self.bluetooth_controller = bluetooth_controller


    # Opens a new window to list available Bluetooth devices
    def open_bluetooth_devices(self):
        try:
            self.scan_window.lift()
        except Exception:
            self.is_bluetooth_window_open = False  # Reset the flag if the window no longer exists
            self.create_bluetooth_devices_window()
            asyncio.run_coroutine_threadsafe(self.list_bluetooth_devices(), self.bluetooth_loop)


    # Creates a new window to list available Bluetooth devices
    def create_bluetooth_devices_window(self):
        self.scan_window = tk.Toplevel(self.parent_instance.root)
        self.scan_window.title("Available Bluetooth Devices")
        self.scan_window.config(bg=ui.background_color)
        self.scan_window.protocol("WM_DELETE_WINDOW", self.on_bluetooth_window_close)

        # Create a frame to center the elements
        self.scan_frame = tk.Frame(self.scan_window, bg=ui.background_color)
        self.scan_frame.pack(fill=tk.BOTH, expand=True)

        self.device_listbox = tk.Listbox(self.scan_frame, width=40, height=30)
        self.device_listbox.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.device_listbox.config(bg=ui.foreground_color, font=(ui.font, ui.xl_font))

        self.device_listbox.bind("<<ListboxSelect>>", self.on_device_select)

        self.button_frame = tk.Frame(self.scan_frame, bg=ui.background_color)
        self.button_frame.pack(side=tk.TOP, fill=tk.BOTH, padx=10, pady=10)

        self.connect_button = tk.Button(self.button_frame, text="Connect", command=lambda: asyncio.run_coroutine_threadsafe(self.bluetooth_controller.connect_bluetooth(), self.bluetooth_loop))
        self.connect_button.config(height=2, bg=ui.bluetooth_button_color, font=(ui.font, ui.xl_font))
        self.connect_button.pack(side=tk.LEFT, padx=10, pady=10)

        self.refresh_button = tk.Button(self.button_frame, text="Refresh", command=lambda: asyncio.run_coroutine_threadsafe(self.list_bluetooth_devices(), self.bluetooth_loop))
        self.refresh_button.config(height=2, bg=ui.refresh_button_color, font=(ui.font, ui.xl_font))
        self.refresh_button.pack(side=tk.RIGHT, padx=10, pady=10)

        self.is_bluetooth_window_open = True

    
    # Called by the refresh button to list Bluetooth devices
    async def list_bluetooth_devices(self):
        try:
            # Clear the listbox
            self.device_listbox.delete(0, tk.END)

            # Add a scanning message
            self.device_listbox.insert(tk.END, "Scanning for Bluetooth devices...")

            # Discover Bluetooth devices
            devices = await BleakScanner.discover()

            # Iterate once to obtain the max name length
            #  Required b/c the first name in the list might be the shortest (thus breaking formatting)
            max_name_length = 10

            for device in devices:
                selected_device_name = device.name if device.name is not None else "Unknown Name"
                max_name_length = max(max_name_length, len(selected_device_name) + 2)

            # Iterate again to insert devices into the listbox
            for device in devices:              
                selected_device_name = device.name if device.name is not None else "Unknown Name"
                self.device_listbox.insert(tk.END, f"{selected_device_name:<{max_name_length}} {device.address}")

            # Delete the scanning message
            self.device_listbox.delete(0)

        except Exception as e:
            # We expect this error if the window is closed before completing.
            error_message = "Error while listing bluetooth devices:"
            print(f"{error_message}\n{e}")
            self.device_listbox.delete(0)
            self.device_listbox.insert(tk.END, error_message)
            self.device_listbox.insert(tk.END, e)
            return
    

    # Calls the appropriate controller function to connect to the selected device
    def connect_to_device(self):
        asyncio.run_coroutine_threadsafe(self.bluetooth_controller.connect_bluetooth(), self.bluetooth_loop)
        self.scan_window.destroy()


    # Called when a device is selected from the Bluetooth devices listbox
    def on_device_select(self, event):
        selected_index = self.device_listbox.curselection()
        if selected_index:
            device_info = self.device_listbox.get(selected_index)
            device_name, device_address = device_info.rsplit(" ", 1)
            self.bluetooth_controller.selected_device_name = device_name
            self.bluetooth_controller.selected_device_address = device_address

    
    def on_bluetooth_window_close(self):
        self.is_bluetooth_window_open = False
        self.scan_window.destroy()
