# webcamp2p

A lightweight, stable peer-to-peer (P2P) dual-window video streaming application built in Python using `Tkinter`, `OpenCV`, and raw TCP sockets.

## Features
- **Dual-Stream UI:** Local and remote video feeds side-by-side using a responsive grid layout.
- **Full-Duplex Sockets:** Dedicated separate ports for inbound and outbound traffic.
- **Port Mirroring:** Instant port-swap feature for easy local loopback testing (`127.0.0.1`).
- **Clean Lifecycle Management:** Thread-safe execution with immediate hardware release on exit.

## Requirements
```
pip install opencv-python numpy pillow
```

## Build Instructions

To build the standalone executable (`.exe`) from source using PyInstaller:

```
python -m PyInstaller --onefile --noconsole webcam.p2p3.py
```
