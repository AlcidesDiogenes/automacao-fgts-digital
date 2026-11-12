# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files
from pathlib import Path

block_cipher = None

datas = []
datas += collect_data_files('customtkinter')
datas += collect_data_files('playwright')
datas += collect_data_files('playwright_stealth')
datas += collect_data_files('pdfminer')
datas += collect_data_files('reportlab')

# Assets do aplicativo
datas.append(('assets', 'assets'))

# Modelos e configurações iniciais
if Path('config/parametros.json').exists():
    datas.append(('config/parametros.json', 'config'))
if Path('config/.env.example').exists():
    datas.append(('config/.env.example', 'config'))
# Nada da pasta data/ entra no instalador: ela guarda relatórios, planilhas, logs e perfis de navegador
# do usuário. Até a v1.0.1 o relatório de exemplo empacotado aqui era um relatório REAL (removido em
# 12/11/2026; teste em tests/test_empacotamento.py).

hiddenimports = [
    'customtkinter',
    'playwright',
    'playwright.sync_api',
    'playwright_stealth',
    'pandas',
    'openpyxl',
    'pdfplumber',
    'pdfminer',
    'pypdf',
    'reportlab',
    'rich',
    'pydantic',
    'dotenv',
    'PIL',
    'PIL._tkinter_finder',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', '_pytest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 1. Executável Principal (Interface Gráfica - sem janela preta de console)
exe_gui = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FGTS_Digital',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
)

# 2. Executável de Console / Depuração (com janela de terminal)
exe_cli = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FGTS_Digital_Console',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
)

coll = COLLECT(
    exe_gui,
    exe_cli,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='FGTS_Digital',
)
