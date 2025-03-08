# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['dns_bypass_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('zanzhuma.jpg', '.')],  # 打包赞助码图片
    hiddenimports=['dns.rdtypes.*', 'dns.rdtypes.IN.*'],  # dnspython需要的隐藏导入
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
    name='DNS代理服务器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 设置为False以隐藏控制台窗口
    icon='favicon.ico',  # 如果您有图标文件的话
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
) 