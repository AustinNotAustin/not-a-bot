from asyncio import create_task, sleep
from bleak import BleakClient

'''
Used to manage bluetooth connections,
read data,
keep alive,
and call actions based on the data
'''

class BluetoothController:

    # The NotABot UI instance
    parent_instance = None
    bluetooth_loop = None

    # Bluetooth Device Information
    client = None

    selected_device_name = "Not Connected"
    selected_device_address = None
    selected_device_characteristic_uuid = None

    is_bluetooth_device_connected = False
    is_bluetooth_device_list_error = False
    is_heart_rate_monitor_running = False

    HEART_RATE_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
    HEART_RATE_CHAR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
    
    SCANNING_RETRY_SLEEP = 2
    BLUETOOTH_RECONNECT_RETRY_SLEEP = 2
    BLUETOOTH_KEEP_ALIVE_SLEEP = 5
    LISTEN_FOR_CANCEL_SLEEP_TIME = 0.1

    # Bluetooth Threads
    bluetooth_loop = None


    def __init__(self, parent_instance, bluetooth_loop):
        self.parent_instance = parent_instance
        self.bluetooth_loop = bluetooth_loop
    

    async def connect_bluetooth(self):
        print(f"Attempting connect to {self.selected_device_name}  ({self.selected_device_address})...")
        while self.client is None:
            try:
                print("Client is None. Attempting to connect...")
                self.client = BleakClient(self.selected_device_address)
                await self.client.connect()

                self.is_bluetooth_device_connected = True
                self.parent_instance.bluetooth_text.config(text=f"{self.parent_instance.bluetooth_device_verbiage}{self.selected_device_name}")
                self.parent_instance.bluetooth_devices_button.config(text="Disconnect")

                create_task(self.bluetooth_keep_alive())

            except Exception as e:
                print(f"Connection error: {e}. Retrying in {self.BLUETOOTH_RECONNECT_RETRY_SLEEP} seconds...")
                self.parent_instance.bluetooth_text.config(text=f"{self.parent_instance.bluetooth_device_verbiage}Connecting...")
                await sleep(self.BLUETOOTH_RECONNECT_RETRY_SLEEP)
    

    # Connect to a defined Bluetooth device and keep the connection alive
    async def bluetooth_keep_alive(self):
        while self.client is not None:
            try:
                if not self.client.is_connected:
                    await self.client.connect()
                    self.is_bluetooth_device_connected = True
                    print(f"Reconnected to {self.selected_device_name} ({self.selected_device_address})")
                else:
                    print("Bluetooth device is kept alive.")
            except Exception as e:
                print(f"Connection error: {e}")
                await self.disconnect_bluetooth_device()
            # Sleep before trying a keep alive again
            await sleep(self.BLUETOOTH_KEEP_ALIVE_SLEEP)
    

    # Begins reading heart rate data from the Bluetooth device
    async def start_heart_rate_monitor(self):
        if not self.is_bluetooth_device_connected:
            print("Bluetooth device is not connected.")
            return

        # Fetch services and characteristics
        self.selected_device_characteristic_uuid = await self.search_for_characteristic_uuid()
        
        # Some devices might not support heart rate measurement
        if not self.selected_device_characteristic_uuid:
            print("BPM Char UUID not found.\nPerhaps device does not support BPM?")
            return

        try:
            await self.client.start_notify(self.selected_device_characteristic_uuid, self.parent_instance.heart_rate_handler)        
            self.is_heart_rate_monitor_running = True
        
        except Exception as e:
            print(f"Error encountered while starting notifications:\n{e}")
            self.stop_heart_rate_monitor()


    def stop_heart_rate_monitor(self):
        self.is_heart_rate_monitor_running = False


    # Handle a situation where the bluetooth device disconnects
    async def disconnect_bluetooth_device(self):
        print("Disconnecting from Bluetooth device...")
        try:
            await self.client.disconnect()
        except:
            pass

        self.selected_device_name = "Not Connected"
        self.parent_instance.bluetooth_text.config(text=f"{self.parent_instance.bluetooth_device_verbiage}{self.selected_device_name}")
        self.parent_instance.bluetooth_devices_button.config(text="Connect Device")
        self.is_bluetooth_device_connected = False

        if self.is_heart_rate_monitor_running:
            self.stop_heart_rate_monitor()

        self.parent_instance.stop_actions()

        self.client = None


    # # # # # # # #
    #
    # Sub Functions
    #
    # # # # # # # #   
 
    # Returns the characteristic UUID for the heart rate service or None
    # Uses the predefined HEART_RATE_SERVICE_UUID and HEART_RATE_CHAR_UUID
    # Those UUIDs are defined in the Bluetooth GATT specification
    async def search_for_characteristic_uuid(self):
        # Ensure the client is connected before fetching services
        if not self.client or not await self.client.is_connected():
            print("Bluetooth client is not connected.")
            return None

        services = await self.client.get_services()
        for service in services:
            if service.uuid.lower() == self.HEART_RATE_SERVICE_UUID.lower():
                for char in service.characteristics:
                    if char.uuid.lower() == self.HEART_RATE_CHAR_UUID.lower():
                        return char.uuid
        
        print("ERROR: No characteristic UUID found.\nDoes the device support Heart Rate Measurement?")
        return None
