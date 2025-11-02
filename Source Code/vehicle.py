import pygame
import os, sys
import math
import pandas as pd
import pygame.gfxdraw
import timeit
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
from pydub import AudioSegment
import sounddevice as sd
import numpy as np
from util import resource_path

cwd = os.getcwd()




# Torque curve data
torque_data = pd.read_csv(resource_path("TorqueRPMdata.csv")) 
rpm_torque_list = torque_data.values.tolist()


class Car: 
    def __init__(self):
        self.rpm = 600
        self.min_rpm = 600
        self.max_rpm = 6800
        self.torque = 246.7
        self.acceleration = 0
        self.speed = 0
        self.gear = 0
        self.clutch_on = False
        self.car_on = False
        self.clutch_level = 0
        self.w_level = 0
        self.s_level = 0
        self.engine_damage_level = 0
        self.engine_damaged = False
        self.engine_stalled = False
        self.gear_ratio1 = 3.625
        self.gear_ratio2 = 2.115
        self.gear_ratio3 = 1.529
        self.gear_ratio4 = 1.125
        self.gear_ratio5 = 0.848
        self.gear_ratio6 = 0.686
        self.gear_ratio_reverse = 3.758
        self.final_drive_ratio = 3.84
        self.wheel_radius = 0.2413 # meters [converted from 19 inches]
        self.vehicle_mass = 1495.9476 # kg [converted from 3298 lbs]
        self.e_damaged = False
        self.c_damaged = False

    def shift_up(self):
        if self.gear < 6: #Ensures that max gear is 6. (when gear_num = 5, gear_num would increment by 1 since shift_up() is called. Here, the final gear_num value would be 6, which is the max gear we want.)
            self.gear += 1
        return self.gear 
    
    def shift_down(self):
        if self.gear > -1:
            self.gear -= 1
        return self.gear
    
    

    def accelerate(self): 
        if self.clutch_on:
            return 0
        # Finding Torque from rpm_torque_list using a Binary Search
        start = 0
        end = len(rpm_torque_list) - 1
        torque = 0
        found = False

        rpm = round(self.rpm, -2)

        if self.clutch_on:
            return 0

    
        while not found and start <= end:
            mid = (start + end) // 2

            if rpm == rpm_torque_list[mid][0]:
                torque = rpm_torque_list[mid][1]
                found = True
            elif rpm < rpm_torque_list[mid][0]:
                end = mid - 1
            else:
                start = mid + 1

        # Calculating Acceleration
        acceleration = (self.w_level * torque * self.getGearRatio() / (self.wheel_radius * self.vehicle_mass)) 

        # Acceleration is negative if gear is set to Reverse
        if self.gear == -1:
            acceleration = (-1) * acceleration

        if self.rpm < self.max_rpm:
            return acceleration
        
        
        
        # Vehicle does not accelerate if max RPM is reached
        if self.rpm >= self.max_rpm or not found:
            return 0
    
    def speedIncrease(self, speed, acceleration):
        if self.clutch_on:
            speed = speed
        if self.gear != -1 and self.speed < (self.rpmToSpeed(6800) - 15):
            speed += abs(acceleration)
            max(0, speed)
        if self.gear == -1 and self.speed < (self.rpmToSpeed(6800) - 15):
            speed -= abs(acceleration)
        return speed

    def speedDecrease(self):
        if self.speed > 0: #include appropriate logic for R gear
            self.speed -= 0.5
        if self.speed < 0:
            self.speed += 0.5
        if self.speed == 0:
            return 0
        return self.speed
    
    def calculate_wheel_rotation_rate(self):
        return self.speed / self.wheel_radius


    def throttleRPM(self):
        if self.gear == -1:  # Reverse gear has a lower RPM limit
            self.max_rpm = 2500
        else:
            self.max_rpm = 6800  # Normal redline
        

        if self.rpm < self.max_rpm:
            # Define a base RPM increase
            base_increase = 100  

            if self.gear == 0:
                self.rpm += base_increase

            # Scale the increase based on gear (higher gears = slower increase)
            gear_factor = max(0.1, 1.1 - (self.gear/6))  # Ensures it never drops below 0.3
        

            rpm_scaling =  min(1.0, math.sin((1/6800)*(self.rpm+1500)))


            # Calculate final RPM gain
            rpm_gain = base_increase * rpm_scaling * gear_factor

            self.rpm += rpm_gain
        
        return min(self.rpm, self.max_rpm)  
   
    def getGearRatio(self):
        if self.gear == 1:
            gear_ratio = self.gear_ratio1
        elif self.gear == 2:
            gear_ratio = self.gear_ratio2
        elif self.gear == 3:
            gear_ratio = self.gear_ratio3
        elif self.gear == 4:
            gear_ratio = self.gear_ratio4
        elif self.gear == 5:
            gear_ratio = self.gear_ratio5
        elif self.gear == 6:
            gear_ratio = self.gear_ratio6
        elif self.gear == 0: 
            gear_ratio = 1
        else:
            gear_ratio = self.gear_ratio_reverse
        
        return gear_ratio
    
    def rpmToSpeed(self, rpm):
        if self.clutch_on:
            return self.speed
        gear_ratio = self.getGearRatio()
        r_speed = round((math.pi * rpm * self.wheel_radius)/(30 * gear_ratio * self.final_drive_ratio),0)

        if self.gear == -1:
            return (-1) * r_speed
        
        return r_speed
    
    def speedToRPM(self):
        gear_ratio = self.getGearRatio()
        s_rpm = round((abs(self.speed) * 30 * gear_ratio * self.final_drive_ratio)/(math.pi * self.wheel_radius),-3) 

        if s_rpm >= self.max_rpm:
            s_rpm = 6800
        if s_rpm <= 600:
            s_rpm = 600
        return s_rpm

    def drawGauge(self, surface, x, y, value, max_value, radius, phase, angle2, line_color):
        pygame.gfxdraw.aacircle(surface, x, y, radius, [255,255,255]) #Currently set the circle to draw from the top right and fill itself, remove later if needed.

        global angle
        angle = math.radians(((abs(value)/max_value) * angle2)) - phase #This is in degrees, converted to rad
        #Radius is set to 100. 100 * cos(angle) gives the base length of the triangle formed by the line.
        global end_x
        global end_y
        #angle MUST be converted to radians for the below math functions to work.
        end_x = x - int(radius * math.cos(angle)) # radius x angle in radians (show this math formula in the documentation)
        end_y = y - int(radius * math.sin(angle)) #figure out more on why its - and not + (pygame coordinate system?)

        pygame.draw.aaline(surface, line_color, (x,y), (end_x,end_y),4)
    
    def calc_engine_damage(self, rpm, w_level, prev_gear, current_gear, engine_damage):
        if current_gear is None:
            current_gear = 0
        if prev_gear is None:
            prev_gear = 0
        
       # Redlining (Max RPM & full throttle) gradually damages the engine
        if rpm >= (self.max_rpm - 200) and w_level == 1:
            engine_damage += 0.1

        # Lugging the engine - High gears (4+) at very low RPMs (<1500)
        if current_gear >= 4 and rpm <= 1500 and w_level != 0 and self.car_on:
            engine_damage += 0.1

        # Aggressive shifting (e.g., skipping multiple gears)
        if abs(current_gear - prev_gear) >= 2 and w_level != 0 and self.clutch_on: 
            engine_damage += 10

        # Ensure damage does not exceed 100
        engine_damage = min(engine_damage, 100)


        return engine_damage
    
    def engine_IsDamaged(self, engine_damage):
        # Check if the engine is fully damaged
        if engine_damage >= 100:
            self.e_damaged = True
            return self.e_damaged

    


