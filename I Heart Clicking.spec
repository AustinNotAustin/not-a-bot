# -*- mode: python ; coding: utf-8 -*-
import os
import sys
import bleak
import importlib.util

block_cipher = None

# Check if winrt is installed and available
winrt_available = importlib.util.find_spec('winrt') is not None
print(f"winrt available: {winrt_available}")

if winrt_available:
    try:
        import winrt
        winrt_path = os.path.dirname(winrt.__file__)
        print(f"winrt Path: {winrt_path}")
    except (ImportError, TypeError, AttributeError) as e:
        print(f"Error importing winrt: {e}")
        winrt_path = None
else:
    print("winrt module not available - Bluetooth functionality may be limited")
    winrt_path = None

# Look for Bleak Location, Debugging
bleak_path = os.path.dirname(bleak.__file__)
print(f"Bleak Path: {bleak.__path__}")

datas=[
    ('img/*', 'img/'),
    ('font/*', 'font/'),
    ('ui_design_variables.py', '.'),
    ('bluetooth_controller.py', '.'),
    ('bluetooth_device_list.py', '.'),
    (bleak_path, 'bleak'),
]

# Add winrt path if available
if winrt_path:
    datas.append((winrt_path, 'winrt'))

a = Analysis(
    ['start.py'],
    pathex=[],
    binaries=[
        # Windows Runtime Bluetooth DLLs
        ('C:/Windows/System32/WindowsCodecs.dll', '.'),
        ('C:/Windows/System32/bthprops.cpl', '.'),
        ('C:/Windows/System32/BluetoothApis.dll', '.'),
    ],
    datas=datas,
    hiddenimports=[
        'PIL._tkinter_finder', 
        'keyboard', 
        'pyautogui',
        'bleak',

        # Add winrt and its required submodules
        'winrt',
        'winrt.windows',
        'winrt.windows.foundation',
        'winrt.windows.foundation.collections',
        'winrt.windows.devices',
        'winrt.windows.devices.bluetooth',
        'winrt.windows.devices.bluetooth.advertisement',
        
        # Add these updated imports instead
        'bleak.backends.winrt',
        'bleak.backends.scanner',
        'bleak.backends.characteristic',
        'bleak.backends.descriptor',
        'bleak.backends.device', 
        'bleak.backends.client',
        'asyncio',
        'async_timeout',
        'asyncio.windows_events',
        
        # Might relevant depending Bleak version
        'bleak.backends.bluezdbus',
        'bleak.backends.p4android',
    ],
    hookspath=[
        'hooks'
    ],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='I Heart Clicking',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='img/heart.ico',
)
