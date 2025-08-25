# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['run_sakura.py'],
    pathex=[],
    binaries=[],
    datas=[('sakura_assistant/Assets', 'Assets'), ('sakura_assistant/UI', 'UI'), ('sakura_assistant/Core', 'Core'), ('sakura_assistant/Utils', 'Utils')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tensorflow', 'keras', 'keras_preprocessing', 'keras-nlp'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LevosAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
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
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LevosAI',
)
