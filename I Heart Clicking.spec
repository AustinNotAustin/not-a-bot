# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['start.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('img/*', 'img/'),
        ('font/*', 'font/'),
        ('ui_design_variables.py', '.'),
        ('bluetooth_controller.py', '.'),
        ('bluetooth_device_list.py', '.')
    ],
    hiddenimports=[
        'PIL._tkinter_finder', 
        'keyboard', 
        'pyautogui',
        'bleak',
        'bleak.backends.dotnet',
        'bleak.backends.winrt',
        'asyncio',
        'async_timeout'
    ],
    hookspath=[],
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
