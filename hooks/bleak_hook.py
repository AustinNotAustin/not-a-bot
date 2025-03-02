import sys

# Make sure the Windows backend is fully loaded
if sys.platform == 'win32':
    import bleak
    from bleak.backends.winrt.scanner import BleakScannerWinRT
    from bleak.backends.winrt.client import BleakClientWinRT

