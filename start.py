import asyncio

from polar_funcs import (
    get_heart_rate,
    set_h10_values,
    connect_to_h10,
    get_heart_rate,
    listen_for_cancel,
)


# The main set of instructions for this application
async def application_loop():
    # Listen for the cancel button
    asyncio.create_task(listen_for_cancel())

    # Obtain the initial H10 values needed to poll the device
    await set_h10_values()
        
    # Attempt to connect to the Polar H10
    client = await connect_to_h10()

    # Print the H10 heart rate values
    await get_heart_rate(client)


if __name__ == "__main__":
    asyncio.run(application_loop())
