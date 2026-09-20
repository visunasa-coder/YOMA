# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['yoma_service_entry.py'],
    pathex=['src'],
    binaries=[],
    datas=[],
    hiddenimports=['win32api','pythoncom','pywintypes','win32event','win32serviceutil','win32service','servicemanager','win32timezone', 'yoma.office.control_server.api', 'yoma.office.control_server.voice_engine', 'yoma.office.control_server.voice_assistant', 'faster_whisper', 'piper'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='YOMA-ControlServer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    contents_directory='control_internal',
    version='release/work/yoma-version.txt',
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name='YOMA-ControlServer',
    strip=False,
    upx=True,
    upx_exclude=[],
)
