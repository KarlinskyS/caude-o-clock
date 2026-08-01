from setuptools import setup


APP = ["ccusagebar.py"]
DATA_FILES = [("assets", ["assets/menubar-glyph.png"])]
OPTIONS = {
    "argv_emulation": False,
    "iconfile": "assets/app-icon.icns",
    "plist": {
        "CFBundleDisplayName": "Caude o'clock",
        "CFBundleName": "Caude o'clock",
        "CFBundleIdentifier": "com.karlinskys.caude-oc",
        "LSUIElement": True,
        "NSHumanReadableCopyright": "Copyright © 2026 KarlinskyS",
    },
}


setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
