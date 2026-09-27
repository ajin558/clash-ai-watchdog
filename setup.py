# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name="clash-ai-watchdog",
    version="2.0.0",
    packages=find_packages(),
    py_modules=["main"],
    install_requires=[],
    extras_require={
        "tray": ["pystray>=0.19.5", "pillow>=9.0.0"],
        "all": ["pystray>=0.19.5", "pillow>=9.0.0", "rich>=13.0.0"],
    },
    entry_points={
        "console_scripts": [
            "caw = clash_watchdog.cli:main",
            "caw-tray = clash_watchdog.tray:main",
        ],
    },
)
