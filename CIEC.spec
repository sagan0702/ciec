# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src\\ciec\\__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets\\images\\splash.png', 'assets\\images'),
        ('assets\\images\\ciec.ico', 'assets\\images'),
        ('assets\\docs\\manual.pdf', 'assets\\docs')
    ],
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name='CIEC',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets\\images\\ciec.ico',
    version='version_info.txt'
)
