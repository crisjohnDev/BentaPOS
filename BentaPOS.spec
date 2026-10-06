from PyInstaller.utils.hooks import collect_submodules


# =========================================================
# HIDDEN IMPORTS
# =========================================================

hiddenimports = []

hiddenimports += collect_submodules("django")
hiddenimports += collect_submodules("webview")
hiddenimports += collect_submodules("rest_framework")
hiddenimports += collect_submodules("rest_framework_simplejwt")
hiddenimports += collect_submodules("corsheaders")
hiddenimports += collect_submodules("whitenoise")


# =========================================================
# ANALYSIS
# =========================================================

a = Analysis(
    ["desktop.py"],

    pathex=[
        ".",
    ],

    binaries=[],

    datas=[

        # Django templates
        (
            "templates",
            "templates"
        ),

        # Source static files
        (
            "static",
            "static"
        ),

        # Collected static files
        (
            "staticfiles",
            "staticfiles"
        ),

    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)


# =========================================================
# PYZ
# =========================================================

pyz = PYZ(
    a.pure
)


# =========================================================
# EXECUTABLE
# =========================================================

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="BentaPOS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='bentaPOS_logo.ico',
)