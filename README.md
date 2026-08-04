# 🚘 Stick Shift Simulator

A Python-based simulator that models the mechanics of driving a manual transmission — real-time RPM/speed telemetry, drag-and-drop gear shifting, engine stalling logic, and live audio synced to engine RPM via PortAudio.

## Table of Contents
- [Features](#features)
- [What I'd Improve With More Experience](#what-id-improve-with-more-experience)
- [Installation](#installation)
- [Usage](#usage)
- [Dependencies](#dependencies)

## Features

**Core mechanics**
- Realistic RPM increase rates based on throttle input, with changing acceleration depending on current RPM
- Engine stalling simulation — triggered by releasing the clutch too quickly without enough throttle, or stopping without shifting to neutral
- Gear-change lockout while the clutch is not pressed, and prevention of invalid gear selection (negative gears, gears above 6)
- Basic engine damage modeling for different failure scenarios

**Interface & feedback**
- Drag-and-drop onscreen shifter for gear changes
- Live telemetry: engine RPM, speed, and current gear, updating in real time
- Visual indicator for optimal shift timing
- Customizable key bindings
- Built-in tutorial
- Post-session report summarizing mistakes (e.g. stall count)

**Audio**
- Real-time engine audio with frequency that scales with RPM

*Images showcasing the GUI will be added to this README in the future.*

## What I'd Improve With More Experience

This was my first large-scale project, and revisiting it now, I'd:
- Refactor into proper OOP classes instead of function-per-screen
- Reorganize the codebase to be more modular (e.g. individual pages in a separate folder, backend services stored separately), along with better naming conventions (Source Code --> src)
- Replace global state (RPM, speed) with encapsulated class attributes
- Add delta-time-based physics for frame-rate independence
- Replace break statements with flag-based control flow

## Installation

1. Ensure Python is installed (`https://www.python.org/`).
2. Download the source code and navigate to the Stick Shift Simulator directory in your terminal.
3. Install dependencies (see [Dependencies](#dependencies)):
```bash
    pip install -r requirements.txt
```
4. Install the required fonts:
    - The `.ttf` files for "Eroded Personal Use" and "JetBrains Mono" are located in `Source Code/Fonts`.
    - Install them onto your system.

## Usage

Run `main.py` — either via your IDE's run button or from a terminal (with the correct working directory):

```bash
python main.py
```

Follow the onscreen instructions to interact with the simulator.

## Dependencies

```
os
sys
time
timeit
math
json
reportlab
pydub
sounddevice
numpy
pandas
threading
pygame
tkinter
matplotlib
```
