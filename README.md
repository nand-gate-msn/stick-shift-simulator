# Stick Shift Simulator

## Table of Contents
 [Introduction](#introduction)
 [Features](#features)
 [Installation](#installation)
 [Usage](#usage)
 [Dependencies](#dependencies)

## Introduction

The Stick Shift Simulator is a Python-based application that allows users to experience the mechanics of a manual transmission. The main script, `main.py`, handles the core functionality of the simulator.

## Features
1) Ability to view live information that updates in realtime, such as engine RPM, speed and the current gear selected.  

2) Ability to change gears by dragging and dropping an onscreen shifter to its desired 	position.  

3) Ability to set custom key binds for controls based on their preferences.  

4) Ability to view a report highlighting a count of their mistakes, such as the number of times they stalled the engine.  

5) Ability to access a simple tutorial to use the program.  

6) Ability to view realtime telemetry data relating to the car.  

7) Ability to provide a visual indication of optimal times to shift gears.  

8) Ability to detect and prevent the user from selecting gears that are 	not present, such as negative gears, or gears above 6.  

9) Ability to simulate basic engine stalling if the user releases the clutch too quickly without enough throttle input, or if the vehicle stops and the gear is not set to neutral.  

10) Ability to simulate changing acceleration depending on the current RPM.  

11) The application prevents the user from changing gears if the clutch is not pressed.  

12) The application simulates realistic RPM increase rates when the throttle is pressed. 

13) The application can produce engine audio whose frequency changes are based on the car’s RPM. 

14) The application can model engine damage for different scenarios.  


## Installation

To get started with the Stick Shift Simulator, follow these steps:

1. Ensure that Python is installed on your system (`https://www.python.org/`). 

2. Install the required dependencies by executing this command (see [Dependencies](#dependencies)):
    ```bash
    pip install r requirements.txt
    ```
3. Install the required font files
    - The required .ttf files for the "Eroded Personal Use" and "JetBrains Mono" font styles can be found under `Source Code\Fonts`.
    - Install the .ttf files onto your system.

## Usage

To run the simulator, run the `main.py` script, either by pressing the Play button in Visual Studio Code or execute the following code in a dedicated terminal (ensure that the current working directory is correct):

```bash
python main.py
```

Follow the onscreen instructions to interact with the simulator.

## Dependencies
The following dependencies must be installed to run this program.
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
Pandas
Threading
pygame
tkinter
matplotlib
```


