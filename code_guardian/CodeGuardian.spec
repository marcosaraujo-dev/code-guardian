# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = [('C:\\Users\\Marcos\\Repos\\code_review\\.claude\\scripts\\code_guardian\\runner.py', 'scripts'), ('C:\\Users\\Marcos\\Repos\\code_review\\.claude\\scripts\\code_guardian\\rule_engine.py', 'scripts'), ('C:\\Users\\Marcos\\Repos\\code_review\\.claude\\scripts\\code_guardian\\vb6_rule_engine.py', 'scripts'), ('C:\\Users\\Marcos\\Repos\\code_review\\.claude\\scripts\\code_guardian\\metrics.py', 'scripts'), ('C:\\Users\\Marcos\\Repos\\code_review\\.claude\\scripts\\code_guardian\\diff_parser.py', 'scripts'), ('C:\\Users\\Marcos\\Repos\\code_review\\.claude\\scripts\\code_guardian\\ai_client.py', 'scripts'), ('C:\\Users\\Marcos\\Repos\\code_review\\.claude\\scripts\\code_guardian\\spelling_checker.py', 'scripts'), ('C:\\Users\\Marcos\\Repos\\code_review\\.claude\\scripts\\code_guardian\\config.json', 'scripts'), ('C:\\Users\\Marcos\\Repos\\code_review\\.claude\\scripts\\code_guardian\\assets', 'assets')]
datas += collect_data_files('customtkinter')


a = Analysis(
    ['C:\\Users\\Marcos\\Repos\\code_review\\.claude\\scripts\\code_guardian\\code_guardian_ui.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['customtkinter', 'darkdetect', 'PIL', 'PIL.Image', 'packaging', 'tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox'],
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
    name='CodeGuardian',
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
    icon=['C:\\Users\\Marcos\\Repos\\code_review\\.claude\\scripts\\code_guardian\\assets\\icon.ico'],
)
