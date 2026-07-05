# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

project_root = os.path.abspath(SPECPATH)

hiddenimports = [
    'fitz',
    'PyMuPDF',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFile',
    'PIL.PngImagePlugin',
    'PIL.JpegImagePlugin',
    'pystray',
    'pystray._appindicator',
    'pystray._darwin',
    'pystray._gtk',
    'pystray._win32',
    'flask',
    'flask.helpers',
    'werkzeug',
    'jinja2',
    'jinja2.ext',
    'markupsafe',
    'click',
    'itsdangerous',
    'pkg_resources',
    'pkg_resources.py2_warn',
]

if sys.platform == 'win32':
    hiddenimports.extend([
        'PIL.ImageWin',
        'win32print',
        'win32ui',
        'win32con',
    ])

a = Analysis(
    [os.path.join(project_root, 'src', 'main.py')],
    pathex=[project_root],
    binaries=[],
    datas=[
        (os.path.join(project_root, 'src', 'templates'), 'src/templates'),
        (os.path.join(project_root, 'src', 'static'), 'src/static'),
    ],
    hiddenimports=hiddenimports,
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
    a.zipfiles,
    a.datas,
    [],
    name='auto-printer',
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
)

if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='AutoPrinter.app',
        icon=None,
        bundle_identifier='com.autoprinter.app',
        info_plist={
            'LSUIElement': True,
        },
    )