class Shifter:
    def __init__(self, screen_width):
        # Define positions for each gear
        self.positions = {
            0: (screen_width - 275, 560),
            1: (screen_width - 375, 460),
            2: (screen_width - 375, 660),
            3: (screen_width - 275, 460),
            4: (screen_width - 275, 660),
            5: (screen_width - 175, 460),
            6: (screen_width - 175, 660),
            7: (screen_width - 475, 460),
        }
        self.x_buffer = 50  # Define buffer for x-axis
        self.y_buffer = 50  # Define buffer for y-axis
        

    def snapToPos(self, x_pos, y_pos):
        # Default to snapping to neutral if out of bounds
        closest_gear = 0
        closest_distance = float("inf")

        for gear, (x, y) in self.positions.items():
            # Check if within snapping range
            if abs(x - x_pos) <= self.x_buffer and abs(y - y_pos) <= self.y_buffer:
                # Calculate distance to determine the closest position
                distance = math.sqrt((x - x_pos) ** 2 + (y - y_pos) ** 2)  # Distance between current pos. and pos. of gear
                if distance < closest_distance:  # If calculated distance < closest distance (initially infinity)
                    closest_distance = distance  # Found new closest distance
                    closest_gear = gear  # New closest gear is the current gear in the iteration

        # Return the coordinates of the closest gear position along with the gear number
        return self.positions[closest_gear][0], self.positions[closest_gear][1], closest_gear
    
    def gearToPos(self, current_gear):
        if current_gear == -1:
            return self.positions[7][0], self.positions[7][1]

        if current_gear in self.positions:
            return self.positions[current_gear][0], self.positions[current_gear][1]
        
    def posToGear(self, x_pos, y_pos):
        for gear, (x, y) in self.positions.items():  # Unpack the tuple properly
            # Use a buffer to account for floating-point precision issues
            if abs(x - x_pos) <= self.x_buffer and abs(y - y_pos) <= self.y_buffer:
                return int(gear)
        return None  # Return None if no gear is found

    

