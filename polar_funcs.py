import global_vars
import keyboard
import asyncio

from bleak import BleakScanner, BleakClient


# Attempt to connect to the Polar H10 and obtain the initial values needed to poll the device
async def set_h10_values():
    device = None

    # Attempt to find the Polar H10 device
    while device is None:
        print(f"Scanning for {global_vars.DEVICE_NAME}...")
        device = await BleakScanner.find_device_by_name(global_vars.DEVICE_NAME)

    async with BleakClient(device.address) as client:
        print(f"Connected to {device.address}")

        global_vars.H10_ADDRESS = device.address
        print(f"H10_ADDRESS: {global_vars.H10_ADDRESS}")
        
        services = await client.get_services()
        for service in services:
            print(f"Service: {service.uuid}")
            for char in service.characteristics:
                print(f"  Characteristic: {char.uuid}")
                if 'notify' in char.properties:
                    global_vars.H10_CHARACTERISTIC_UUID = char.uuid
                    print(f"H10_CHARACTERISTIC_UUID: {global_vars.H10_CHARACTERISTIC_UUID}")
                    return
        
        if global_vars.H10_CHARACTERISTIC_UUID is None:
            print("No suitable characteristic found for heart rate notifications.")


# Attempt to connect to the Polar H10 and return the client object
#   Sleeps for SCANNING_SLEEP seconds if the connection fails
async def connect_to_h10():
    client = None

    while client is None:
        try:
            client = BleakClient(global_vars.H10_ADDRESS)
            await client.connect()
            return client
        except Exception as e:
            print(f"Connection error: {e}. Retrying in {global_vars.SCANNING_SLEEP} seconds...")
            await asyncio.sleep(global_vars.SCANNING_SLEEP)
            continue


# Print the heart rate values from the Polar H10
async def get_heart_rate(client):
    
    def heart_rate_handler(sender, data):
        heart_rate = data[1]
        print(f"Heart Rate: {heart_rate} bpm")

    await client.start_notify(global_vars.H10_CHARACTERISTIC_UUID, heart_rate_handler)
    try:
        while await client.is_connected():
            await asyncio.sleep(10)
    finally:
        await client.stop_notify(global_vars.H10_CHARACTERISTIC_UUID)


# Listen for the CANCEL_BUTTON to be pressed, and if it is, stop the application
async def listen_for_cancel():
    while True:
        if keyboard.is_pressed(global_vars.CANCEL_BUTTON):
            print("Cancel button pressed. Exiting...")
            print(f"H10_ADDRESS: {global_vars.H10_ADDRESS}")
            print(f"H10_CHARACTERISTIC_UUID: {global_vars.H10_CHARACTERISTIC_UUID}")
            exit(0)
        await asyncio.sleep(global_vars.LISTEN_FOR_CANCEL_SLEEP_TIME)
