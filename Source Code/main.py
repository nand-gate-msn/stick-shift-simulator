import sys, time, math, os, json, timeit, platform

import pygame
import pygame.gfxdraw
import pygame.mixer

import tkinter as tk
from tkinter import Tk
from tkinter.filedialog import asksaveasfilename
from tkinter import messagebox

import threading

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from util import load_save, reset_keys, resource_path
from vehicle import Car, Shifter
from buttons import DefaultButton, SubButton
from controls import Controls_Handler


from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.backends.backend_agg as agg
import matplotlib.pyplot as plt

# AUDIO
from pydub import AudioSegment
import sounddevice as sd
import numpy as np

#----------------------------- INITIALIZING IMPORTANT VARIABLES AND VARIABLES ----------------------------#
pygame.init()

#---------------- SCREEN AND SIMULATION WINDOW ----------------#
screen = pygame.display.init()
flags = pygame.RESIZABLE
screen = pygame.display.set_mode((1280,720), flags)
SCREEN_WIDTH, SCREEN_HEIGHT = screen.get_size()   
overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

main_icon_path = resource_path("Images/SSS_icon2.png") #os.path.join("Source Code", "Images", "SSS_icon2.png")
main_icon = pygame.image.load(main_icon_path).convert_alpha()
pygame.display.set_icon(main_icon)

#------------------- BACKGROUND ------------------#
background_path = resource_path("Images/background_img.png") #os.path.join("Source Code", "Images", "background_img.png")
background = pygame.image.load(background_path).convert_alpha()

button_surface1 = pygame.image.load(resource_path("Images/button_surface.png")).convert_alpha() # pygame.image.load(os.path.join("Source Code", "Images", "button_surface.png")).convert_alpha()

#---------------- CONTROLS ----------------#
default_control_set = True

global ws_option1, ws_option2, clutch_option1, clutch_option2, clutch_option3
ws_option1 = True # W and S
ws_option2 = False # up and down


clutch_option1 = True # shift for clutch
clutch_option2 = False # ctrl for clutch
clutch_option3 = False # tab for clutch

global  old_gear, new_gear
new_gear = 0

global old_rpm
old_rpm = 600

#---------------- FONT STYLES ----------------#
default_font = pygame.font.SysFont(None, 24) 
small_font = pygame.font.SysFont(None, 21)
screen_text_font = pygame.font.SysFont("Verdana", 14)
option_font = pygame.font.SysFont("JETBRAINS MONO", 30) 

if platform.system() == 'Windows': # Adjusts font name accordingly based on operating system
    title_font = pygame.font.SysFont("ERODED PERSONAL USE Regular", 130) 
if platform.system() == 'Darwin':
    title_font = pygame.font.SysFont("ERODED PERSONAL USE", 130)


#---------------- ACTIONS DICTIONARY ----------------#
actions = {"ENGINE": False, "THROTTLE": False, "BRAKE": False, 
                "CLUTCH": False, "SHIFT-UP": False, "SHIFT-DOWN": False,  
                "NAV-UP": False, "NAV-DOWN": False, "NAV-LEFT": False, 
                "NAV-RIGHT": False, "EDIT": False,}


#---------------- VARIABLES FOR THE PDF REPORT ----------------#
global engine_stall_count, excess_rev_count, sum_rpm, sum_rpm_count, elapsed_time, elapsed_p, eng_damage
engine_stall_count = 0
eng_damage = 0
excess_rev_count = 0
sum_rpm = 0
sum_rpm_count = 0
elapsed_time = 0
elapsed_p = 0



#----------------------------- INITIALIZING TELEMETRY WINDOW VARIABLES AND CONSTANTS ----------------------------#
global t_click # Keeps track of number of times the TELEMETRY button is pressed
t_click = 0

global rpm_plot_display, speed_plot_display, gear_plot_display
rpm_plot_display = True
speed_plot_display = False
gear_plot_display = False




# Loading the current savefile
save = load_save()

#----------------------------- INITIALIZING VOLUME SLIDER ----------------------------#
class Slider:
    def __init__(self, pos, size, initial_val, min_val, max_val):
        self.pos = pos
        self.size = size

        self.slider_left_pos = self.pos[0] - (size[0]//2)
        self.slider_right_pos = self.pos[0] + (size[0]//2) 
        self.slider_top_pos = self.pos[1] - (size[1]//2)

        self.min = min_val
        self.max = max_val
        self.initial_val = (self.slider_right_pos-self.slider_left_pos)*initial_val

        self.container_rect = pygame.Rect(self.slider_left_pos, self.slider_top_pos, self.size[0], self.size[1])
        self.button_rect = pygame.Rect(self.slider_left_pos + self.initial_val - 5, self.slider_top_pos, 50, self.size[1])

        

    def render(self, screen):
        pygame.draw.rect(screen, (217, 217, 217), self.container_rect)
        pygame.draw.rect(screen, (125, 217, 86), self.button_rect)

    def move_slider(self, mouse_pos):
        self.button_rect.centerx = mouse_pos()[0]
    
    def get_value(self): 
        val_range = self.slider_right_pos - self.slider_left_pos - 1
        button_val = self.button_rect.centerx - self.slider_left_pos

        return round((button_val/val_range * (self.max - self.min) + self.min), 1) #finds range, percentage across slider, + min offset


#----------------------------- ENGINE SOUND ----------------------------#
class EngineSound:
    def __init__(self):
        pygame.mixer.init()
        self.engine_start = pygame.mixer.Sound(resource_path("Sound Files/engine_start.wav")) # pygame.mixer.Sound(os.path.join("Source Code", "Sound Files", "engine_start.wav"))
        
        # Load audio files but don't convert to AudioSegment yet
        self.engine_idle_path = resource_path("Sound Files/engine_idle.wav") #os.path.join("Source Code", "Sound Files", "engine_idle.wav")
        self.engine_up_path = resource_path("Sound Files/engine_up.wav") #os.path.join("Source Code", "Sound Files", "engine_up.wav")
        self.engine_down_path = resource_path("Sound Files/engine_down.wav") #os.path.join("Source Code", "Sound Files", "engine_down.wav")

        self.volume = 0.5
        self.up_duration = 4081
        self.down_duration = 3.120

        self.min_rpm = 600
        self.max_rpm = 6800
        self.rpm_range = 6200

        self.up_ms_per_rpm = 0.658225
        self.down_ms_per_rpm = 0.5032258

        self.stream = None
        self.is_playing = False
        self.current_samples = None
        self.target_rpm = self.min_rpm

        # Initialize stream with error handling
        try:
            self.stream = sd.OutputStream(
                channels=1,
                samplerate=44100,  # Standard sample rate
                dtype=np.float32,
                blocksize=1024,
                latency='low',
                callback=self._audio_callback
            )
            self.stream.start()
        except Exception as e:
            print(f"Failed to initialize audio stream: {e}")
            self.stream = None

    def _audio_callback(self, outdata, frames, time, status):
        try:
            if self.is_playing and self.current_samples is not None:
                if len(self.current_samples) >= frames:
                    outdata[:] = self.current_samples[:frames].reshape(-1, 1)
                    self.current_samples = self.current_samples[frames:]
                else:
                    # Pad with zeros if we run out of samples
                    outdata[:frames] = np.pad(self.current_samples, 
                                            (0, frames - len(self.current_samples)),
                                            'constant').reshape(-1, 1)
                    self.current_samples = None
            else:
                outdata.fill(0)
        except Exception as e:
            print(f"Audio callback error: {e}")
            outdata.fill(0)

    def update_rpm(self, prev_rpm, rpm):
        if not self.is_playing or self.stream is None:
            return

        try:
            if prev_rpm < rpm:  # RPM is increasing
                audio_file = AudioSegment.from_wav(self.engine_up_path)
                position = int((rpm - self.min_rpm) * self.up_ms_per_rpm)
            else:  # RPM is decreasing
                audio_file = AudioSegment.from_wav(self.engine_down_path)
                position = int((prev_rpm - self.min_rpm) * self.down_ms_per_rpm)

            # Safely get audio segment
            start_pos = max(0, position - 500)
            end_pos = min(len(audio_file), position + 500)
            segment = audio_file[start_pos:end_pos]

            # Convert to samples safely
            samples = np.array(segment.get_array_of_samples(), dtype=np.float32)
            samples = samples * self.volume / np.iinfo(np.int16).max
            self.current_samples = samples

        except Exception as e:
            print(f"Error updating RPM sound: {e}")

    def play_start_sound(self):
        pygame.mixer.stop()
        self.engine_start.play().set_volume(self.volume)

    def play_idle_sound(self):
        if not self.is_playing or self.target_rpm <= 600:
            try:
                audio_file = AudioSegment.from_wav(self.engine_idle_path)
                samples = np.array(audio_file.get_array_of_samples(), dtype=np.float32)
                self.current_samples = samples * self.volume / np.iinfo(np.int16).max
                self.is_playing = True
            except Exception as e:
                print(f"Error playing idle sound: {e}")

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, volume))
        if self.current_samples is not None:
            self.current_samples *= self.volume

    def play(self):
        self.is_playing = True

    def stop(self):
        self.is_playing = False
        self.current_samples = None
        pygame.mixer.stop()

    def __del__(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()

#---------------- GLOBAL VARIABLES FOR ENGINE_SOUND ----------------#
global engine_sound
engine_sound = EngineSound()
global engine_volume
engine_volume = engine_sound.volume

#----------------------------- CONTROLLING ENGINE AUDIO BASED ON RPM ----------------------------#
def handle_throttle():
    global car, engine_sound, default_control_set, keybinds, paused
    global custom_throttle, custom_clutch, custom_shift_up, custom_shift_down, custom_brake
    global old_rpm, delta_time

    keystate = pygame.key.get_pressed()
    
    # Stop engine sounds if in a menu or engine is damaged
    if paused or car.engine_damaged:
        if engine_sound:
            engine_sound.stop()
        return
    
    if (((default_control_set and ((keystate[pygame.K_w] and ws_option1) or (keystate[pygame.K_UP] and ws_option2))) or (not default_control_set and keystate[custom_throttle]))) and car.car_on:
        if engine_sound:
            engine_sound.play()
            engine_sound.update_rpm(old_rpm, car.rpm)
    elif engine_sound and car.car_on:
        engine_sound.update_rpm(old_rpm, car.rpm)
    elif not car.car_on:
        engine_sound.stop()
    elif paused or car.engine_damaged:
        
        engine_sound.stop()

def display_message(title, message):
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    messagebox.showinfo(title, message)
    root.destroy()  # Close the root window after clicking OK

    # Force focus back to the Pygame window
    if os.name == "nt":  # Windows
        import ctypes
        ctypes.windll.user32.SetForegroundWindow(pygame.display.get_wm_info()["window"])
    elif os.name == "posix":  # macOS or Linux
        os.system(f"wmctrl -a Stick Shift Simulator")  # Use the window title to focus


#----------------------------- TELEMETRY WINDOW ----------------------------#
def telemetry_screen(car):
    global t_click
    root = tk.Tk()
    root.title("Stick Shift Simulator - Live Telemetry")
    root.geometry("300x400")
    root.attributes('-topmost', True) 
    
    # Initialize data lists
    global rpm_data, speed_data, gear_data
    data_points = 100
    rpm_data = [0] * data_points
    speed_data = [0] * data_points
    gear_data = [0] * data_points
    
    times = list(range(data_points))
    
    # Create main figure
    fig = Figure(figsize=(8, 6), dpi=100)
    fig.patch.set_facecolor('#2E2E2E')
    
    # Create subplots for rpm, speed, and gear data
    rpm_plot = fig.add_subplot(311) # 3 rows, 1 column, 1st plot
    speed_plot = fig.add_subplot(312) # 3 rows, 1 column, 2nd plot
    gear_plot = fig.add_subplot(313) # 3 rows, 1 column, 3rd plot
    
    # Color-code each subplot
    for plot in [rpm_plot, speed_plot, gear_plot]:
        plot.set_facecolor('#1E1E1E')
        plot.grid(True, color='#444444')
        plot.tick_params(colors='white', labelsize=7)
        plot.set_xlim(0, data_points)

        
    
    # Create and define colors for lines (for each subplot)
    rpm_line, = rpm_plot.plot(times, rpm_data, 'g-', label='RPM')
    speed_line, = speed_plot.plot(times, speed_data, 'b-', label='Speed')
    gear_line, = gear_plot.plot(times, gear_data, 'r-', label='Gear')
    
    # Set labels and limits (for each subplot)
    rpm_plot.set_ylim(0, 7000)
    rpm_plot.set_ylabel('RPM', color='white')
    rpm_plot.legend()
    
    speed_plot.set_ylim(0, 220)
    speed_plot.set_ylabel('Speed (km/h)', color='white')
    speed_plot.legend()
    
    gear_plot.set_ylim(-1, 6)
    gear_plot.set_ylabel('Gear', color='white')
    gear_plot.legend()
    
    fig.tight_layout()
    
    # Create canvas for embedding
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def update():
        global rpm_data, speed_data, gear_data
        # Slice list to update data
        rpm_data = rpm_data[1:] + [car.rpm]

        speed_data = speed_data[1:] + [car.speed * 3.6]

        gear_data = gear_data[1:] + [car.gear]
                
        # Update graph lines based on new data
        rpm_line.set_ydata(rpm_data)
        speed_line.set_ydata(speed_data)
        gear_line.set_ydata(gear_data)
        
        # Redraw the main embedded canvas
        canvas.draw()
        
        # Plot updates every 30 frames
        root.after(30, update) 
    
    def on_close(): # resets the t_click variable on closing
        global t_click
        t_click = 0
        root.destroy()

    # Start updates
    update()
    
    root.protocol("WM_DELETE_WINDOW", on_close)
    # Run window
    root.mainloop()


#----------------------------- CREATING THE CUSTOM KEYBINDS MENU ----------------------------#
def custom_keybinds_menu():
    global default_control_set
    
    pygame.init()
    DISPLAY_W, DISPLAY_H = pygame.display.get_window_size() 
    window = pygame.display.set_mode((DISPLAY_W, DISPLAY_H), flags)
    canvas = pygame.Surface((DISPLAY_W, DISPLAY_H))
    
    control_handler = Controls_Handler(save, DISPLAY_W * 2, DISPLAY_H * 2)
    

    
    running = True

    backbutton_surface = pygame.image.load(resource_path("Images/buttonv2.png")).convert_alpha()
    backbutton_surface = pygame.transform.scale(backbutton_surface, (400, 125))

    backbutton = DefaultButton(backbutton_surface, 0, 0, "BACK TO MAIN MENU", "black", window)

    while running:
        # Center the backbutton based on the actual window size
        backbutton.centerOnScreen(DISPLAY_W * 2, DISPLAY_H * 2, 100, 100)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    fade(window, main_menu)
                if event.key == control_handler.controls['ENGINE']:
                    actions['ENGINE'] = True
                    default_control_set = False
                if event.key == control_handler.controls['THROTTLE']:
                    actions['THROTTLE'] = True
                    default_control_set = False
                if event.key == control_handler.controls['BRAKE']:
                    actions['BRAKE'] = True
                    default_control_set = False
                if event.key == control_handler.controls['CLUTCH']:
                    actions['CLUTCH'] = True
                    default_control_set = False
                if event.key == control_handler.controls['SHIFT-UP']:
                    actions['SHIFT-UP'] = True
                    default_control_set = False
                if event.key == control_handler.controls['SHIFT-DOWN']:
                    actions['SHIFT-DOWN'] = True
                    default_control_set = False
                if event.key == control_handler.controls['EDIT']:
                    actions['EDIT'] = True
                    default_control_set = False
                if event.key == control_handler.controls['NAV-UP']:
                    actions['NAV-UP'] = True
                    default_control_set = False
                if event.key == control_handler.controls['NAV-DOWN']:
                    actions['NAV-DOWN'] = True
                    default_control_set = False
                if event.key == control_handler.controls['NAV-LEFT']:
                    actions['NAV-LEFT'] = True
                    default_control_set = False
                if event.key == control_handler.controls['NAV-RIGHT']:
                    actions['NAV-RIGHT'] = True
                    default_control_set = False

            if event.type == pygame.KEYUP:
                if event.key == control_handler.controls['ENGINE']:
                    actions['ENGINE'] = False
                    default_control_set = False
                if event.key == control_handler.controls['THROTTLE']:
                    actions['THROTTLE'] = False
                    default_control_set = False
                if event.key == control_handler.controls['BRAKE']:
                    actions['BRAKE'] = False
                    default_control_set = False
                if event.key == control_handler.controls['CLUTCH']:
                    actions['CLUTCH'] = False
                    default_control_set = False
                if event.key == control_handler.controls['SHIFT-UP']:
                    actions['SHIFT-UP'] = False
                    default_control_set = False
                if event.key == control_handler.controls['SHIFT-DOWN']:
                    actions['SHIFT-DOWN'] = False
                    default_control_set = False
                if event.key == control_handler.controls['EDIT']:
                    actions['EDIT'] = False
                    default_control_set = False
                if event.key == control_handler.controls['NAV-UP']:
                    actions['NAV-UP'] = False
                    default_control_set = False
                if event.key == control_handler.controls['NAV-DOWN']:
                    actions['NAV-DOWN'] = False
                    default_control_set = False
                if event.key == control_handler.controls['NAV-LEFT']:
                    actions['NAV-LEFT'] = False
                    default_control_set = False
                if event.key == control_handler.controls['NAV-RIGHT']:
                    actions['NAV-RIGHT'] = False
                    default_control_set = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                if backbutton.checkForInput(pygame.mouse.get_pos()):
                    fade(window, main_menu)

        for button in [backbutton]:
            button.update()
            button.changeColor(pygame.mouse.get_pos())

        control_handler.update(actions)
        # Clear the canvas
        canvas.fill((59, 59, 59))

        # Blit the background onto the canvas
        canvas.blit(pygame.transform.scale(background, (DISPLAY_W, DISPLAY_H)), (0, 0))

        control_handler.render(canvas)
        window.blit(pygame.transform.scale(canvas, (DISPLAY_W * 2, DISPLAY_H * 2)), (0, 0))
        pygame.display.update()
        reset_keys(actions)
    pygame.quit()

#----------------------------- CREATING THE MAIN SIMULATION WINDOW ----------------------------#
def play():

    global default_control_set
    global sum_rpm, sum_rpm_count, elapsed_time, engine_stall_count, excess_rev_count, elapsed_p, eng_damage
    global t_click 
    global old_rpm
    global engine_volume
    

    global engine_sound, paused
    
    #----------------------------- INITIALIZING IMPORTANT VARIABLES AND CONSTANTS ----------------------------#
    run = True
    paused = False

    SCREEN_WIDTH, SCREEN_HEIGHT = screen.get_size()
    pygame.display.set_caption("Simulation Window")

    last_w_press = 0 # These two variables track the last itme each key was pressed
    last_s_press = 0

    time_interval_W = 0.005 # Time interval between when the respective functions for W and S keys are triggered
    time_interval_S = 0.01

    #----------------------------- INITIALIZING UI ELEMENTS ----------------------------#
    car_text = ""
    shifter_img_path = resource_path("Images/Shifter.png")#os.path.join("Source Code", "Images", "Shifter.png")
    shifter_img = pygame.image.load(shifter_img_path).convert_alpha()
    
    shifter = pygame.Rect(SCREEN_WIDTH - 275, 560, 50, 50) # Neutral
    shifter_clicked = False

    


    # Current Selected Gear
    gear_text = "CURRENT GEAR"
    gear_text_surface = screen_text_font.render(gear_text, True, "white")

    speed_text = "CURRENT SPEED"
    speed_text_surface = screen_text_font.render(speed_text, True, "white")

    rpm_text = "CURRENT RPM"
    rpm_text_surface = screen_text_font.render(rpm_text, True, "white")







    clock = pygame.time.Clock()

    #----------------------------- INITIALIZING VEHICLE VARIABLES AND CONSTANTS ----------------------------#
    increment_speed = 2.0 # PARAMETER that can be edited as needed to increase/decrease the speed of control intensity increase
    global delta_time
    delta_time = 0
    global car
    car = Car()

    engine_sound = EngineSound()
    engine_sound.set_volume(engine_volume)



    #----------------------------- INITIALIZING CUSTOM USER CONTROLS ----------------------------#
    global custom_throttle, custom_clutch, custom_shift_up, custom_shift_down, custom_brake

    # Reading the save.json file for the custom keybinds
    with open("save.json", 'r') as file:
        controls_data = json.load(file)

    # Extract the current profile
    current_profile = str(controls_data["current_profile"])  # Convert to string for consistency
    keybinds = controls_data["controls"][current_profile]  # Get the keybinds for the current profile

    custom_clutch = keybinds['CLUTCH']
    custom_throttle = keybinds['THROTTLE']
    custom_brake = keybinds['BRAKE']
    custom_shift_up = keybinds['SHIFT-UP']
    custom_shift_down = keybinds['SHIFT-DOWN']

    

    
    #----------------------------- DEFINING BUTTONS ----------------------------#
    # Create both buttons together
    tutorial_button_surface = button_surface1
    tutorial_button_surface = pygame.transform.scale(tutorial_button_surface, (250, 85))
    tutorial_button = DefaultButton(tutorial_button_surface, 0, 0, "(?) HELP (?)", "white", screen)

    telemetry_button_surface = button_surface1
    telemetry_button_surface = pygame.transform.scale(telemetry_button_surface, (250, 85))  # Made same size as tutorial button
    telemetry_button = DefaultButton(telemetry_button_surface, 0, 0, "TELEMETRY", "white", screen)
    
    # ---------- MISC -------------- #
    telemetry_window = None
    show_telemetry = False
    message_displayed = False 
    
    start_time = timeit.default_timer() # must be defined outside the game loop, or its gonna be reset with each frame


    global time_above_6700
    time_above_6700 = 0
    start_rev = None

    
    while run:
        pygame.display.set_caption("Stick Shift Simulator - Simulation Window")
        old_gear = car.gear

        eng_damage = car.engine_damage_level
        SCREEN_WIDTH, SCREEN_HEIGHT = screen.get_size()   
        tutorial_button.centerOnScreen(SCREEN_WIDTH, SCREEN_HEIGHT, (SCREEN_WIDTH / 2.56), -(SCREEN_HEIGHT / 2.3))
        telemetry_button.centerOnScreen(SCREEN_WIDTH, SCREEN_HEIGHT, (SCREEN_WIDTH / 2.56), -(SCREEN_HEIGHT / 2.3) + 100)  # 100 pixels below tutorial button

        gear_shifter = Shifter(SCREEN_WIDTH)


        screen.fill((14, 14, 23))
        speedometer_path = resource_path("Images/speedometer.png") #os.path.join("Source Code", "Images", "speedometer.png")
        rpmmeter_path = resource_path("Images/RPM_Meter.png") #os.path.join("Source Code", "Images", "RPM_Meter.png")
        shifter_background_path = resource_path("Images/shifter_background.png") #os.path.join("Source Code", "Images", "shifter_background.png")
        

        #----- RECT INITIALIZATION (for on screen UI) ----#
        # Standard parameters of rect
        RECT_WIDTH, RECT_HEIGHT = 200, 75
        RECT_WIDTH2, RECT_HEIGHT2 = 100, 75

        rect_bg = button_surface1
        rect_bg = pygame.transform.smoothscale(rect_bg, (RECT_WIDTH, RECT_HEIGHT))
        rect_bg2 = pygame.transform.smoothscale(rect_bg, (RECT_WIDTH2, RECT_HEIGHT2))

        # Gear text rectangle
        OFFSET_XGEAR, OFFSET_YGEAR = -50, 200
        OFFSET_XGEAR2, OFFSET_YGEAR2 = 100, 200

        OFFSET_XSPEED, OFFSET_YSPEED = -50, 250
        OFFSET_XSPEED2, OFFSET_YSPEED2 = 100, 250

        OFFSET_XRPM, OFFSET_YRPM = -50, 300
        OFFSET_XRPM2, OFFSET_YRPM2 = 100, 300

        rect_xgear = (SCREEN_WIDTH - RECT_WIDTH) // 2 + OFFSET_XGEAR
        rect_ygear = (SCREEN_HEIGHT - RECT_HEIGHT) // 2 + OFFSET_YGEAR
        rect_xgear2 = (SCREEN_WIDTH - RECT_WIDTH2) // 2 + OFFSET_XGEAR2
        rect_ygear2 = (SCREEN_HEIGHT - RECT_HEIGHT2) // 2 + OFFSET_YGEAR2

        rect_xspeed = (SCREEN_WIDTH - RECT_WIDTH) // 2 + OFFSET_XSPEED
        rect_yspeed = (SCREEN_HEIGHT - RECT_HEIGHT) // 2 + OFFSET_YSPEED
        rect_xspeed2 = (SCREEN_WIDTH - RECT_WIDTH2) // 2 + OFFSET_XSPEED2
        rect_yspeed2 = (SCREEN_HEIGHT - RECT_HEIGHT2) // 2 + OFFSET_YSPEED2

        rect_xrpm = (SCREEN_WIDTH - RECT_WIDTH) // 2 + OFFSET_XRPM
        rect_yrpm = (SCREEN_HEIGHT - RECT_HEIGHT) // 2 + OFFSET_YRPM
        rect_xrpm2 = (SCREEN_WIDTH - RECT_WIDTH2) // 2 + OFFSET_XRPM2
        rect_yrpm2 = (SCREEN_HEIGHT - RECT_HEIGHT2) // 2 + OFFSET_YRPM2


        gear_rect = pygame.Rect(rect_xgear, rect_ygear, RECT_WIDTH, RECT_HEIGHT)
        gear_text_rect = gear_text_surface.get_rect(center=gear_rect.center)

        speed_rect = pygame.Rect(rect_xspeed, rect_yspeed, RECT_WIDTH, RECT_HEIGHT)
        speed_text_rect = speed_text_surface.get_rect(center=speed_rect.center)

        rpm_rect = pygame.Rect(rect_xrpm, rect_yrpm, RECT_WIDTH, RECT_HEIGHT)
        rpm_text_rect = rpm_text_surface.get_rect(center=rpm_rect.center)

        current_time = time.time()

        
        speedometer_img = pygame.image.load(speedometer_path).convert_alpha()
        rpmmeter_img = pygame.image.load(rpmmeter_path).convert_alpha()
        shifter_background_img = pygame.image.load(shifter_background_path).convert_alpha()


        screen.blit(pygame.transform.smoothscale(speedometer_img, (750,575)), (SCREEN_WIDTH // 2 - 172, SCREEN_HEIGHT // 2 - 370))
        screen.blit(pygame.transform.smoothscale(rpmmeter_img, (480,369)), (SCREEN_WIDTH // 2 - 439, SCREEN_HEIGHT // 2 - 240))

        # Align the shifter background with the gear rectangles
        shifter_x = SCREEN_WIDTH - 524  # Adjust based on rectangle positions
        shifter_y = 455  # Adjust if needed to align properly

        screen.blit(pygame.transform.smoothscale(shifter_background_img, (475, 260)), (shifter_x, shifter_y))


        keystate = pygame.key.get_pressed()

        if default_control_set:
            # Adjusts the clutch key for each clutch option
            if clutch_option1:
                car.clutch_on = keystate[pygame.K_LSHIFT]  
            
            elif clutch_option2:
                car.clutch_on = keystate[pygame.K_LCTRL] 
            
            elif clutch_option3:
                car.clutch_on = keystate[pygame.K_TAB]
        else:
            car.clutch_on = keystate[custom_clutch]
        

        # Time handling for smooth clutch operation
        delta_time = clock.get_time() / 1000.0  # Time since last frame in seconds

        # Adjust clutch value
        if not paused:
            if car.clutch_on:
                car.clutch_level = min(1.0, car.clutch_level + increment_speed * delta_time)  # Increase to 1.0
            
            else:
                car.clutch_level = max(0.0, car.clutch_level - increment_speed * delta_time)  # Decrease to 0.0


        
        
        # Drawing the clutch (outer rectangle)
        pygame.draw.rect(screen,"white",pygame.Rect(55, 500, 40, 200)) # Rect(x coord, y coord, x width, y width)

        # Filling outer rectangle with current clutch intensity
        pygame.draw.rect(screen,"black",pygame.Rect(55, 500, 40,(200- (car.clutch_level)*200)))
        pygame.draw.rect(screen,"white",pygame.Rect(55, 500, 40,(200- (car.clutch_level)*200)),1)



        screen.blit(rect_bg, (rect_xgear, rect_ygear))
        screen.blit(gear_text_surface, gear_text_rect)

        screen.blit(rect_bg, (rect_xspeed, rect_yspeed))
        screen.blit(speed_text_surface, speed_text_rect)

        screen.blit(rect_bg, (rect_xrpm, rect_yrpm))
        screen.blit(rpm_text_surface, rpm_text_rect)

        if car.gear == 0:
            gear_text2 = "N"
        elif car.gear == -1:
            gear_text2 = "R"
        else:
            gear_text2 = str(car.gear)
        gear_text_surface2 = screen_text_font.render(gear_text2, True, "white")

        speed_text2 = str(round(3.6 * car.speed, 0)) + "km/h"
        speed_text_surface2 = screen_text_font.render(speed_text2, True, "white")

        if car.car_on:
            rpm_text2 = str(round(car.rpm, 0))
        else:
            rpm_text2 = str(0)
        rpm_text_surface2 = screen_text_font.render(rpm_text2, True, "white")

        gear_rect2 = pygame.Rect(rect_xgear2, rect_ygear2, RECT_WIDTH2, RECT_HEIGHT2)
        gear_text_rect2 = gear_text_surface2.get_rect(center=gear_rect2.center)

        speed_rect2 = pygame.Rect(rect_xspeed2, rect_yspeed2, RECT_WIDTH2, RECT_HEIGHT2)
        speed_text_rect2 = speed_text_surface2.get_rect(center=speed_rect2.center)

        rpm_rect2 = pygame.Rect(rect_xrpm2, rect_yrpm2, RECT_WIDTH2, RECT_HEIGHT2)
        rpm_text_rect2 = rpm_text_surface2.get_rect(center=rpm_rect2.center)
       
        screen.blit(rect_bg2, (rect_xgear2, rect_ygear2))
        screen.blit(gear_text_surface2, gear_text_rect2)

        screen.blit(rect_bg2, (rect_xspeed2, rect_yspeed2))
        screen.blit(speed_text_surface2, speed_text_rect2)

        screen.blit(rect_bg2, (rect_xrpm2, rect_yrpm2))
        screen.blit(rpm_text_surface2, rpm_text_rect2)
        
        shiftx, shifty = shifter.x, shifter.y
        
        pygame.draw.rect(screen, "white", [SCREEN_WIDTH - 275, 560, 50, 50])

        



        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Left mouse button only
                    if shifter.collidepoint(event.pos): # Checks if mouse pointer coordinates (event.pos) is within the "rect" of the shifter
                        shifter_clicked = True 
                        
                        old_gear = gear_shifter.posToGear(event.pos[0], event.pos[1]) 
                        print(f"    OLD GEAR: {old_gear}")
                        # Calculate offset between mouse position and shifter position
                        offset_x = shifter.x - event.pos[0]
                        offset_y = shifter.y - event.pos[1]
                        
                    if tutorial_button.checkForInput(pygame.mouse.get_pos()):
                        fade(screen, tutorial_screen)

                    if telemetry_button.checkForInput(pygame.mouse.get_pos()): 
                            t_click += 1
                            
                            print(f"t_click: {t_click}")
                            if t_click >= 2:
                                break 
                            try:
                                print("Opening telemetry window...")
                                
                                # Create telemetry window in a separate thread to not block the main game
                                telemetry_thread = threading.Thread(target=telemetry_screen, args=(car,)) 
                                telemetry_thread.daemon = True  # Make thread close with main program
                                telemetry_thread.start()
                            
                            except Exception as e:
                                print(f"Telemetry window error: {e}")
            if event.type == pygame.MOUSEMOTION:
                if shifter_clicked:
                    # Set the shifter's position based on the mouse position and offset
                    shifter.x = event.pos[0] + offset_x
                    shifter.y = event.pos[1] + offset_y
                    
                    shiftx, shifty = shifter.x, shifter.y
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    shifter_clicked = False
                    shifter.x, shifter.y, shifter_gear = gear_shifter.snapToPos(shiftx, shifty)
                    print(shifter.x, shifter.y, shifter_gear)

                    if shifter_gear == 7 and (car.clutch_on):
                        car.gear = -1
                    
                    elif shifter_gear != 7 and (car.clutch_on):
                        car.gear = shifter_gear
                    
                    car.rpm = car.speedToRPM() 

                    print(f"    New gear {car.gear}")
                    print("...")
                    # Calculate engine damage
                    car.engine_damage_level = car.calc_engine_damage(
                        car.rpm, car.w_level, old_gear, shifter_gear, car.engine_damage_level
                    )
                    car.engine_damaged = car.engine_IsDamaged(car.engine_damage_level)    
            if event.type == pygame.QUIT:
                end_time = timeit.default_timer()
                elapsed_time = (end_time - start_time) - elapsed_p
                fade(screen, quit_screen)



    
            if event.type == pygame.KEYDOWN:
                if ((default_control_set and event.key == pygame.K_f) or (not default_control_set and event.key == keybinds["ENGINE"])) and not paused:
                    if car.car_on:
                        car.car_on = False
                    
                    elif car.car_on == False and car.gear != 0 and not (car.clutch_on) and car.speed == 0 and car.clutch_level < 0.3 and car.w_level < 0.1 and not paused: #Doesn't turn on car if gear is not 0
                        car.car_on = False

                        car.engine_stalled = True
                        engine_stall_count += 1

                    else: 
                        engine_sound.play_start_sound()
                         # used pygame mixer, as it only had to be played once.
                        car.car_on = True

                if event.key == pygame.K_ESCAPE:
                    paused = not paused
                
                if (((default_control_set and event.key == pygame.K_e) or (not default_control_set and event.key == keybinds["SHIFT-UP"])) and (car.clutch_on)) and (not paused): #function runs only if clutch is being pressed, and E just got pressed. Same goes for the Q stuff below.
                    old_gear = car.gear

                    car.gear = car.shift_up()
                    
                    # Calculate engine damage
                    car.engine_damage_level = car.calc_engine_damage(
                        car.rpm, car.w_level, old_gear, car.gear, car.engine_damage_level
                    )
                    car.engine_damaged = car.engine_IsDamaged(car.engine_damage_level)

                    car.rpm = car.speedToRPM()
                    shifter.x, shifter.y = gear_shifter.gearToPos(car.gear)
                    

                if (((default_control_set and event.key == pygame.K_q) or (not default_control_set and event.key == keybinds["SHIFT-DOWN"])) and (car.clutch_on)) and (not paused):
                    old_gear = car.gear
                    car.gear = car.shift_down()
                    


                    # Calculate engine damage
                    car.engine_damage_level = car.calc_engine_damage(
                        car.rpm, car.w_level, old_gear, car.gear, car.engine_damage_level
                    )
                    car.engine_damaged = car.engine_IsDamaged(car.engine_damage_level)

                    car.rpm = car.speedToRPM()
                    print(car.gear)

                    shifter.x, shifter.y = gear_shifter.gearToPos(car.gear)

        
        
        if not paused:
            if (((default_control_set and ((keystate[pygame.K_w] and ws_option1) or (keystate[pygame.K_UP] and ws_option2))) or (not default_control_set and keystate[custom_throttle])) and (current_time - last_w_press >= time_interval_W)) and car.car_on: 
                old_rpm = car.rpm
                car.rpm = car.throttleRPM()
                
                sum_rpm += car.rpm
                sum_rpm_count += 1

                if car.gear != 0 and car.car_on:
                    initial_speed = car.rpmToSpeed(car.rpm)
                    acceleration = car.accelerate()
                    car.speed = round(car.speedIncrease(initial_speed, acceleration), 0)



                # Calculate engine damage
                car.engine_damage_level = car.calc_engine_damage(
                    car.rpm, car.w_level, old_gear, car.gear, car.engine_damage_level
                )
                car.engine_damaged = car.engine_IsDamaged(car.engine_damage_level)

                last_w_press = current_time

                if car.rpm > 6700 or car.rpm == car.max_rpm:
                    if start_rev is None:  # Start timing only when crossing 6700 for the first time
                        start_rev = timeit.default_timer()
                    else:
                        # Continuously update the time spent above 6700 while still in that range
                        time_above_6700 += timeit.default_timer() - start_rev
                        start_rev = timeit.default_timer()  # Reset start time to prevent double counting

                else:
                    if start_rev is not None:  # If RPM drops below 6700, finalize time count
                        time_above_6700 += timeit.default_timer() - start_rev
                        start_rev = None  # Reset start_rev since rpm is no longer above 6700

                # Incremement curr_w like curr_clutch 
                car.w_level = min(1.0, car.w_level + increment_speed * delta_time)  # Increase to 1.0
            
            else:
                car.w_level = max(0.0, car.w_level - increment_speed * delta_time)  # Decrease to 0.0


                # RPM falls back to 680
                if current_time - last_w_press >= 0.1 and car.rpm > 680 and not paused:
                    if car.gear == 0 or car.gear == 1:
                        car.rpm -= 100
                    elif car.gear == -1:
                        car.rpm -= 5
                    else:
                        car.rpm -= 25

                # Speed slowly falls back
                if current_time - last_w_press >= 0.1 and not paused:
                    if car.speed > 0:
                        car.speed = max(0, car.speed - 0.1)  # Ensure speed never goes negative
                    elif car.speed < 0:
                        car.speed += 0.1  # Directly set speed to 0 instead of adding 0.7

                    # Check for engine stall
                    if car.car_on and car.gear != 0 and not car.clutch_on and car.speed == 0 and car.clutch_level < 0.3 and car.w_level < 0.1:
                        car.car_on = False
                        engine_stall_count += 1

            if car.car_on and car.rpm <= 600:
                
                engine_sound.play_idle_sound()
            # Display engine stalled message only when engine stalls naturally
            if not car.car_on and car.gear != 0 and not car.clutch_on and car.speed == 0 and car.clutch_level < 0.3 and car.w_level < 0.1:
                car.engine_stalled = True
                car_text = "ENGINE STALLED"
                car_status = default_font.render(car_text, True, "red")
                screen.blit(car_status, (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 150))
                
                if not message_displayed:
                    title = "Engine Stalled"
                    message = "Gear must be set to Neutral to turn on the car.\n\nClutch must be pressed if gear is not Neutral and the car is stationary."
                    stall_thread = threading.Thread(target=display_message, args=(title, message,)) 
                    stall_thread.daemon = True  # Make thread close with main program
                    stall_thread.start()
                    message_displayed = True


            if (((default_control_set and ((keystate[pygame.K_s] and ws_option1) or (keystate[pygame.K_DOWN] and ws_option2))) or (not default_control_set and keystate[custom_brake])) and (current_time - last_s_press >= time_interval_S)): 
                car.speed = car.speedDecrease() 
                print(f"Slowing down, current speed is {car.speed}")
                
                last_s_press = current_time
                if car.car_on and car.gear != 0 and not (car.clutch_on) and car.speed == 0 and car.clutch_level < 0.3 and car.w_level < 0.1:
                    car.car_on = False
                    car_text = "ENGINE STALLED." 
                    car_status = default_font.render(car_text, True, "red")
                    engine_stall_count += 1

                    if paused or not paused:
                        screen.blit(car_status, (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 150))
                car.s_level = min(1.0, car.s_level + increment_speed * delta_time)
                
            
            else:
                if not paused:
                    car.s_level = max(0.0, car.s_level - increment_speed * delta_time)

        

        


        # Optimal Shift RPM Indicator (Green if RPM between 2500 and 3000 RPM, yellow otherwise)
        if car.rpm >= 2500 and car.rpm <= 3000:
            pygame.draw.circle(screen, [23, 193, 126], (275,150), 10, 20) # Green

        elif car.rpm > 4000 and car.rpm < 5500:
            pygame.draw.circle(screen, [245, 95, 16], (275,150), 10, 20) # Orange

        elif car.rpm >= 5500: 
            pygame.draw.circle(screen, [249, 24, 23], (275,150), 10, 20) # Red

        else:
            pygame.draw.circle(screen, [255, 246, 39], (275,150), 10, 20) # Yellow
            
        # Drawing W (outer rectangle)
        pygame.draw.rect(screen,"white",pygame.Rect(105, 500, 40, 200)) # Rect(x coord, y coord, x width, y height)

        # Filling outer rectangle with current W intensity
        pygame.draw.rect(screen,"black",pygame.Rect(105, 500, 40,(200 - (car.w_level)*200)))
        pygame.draw.rect(screen,"white",pygame.Rect(105, 500, 40,(200 - (car.w_level)*200)), 1)

        # Drawing S (outer rectangle)
        pygame.draw.rect(screen,"white",pygame.Rect(155, 500, 40, 200)) # Rect(x coord, y coord, x width, y width)

        # Filling outer rectangle with current S intensity
        pygame.draw.rect(screen,"black",pygame.Rect(155, 500, 40,(200 - (car.s_level)*200)))
        pygame.draw.rect(screen,"white",pygame.Rect(155, 500, 40,(200 - (car.s_level)*200)), 1)

        # Drawing Engine Damage (outer rectangle)
        pygame.draw.rect(screen,"red",pygame.Rect(420, 500, 30, 150)) # Rect(x coord, y coord, x width, y width)

        # Filling outer rectangle with current engine damage level
        pygame.draw.rect(screen,"black",pygame.Rect(420, 500, 30,(150 - (car.engine_damage_level)*1.5)))
        pygame.draw.rect(screen,"red",pygame.Rect(420, 500, 30,(150 - (car.engine_damage_level)*1.5)), 1)

        if car.engine_damage_level <= 30: # Load green engine image
            engine_img_path = resource_path("Images/Check_Engine_Green.png") #os.path.join("Source Code", "Images", "Check_Engine_Green.png")
        
        if car.engine_damage_level > 30 and car.engine_damage_level <= 75: # Load yellow engine image
            engine_img_path = resource_path("Images/Check_Engine_Yellow.png") #os.path.join("Source Code", "Images", "Check_Engine_Yellow.png")
        
        if car.engine_damage_level > 75: # Load red engine image
            engine_img_path = resource_path("Images/Check_Engine_Red.png") #os.path.join("Source Code", "Images", "Check_Engine_Red.png")
        
        engine_img = pygame.image.load(engine_img_path).convert_alpha()
        
        screen.blit(pygame.transform.smoothscale(engine_img, (45, 45)), (410, 655))

        



        # SPEEDOMETER GAUGE
        car.drawGauge(screen, (SCREEN_WIDTH // 2) + 200, SCREEN_HEIGHT // 2 - 140, 3.6 * car.speed, 220, 150, (math.pi)/4, 245, [255,255,255]) 
        
        # Drawing the small circle to cover the needle (speedometer)
        pygame.draw.circle(screen,"black",((SCREEN_WIDTH // 2) + 200, SCREEN_HEIGHT // 2 - 140),10,10) # SPEEDOMETER

        # RPM GAUGE
        if car.car_on:
            car.drawGauge(screen, (SCREEN_WIDTH // 2) - 200, SCREEN_HEIGHT // 2 - 90, 3.6 * car.rpm, 6800, 100, math.pi/4, 63.8, [255,255,255]) # RPM METER 
        else:
            car.drawGauge(screen, (SCREEN_WIDTH // 2) - 200, SCREEN_HEIGHT // 2 - 90, 0, 6800, 100, math.pi/4, 63.8, [255,255,255])
        



        if not paused:
            if car.clutch_on:
                clutch_text = "CLUTCH PRESSED"

            else:
                clutch_text = "CLUTCH NOT PRESSED"


            if (default_control_set and ((keystate[pygame.K_w] and ws_option1) or (keystate[pygame.K_UP] and ws_option2))) or (not default_control_set and keystate[custom_throttle]):
                w_text = "GAS PEDAL PRESSED"

            else:
                w_text = "GAS PEDAL NOT PRESSED"


            if (default_control_set and ((keystate[pygame.K_s] and ws_option1) or (keystate[pygame.K_DOWN] and ws_option2))) or (not default_control_set and keystate[custom_brake]):
                s_text = "BRAKES PRESSED"

            else:
                s_text = "BRAKES NOT PRESSED"


            if not car.car_on:
                on_off_text = "ENGINE TURNED OFF"
            
            if car.car_on:
                on_off_text = "ENGINE STARTED"

            clutch_status = screen_text_font.render(clutch_text,True,"white")
            w_status = screen_text_font.render(w_text,True,"white")
            s_status = screen_text_font.render(s_text,True,"white")
            on_off_status = screen_text_font.render(on_off_text,True,"red")

            if default_control_set:
                if not car.car_on:
                    on_off_text2 = "F TO TURN ON ENGINE"
                elif car.car_on:
                    on_off_text2 = ""

                if not car.clutch_on and clutch_option1:
                    clutch_text2 = "SHIFT TO PRESS CLUTCH"
                elif not car.clutch_on and clutch_option2:
                    clutch_text2 = "LCTRL TO PRESS CLUTCH"
                elif car.clutch_on:
                    clutch_text2 = ""


                if ws_option1:
                    w_text2 = "W TO PRESS THE THROTTLE"
                else:
                    w_text2 = "UP ARROW TO PRESS THE THROTTLE"
                

                if ws_option1:
                    s_text2 = "S TO PRESS THE BRAKE"
                else:
                    s_text2 = " DOWN ARROW TO BRAKE"


                e_text = "SHIFT + E TO SHIFT-UP"
                q_text = "SHIFT + Q TO SHIFT-DOWN"
                

            if not default_control_set:
                if not car.car_on:
                    on_off_text2 = f"{pygame.key.name(keybinds["ENGINE"])} TO TURN ON ENGINE"
                elif car.car_on:
                    on_off_text2 = ""

                if not car.clutch_on:
                    clutch_text2 = F"{pygame.key.name(keybinds["CLUTCH"])} TO PRESS CLUTCH"
                elif car.clutch_on:
                    clutch_text2 = ""

                w_text2 = f"{pygame.key.name(keybinds["THROTTLE"])} TO PRESS THE THROTTLE"
                

                s_text2 = f"{pygame.key.name(keybinds["BRAKE"])} TO PRESS THE BRAKE"
                

                
                e_text = f"{pygame.key.name(keybinds["CLUTCH"])} + {pygame.key.name(keybinds["SHIFT-UP"])} TO SHIFT-UP"
                q_text = f"{pygame.key.name(keybinds["CLUTCH"])} + {pygame.key.name(keybinds["SHIFT-DOWN"])} TO SHIFT-DOWN"
                
            info = "KEY MAPPINGS:"

            info_disp = screen_text_font.render(info, True, "white")
            on_off_text2_disp = screen_text_font.render(on_off_text2, True, "white")
            clutch_text2_disp = screen_text_font.render(clutch_text2, True, "white")
            w_text2_disp = screen_text_font.render(w_text2, True, "white")
            s_text2_disp = screen_text_font.render(s_text2, True, "white")
            e_text_disp = screen_text_font.render(e_text, True, "white")
            q_text_disp = screen_text_font.render(q_text, True, "white")

            screen.blit(info_disp,(SCREEN_WIDTH // 2 - (SCREEN_WIDTH / 2.1), SCREEN_HEIGHT // 2 - (SCREEN_HEIGHT / 3.2)))
            screen.blit(on_off_text2_disp, (SCREEN_WIDTH // 2 - (SCREEN_WIDTH / 2.025), SCREEN_HEIGHT // 2 - (SCREEN_HEIGHT / 3.6)))
            screen.blit(clutch_text2_disp, (SCREEN_WIDTH // 2 - (SCREEN_WIDTH / 2.025), SCREEN_HEIGHT // 2 - (SCREEN_HEIGHT / 4.2)))
            screen.blit(w_text2_disp, (SCREEN_WIDTH // 2 - (SCREEN_WIDTH / 2.025), SCREEN_HEIGHT // 2 - (SCREEN_HEIGHT / 5)))
            screen.blit(s_text2_disp, (SCREEN_WIDTH // 2 - (SCREEN_WIDTH / 2.025), SCREEN_HEIGHT // 2 - (SCREEN_HEIGHT / 6.2)))
            screen.blit(e_text_disp, (SCREEN_WIDTH // 2 - (SCREEN_WIDTH / 2.025), SCREEN_HEIGHT // 2 - (SCREEN_HEIGHT / 7.8)))
            screen.blit(q_text_disp, (SCREEN_WIDTH // 2 - (SCREEN_WIDTH / 2.025), SCREEN_HEIGHT // 2 - (SCREEN_HEIGHT / 11)))

        if paused or not paused:
            for button in [tutorial_button, telemetry_button]:  
                button.update()
                button.changeColor(pygame.mouse.get_pos())


            screen.blit(clutch_status,(SCREEN_WIDTH // 2 - 575, SCREEN_HEIGHT // 2 - 350)) 
            screen.blit(w_status,(SCREEN_WIDTH // 2 - 330, SCREEN_HEIGHT // 2 - 350)) 
            screen.blit(s_status,(SCREEN_WIDTH // 2 - 85, SCREEN_HEIGHT // 2 - 350)) 
            screen.blit(on_off_status,((SCREEN_WIDTH // 2 - 80, SCREEN_HEIGHT // 2 + 35)))


        start_p = timeit.default_timer() 
        if paused: 
            
            pause_menu(SCREEN_WIDTH, SCREEN_HEIGHT)
            end_p = timeit.default_timer()
            elapsed_p = end_p - start_p
            paused = False  


            continue

        # display engine damage level
        if car.engine_damaged == True:
            end_time = timeit.default_timer()
            elapsed_time = (end_time - start_time) - elapsed_p
            fade(screen, fail_screen(SCREEN_WIDTH, SCREEN_HEIGHT))

        screen.blit(pygame.transform.smoothscale(shifter_img, (150,150)), (shiftx - 50, shifty - 50))
       


        clock.tick(60)
        SCREEN_WIDTH, SCREEN_HEIGHT = screen.get_size()
        
        # Add after your event handling
        if show_telemetry and telemetry_window:
            try:
                if not telemetry_window.update(car):
                    telemetry_window = None
                    show_telemetry = False
            except Exception as e:
                print(f"Telemetry update error: {e}")
                telemetry_window = None
                show_telemetry = False
        
        # Add to your rendering section
        telemetry_button.update()
        telemetry_button.changeColor(pygame.mouse.get_pos())
        handle_throttle()
        pygame.display.flip()

    pygame.quit()

#----------------------------- CREATING THE OPTIONS MENU ----------------------------#
def options_menu():
    global default_control_set
    global engine_sound, engine_volume
    default_control_set = True


    click_count_ws = 0
    click_count_clutch = 0
    global ws_option1, ws_option2, clutch_option1, clutch_option2

    pygame.display.set_caption("Options - Stick Shift Simulator")

    backbutton_surface = pygame.image.load(resource_path("Images/buttonv2.png")).convert_alpha()
    backbutton_surface = pygame.transform.scale(backbutton_surface, (400, 125))
    backbutton_surface2 = pygame.transform.scale(backbutton_surface, (425, 125))
    SCREEN_WIDTH, SCREEN_HEIGHT = pygame.display.get_window_size()

    backbutton = DefaultButton(backbutton_surface, 0, 0, "BACK TO MAIN MENU", "black", screen)
    custom_keybinds_button = DefaultButton(backbutton_surface, 0, 0, "CUSTOM KEYBINDS", "black", screen)
    return_to_sim_button = DefaultButton(backbutton_surface2, 0, 0, "RETURN TO SIMULATION", "black", screen)

    subbutton_surface1 = pygame.image.load(resource_path("Images/control_button_unselected.png")).convert_alpha()
    subbutton_surface1 = pygame.transform.scale(subbutton_surface1, (300, 125))
    subbutton_surface2 = pygame.image.load(resource_path("Images/control_button_selected.png")).convert_alpha()
    subbutton_surface2 = pygame.transform.scale(subbutton_surface2, (300, 125))

    ws_subbutton = SubButton(subbutton_surface2, subbutton_surface1, 640, 360, "W/S") 
    ud_subbutton = SubButton(subbutton_surface1, subbutton_surface2, 640, 360, "↑/↓")

    shift_subbutton = SubButton(subbutton_surface2, subbutton_surface1, 460, 280, "LSHIFT") 
    ctrl_subbutton = SubButton(subbutton_surface1, subbutton_surface2, 460, 280, "LCTRL")

    volume_slider = Slider((SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 175), (500,80), 0.5, 0, 1)
    
    while True:
        SCREEN_WIDTH, SCREEN_HEIGHT = pygame.display.get_window_size()
        ws_subbutton.centerOnScreen(SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0)
        ud_subbutton.centerOnScreen(SCREEN_WIDTH, SCREEN_HEIGHT, 400, 0)

        shift_subbutton.centerOnScreen(SCREEN_WIDTH, SCREEN_HEIGHT, 0, 100)
        ctrl_subbutton.centerOnScreen(SCREEN_WIDTH, SCREEN_HEIGHT, 400, 100)
        backbutton.centerOnScreen(SCREEN_WIDTH, SCREEN_HEIGHT, -400, 300)
        custom_keybinds_button.centerOnScreen(SCREEN_WIDTH, SCREEN_HEIGHT, 400, 300)
        return_to_sim_button.centerOnScreen(SCREEN_WIDTH, SCREEN_HEIGHT, 0, 300)

        screen.blit(pygame.transform.scale(background, (SCREEN_WIDTH, SCREEN_HEIGHT)), (0, 0))  # Adjust BG image to current dimensions
        
        if volume_slider.container_rect.collidepoint(pygame.mouse.get_pos()) and pygame.mouse.get_pressed()[0]: 
            volume_slider.move_slider(pygame.mouse.get_pos)
            print(100 * volume_slider.get_value())
            engine_volume = volume_slider.get_value()
            engine_sound.set_volume(engine_volume)
        volume_slider.render(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                
                if ws_subbutton.checkForInput(pygame.mouse.get_pos()) or ud_subbutton.checkForInput(pygame.mouse.get_pos()):
                    
                    if click_count_ws % 2 != 0:
                        ws_option1 = True
                        ws_option2 = False
                        ws_subbutton.changeImage(subbutton_surface1, subbutton_surface2)
                        ud_subbutton.changeImage(subbutton_surface2, subbutton_surface1) 

                    if click_count_ws % 2 == 0:
                        ws_option1 = False
                        ws_option2 = True
                        ws_subbutton.changeImage(subbutton_surface2, subbutton_surface1) 
                        ud_subbutton.changeImage(subbutton_surface1, subbutton_surface2)

                    click_count_ws += 1
                    print(f"Current click count: {click_count_ws}")
                       
                    print(f"WS selected: {ws_option1}, updn sleected: {ws_option2}")
                    
                if shift_subbutton.checkForInput(pygame.mouse.get_pos()) or ctrl_subbutton.checkForInput(pygame.mouse.get_pos()):
                    if click_count_clutch % 2 != 0:
                        clutch_option1 = True
                        clutch_option2 = False 
                        shift_subbutton.changeImage(subbutton_surface1, subbutton_surface2)
                        ctrl_subbutton.changeImage(subbutton_surface2, subbutton_surface1) 
                    
                    if click_count_clutch % 2 == 0:
                        clutch_option1 = False
                        clutch_option2 = True
                        shift_subbutton.changeImage(subbutton_surface2, subbutton_surface1)
                        ctrl_subbutton.changeImage(subbutton_surface1, subbutton_surface2) 
                    
                    click_count_clutch += 1
                    print(f"Current click count: {click_count_ws}")
                    print(f"Shift selected: {clutch_option1}, CTRL sleected: {clutch_option2}")

                if backbutton.checkForInput(pygame.mouse.get_pos()):
                    fade(screen, main_menu)
                
                if custom_keybinds_button.checkForInput(pygame.mouse.get_pos()):
                    fade(screen, custom_keybinds_menu)
                
                if return_to_sim_button.checkForInput(pygame.mouse.get_pos()):
                    fade(screen, play)
        
        for button in [backbutton, ws_subbutton, ud_subbutton, shift_subbutton, ctrl_subbutton, custom_keybinds_button, return_to_sim_button]:
            button.update()
            button.changeColor(pygame.mouse.get_pos())
        
        def get_text_position(screen_width, screen_height, x_offset, y_offset):
            """Centers the text relative to the screen with offsets."""
            x_pos = screen_width // 2 + x_offset
            y_pos = screen_height // 2 + y_offset
            return x_pos, y_pos

        control_text1_x, control_text1_y = get_text_position(SCREEN_WIDTH, SCREEN_HEIGHT, -600, -5)
        control_text2_x, control_text2_y = get_text_position(SCREEN_WIDTH, SCREEN_HEIGHT, -550, 85)
        volume_text_x, volume_text_y = get_text_position(SCREEN_WIDTH, SCREEN_HEIGHT, -175, -125)

        control_text1 = option_font.render("THROTTLE/BRAKE CONTROL", True, "white")
        control_text2 = option_font.render("CLUTCH CONTROL", True, "white")
        volume_text = option_font.render(f"MASTER VOLUME: {math.trunc(100*engine_volume)}", True, "white")

        screen.blit(control_text1, (control_text1_x, control_text1_y))
        screen.blit(control_text2, (control_text2_x, control_text2_y))
        screen.blit(volume_text, (volume_text_x, volume_text_y))
        
        
        title_text = title_font.render("SIMULATION SETTINGS", True, [241, 128, 72])
        screen.blit(title_text,(SCREEN_WIDTH // 2 - 325, SCREEN_HEIGHT // 2 - 350))

        pygame.display.update()

#----------------------------- CREATING THE PAUSE MENU ----------------------------#
def pause_menu(width, height):
    global paused
    # Create a semi-transparent overlay
    overlay = pygame.Surface((width, height), pygame.SRCALPHA)

    pygame.draw.rect(overlay, [125, 125, 125, 225], [0,0, width, height])
   
    # Display pause text
    
    pause_text = option_font.render("Simulation Paused. Press ESC to Resume", True, "white")
    text_rect = pause_text.get_rect(center=(width // 2, height // 2 - 200))

    # Calculate the rectangle dimensions based on the text size
    rect_width = text_rect.width + 40  
    rect_height = text_rect.height + 20  

    rect_x = text_rect.centerx - rect_width // 2
    rect_y = text_rect.centery - rect_height // 2

    # Draw the rectangle
    pygame.draw.rect(overlay, "dark gray", [rect_x, rect_y, rect_width, rect_height], 0, 5)

    overlay.blit(pause_text, text_rect)

    
    

    button_surface = pygame.image.load(resource_path("Images/buttonv2.png")).convert_alpha()
    button_surface = pygame.transform.scale(button_surface, (400, 125))

    backbutton = DefaultButton(button_surface, 0, 0, "BACK TO MAIN MENU", "black", screen)
    optionsbutton = DefaultButton(button_surface, 0, 0, "OPTIONS", "black", screen)

    tutorial_button_surface = pygame.image.load(resource_path("Images/buttonv2.png")).convert_alpha()
    tutorial_button_surface = pygame.transform.scale(tutorial_button_surface, (250, 85))

    tutorial_button = DefaultButton(tutorial_button_surface, 0, 0, "(?) HELP (?)", "black", screen)


    screen.blit(overlay, (0, 0))    

    while True:
        SCREEN_WIDTH, SCREEN_HEIGHT = pygame.display.get_window_size()

        backbutton.centerOnScreen(SCREEN_WIDTH, SCREEN_HEIGHT, 0, 300)
        optionsbutton.centerOnScreen(SCREEN_WIDTH, SCREEN_HEIGHT, 0, 150)
        tutorial_button.centerOnScreen(SCREEN_WIDTH, SCREEN_HEIGHT, (SCREEN_WIDTH / 2.56), - (SCREEN_HEIGHT / 2.3))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:  # Press 'ESCAPE' to unpause
                    return
                
            if event.type == pygame.MOUSEBUTTONDOWN:
                if backbutton.checkForInput(pygame.mouse.get_pos()):
                    fade(screen, main_menu)
                
                if optionsbutton.checkForInput(pygame.mouse.get_pos()):
                    fade(screen, options_menu)

                if tutorial_button.checkForInput(pygame.mouse.get_pos()):
                    fade(screen, tutorial_screen)
                

          # Blit the overlay onto the screen
        for button in [backbutton, optionsbutton, tutorial_button]:
            button.update()
            button.changeColor(pygame.mouse.get_pos())

        pygame.display.update()

#----------------------------- CREATING THE FAIL SCREEN ----------------------------#
def fail_screen(width, height):
    # Create a semi-transparent overlay
    overlay = pygame.Surface((width, height), pygame.SRCALPHA)

    pygame.draw.rect(overlay, [245, 72, 66, 225], [0,0, width, height]) # Turn into red color
   
    
    fail_text = option_font.render("Engine Damaged. Press ESC to Return to Main Menu.", True, "red")
    text_rect = fail_text.get_rect(center=(width // 2, height // 2 - 200))

    # Calculate the rectangle dimensions based on the text size
    rect_width = text_rect.width + 40  
    rect_height = text_rect.height + 20  

    rect_x = text_rect.centerx - rect_width // 2
    rect_y = text_rect.centery - rect_height // 2

    # Draw the rectangle
    pygame.draw.rect(overlay, "dark gray", [rect_x, rect_y, rect_width, rect_height], 0, 5)

    overlay.blit(fail_text, text_rect)

    
      # Blit the overlay to the screen

    backbutton_surface = pygame.image.load(resource_path("Images/buttonv2.png")).convert_alpha()
    backbutton_surface = pygame.transform.scale(backbutton_surface, (400, 125))

    backbutton = DefaultButton(backbutton_surface, 0, 0, "BACK TO MAIN MENU", "black", screen)
    screen.blit(overlay, (0, 0))    

    clock = pygame.time.Clock()
    running = True
    while running:
        SCREEN_WIDTH, SCREEN_HEIGHT = pygame.display.get_window_size()

        backbutton.centerOnScreen(SCREEN_WIDTH, SCREEN_HEIGHT, 0, 300)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:  # Press 'ESCAPE' to unpause
                    fade(screen, main_menu)
            if event.type == pygame.MOUSEBUTTONDOWN:
                if backbutton.checkForInput(pygame.mouse.get_pos()):
                    fade(screen, main_menu)


        backbutton.update()
        backbutton.changeColor(pygame.mouse.get_pos())

        clock.tick(30)
        pygame.display.update()

#----------------------------- CREATING THE MAIN MENU ----------------------------#
def main_menu():



    pygame.display.set_caption("Main Menu - Stick Shift Simulator")
        # Load and scale the button image
    optionbutton_surface = pygame.image.load(resource_path("Images/button_surface.png")).convert_alpha() #pygame.image.load("Source Code/Images/button_surface.png").convert_alpha() <<<--- this caused an issue
    optionbutton_surface = pygame.transform.scale(optionbutton_surface, (400, 125))

    # Create instances of StartButton
    startbutton = DefaultButton(optionbutton_surface, 640, 360, "START SIMULATION", "white", screen)
    optionsbutton = DefaultButton(optionbutton_surface, 640, 360, "OPTIONS", "white", screen)
    tutorialbutton = DefaultButton(optionbutton_surface, 640, 360, "TUTORIAL", "white", screen)
    exitbutton = DefaultButton(optionbutton_surface, 640, 360, "EXIT", "white", screen)


    while True:
        SCREEN_WIDTH, SCREEN_HEIGHT = pygame.display.get_window_size()

        startbutton.centerOnScreen(SCREEN_WIDTH, SCREEN_HEIGHT, 0, -160)
        optionsbutton.centerOnScreen(SCREEN_WIDTH, SCREEN_HEIGHT, 0, -55)
        tutorialbutton.centerOnScreen(SCREEN_WIDTH, SCREEN_HEIGHT, 0, 50)
        exitbutton.centerOnScreen(SCREEN_WIDTH, SCREEN_HEIGHT, 0, 155)

        screen.blit(pygame.transform.scale(background, (SCREEN_WIDTH, SCREEN_HEIGHT)), (0, 0))  # Adjust BG image to current dimensions
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if startbutton.checkForInput(pygame.mouse.get_pos()):
                    fade(screen, play)  # Fade to play()
                if optionsbutton.checkForInput(pygame.mouse.get_pos()):
                    fade(screen, options_menu)
                    
                if exitbutton.checkForInput(pygame.mouse.get_pos()):
                    pygame.quit()
                    sys.exit()
                if tutorialbutton.checkForInput(pygame.mouse.get_pos()):
                    fade(screen, tutorial_screen)


        for button in [startbutton, optionsbutton, tutorialbutton, exitbutton]:
            button.update()
            button.changeColor(pygame.mouse.get_pos())

        title_text = title_font.render("Stick Shift Simulator", True, [241, 128, 72])
        screen.blit(title_text,(SCREEN_WIDTH // 2 - 328, SCREEN_HEIGHT // 2 - (SCREEN_HEIGHT / 2.06)))

        

        pygame.display.update()

#----------------------------- CREATING FADE ANIMATIONS ----------------------------#
def fade(screen, target_function, fade_speed=5):
    """Handles fade-out, calls the target function, then fades back in gradually."""
    fade_surface = pygame.Surface(screen.get_size())
    fade_surface.fill((0, 0, 0))  # Black overlay

    # Fade out (increase alpha)
    for alpha in range(0, 256, fade_speed):
        fade_surface.set_alpha(alpha)
        screen.blit(fade_surface, (0, 0))
        pygame.display.update()
        pygame.time.delay(10)

    # Call the target function before the fade-in starts
    target_function()

    # Fade in (decreasing alpha) while rendering the new screen
    for alpha in range(255, 0, -fade_speed):
        screen.fill((0, 0, 0))  # Clear screen for smooth transition
        target_function()  # Continuously render the new screen
        fade_surface.set_alpha(alpha)
        screen.blit(fade_surface, (0, 0))  # Overlay fades out
        pygame.display.update()
        pygame.time.delay(10)

#----------------------------- CREATING THE TUTORIAL SCREEN ----------------------------#
def tutorial_screen():


    I = 0

    navbutton_surface = pygame.image.load(resource_path("Images/buttonv2.png")).convert_alpha()
    navbutton_surface = pygame.transform.scale(navbutton_surface, (250, 125))
    navbutton_surface2 = pygame.transform.scale(navbutton_surface, (400, 125))

    next_button = DefaultButton(navbutton_surface, 0, 0, "NEXT", "black", screen)
    prev_button = DefaultButton(navbutton_surface, 0, 0, "PREVIOUS", "black", screen)
    back_button = DefaultButton(navbutton_surface2, 0, 0, "BACK TO SIMULATION", "black", screen)

    # Define the directory correctly
    tutorial_folder = resource_path("Tutorial") #os.path.join("Source Code", "Tutorial")
    

    # List files in the folder and sort them numerically
    files = (os.listdir(tutorial_folder)) 

    image_paths = []
    # List files in the folder and sort them in ascending order
    files = sorted(os.listdir(tutorial_folder))

    for file in files:
        full_path = resource_path(os.path.join(tutorial_folder, file))
        image_paths.append(full_path)

    '''
    for file in files:
        full_path = os.path.join(tutorial_folder, file)  # Get full path
        image_paths.append(os.path.abspath(full_path))  # Get absolute path

    '''

    print(image_paths)


    run = True
    
    while run:
        pygame.display.set_caption("Tutorial - Stick Shift Simulator")
        SCREEN_WIDTH, SCREEN_HEIGHT = screen.get_size()
        screen.blit(pygame.transform.scale(background, (SCREEN_WIDTH, SCREEN_HEIGHT)), (0,0))

        curr_image = pygame.image.load(image_paths[I]).convert_alpha()
        curr_image = pygame.transform.smoothscale(curr_image, (SCREEN_WIDTH // 1.5, SCREEN_HEIGHT // 1.5))
        border = pygame.draw.rect(screen, (23, 22, 22), pygame.Rect(SCREEN_WIDTH // 8, SCREEN_HEIGHT // 8 + 20, SCREEN_WIDTH - 325, SCREEN_HEIGHT - 200)) # Rect(x coord, y coord, x width, y width)
        screen.blit(curr_image, (SCREEN_WIDTH // 8 + 50, SCREEN_HEIGHT // 8 + 40))

        next_button.centerOnScreen(SCREEN_WIDTH, SCREEN_HEIGHT, (SCREEN_WIDTH / 2.56), (SCREEN_HEIGHT / 2.4))
        prev_button.centerOnScreen(SCREEN_WIDTH, SCREEN_HEIGHT, -(SCREEN_WIDTH / 2.56), (SCREEN_HEIGHT / 2.4))
        back_button.centerOnScreen(SCREEN_WIDTH, SCREEN_HEIGHT, ((SCREEN_WIDTH / 2.56) -(SCREEN_WIDTH / 2.56))/2, (SCREEN_HEIGHT / 2.4))
        
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    fade(screen, main_menu)
            if event.type == pygame.MOUSEBUTTONDOWN:
                if next_button.checkForInput(pygame.mouse.get_pos()):
                    I += 1
                    if I == len(image_paths):
                        I = 0
                if prev_button.checkForInput(pygame.mouse.get_pos()):
                    I -= 1
                    if I == 0:
                        I == len(image_paths) - 1
                if back_button.checkForInput(pygame.mouse.get_pos()):
                    fade(screen, play)

        for button in [next_button, prev_button, back_button]:
            button.update()
            button.changeColor(pygame.mouse.get_pos())           
        
        
        title_text = title_font.render("TUTORIAL", True, [241, 128, 72])
        screen.blit(title_text,(SCREEN_WIDTH // 2 - 125, SCREEN_HEIGHT // 2 - (SCREEN_HEIGHT / 2)))
        pygame.display.update()

    pygame.quit()

#----------------------------- CREATING THE QUIT SCREEN ----------------------------#
def quit_screen():
    global sum_rpm, sum_rpm_count, elapsed_time, engine_stall_count, excess_rev_count, elapsed_p, eng_damage, time_above_6700 


    button_surface = pygame.image.load(resource_path("Images/buttonv2.png")).convert_alpha()
    button_surface = pygame.transform.scale(button_surface, (250, 125))
    button_surface2 = pygame.transform.scale(button_surface, (450, 125))

    esc_button = DefaultButton(button_surface, 0, 0, "BACK", "black", screen)
    gen_button = DefaultButton(button_surface2, 0, 0, "GENERATE PDF REPORT", "black", screen)

    run = True
    if sum_rpm == 0 or sum_rpm_count == 0:
        avg_rpm = 0
    else:
        avg_rpm = round((sum_rpm)/(sum_rpm_count), 2)
    

    while run:
        pygame.display.set_caption("Confirmation Menu - Stick Shift Simulator")
        SCREEN_WIDTH, SCREEN_HEIGHT = screen.get_size()
        screen.blit(pygame.transform.scale(background, (SCREEN_WIDTH, SCREEN_HEIGHT)), (0,0))

        esc_button.centerOnScreen(SCREEN_WIDTH, SCREEN_HEIGHT, 0, (SCREEN_HEIGHT / 2.4))
        gen_button.centerOnScreen(SCREEN_WIDTH, SCREEN_HEIGHT, 0, -(SCREEN_HEIGHT / 2.4))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    fade(screen, main_menu)
                
            if event.type == pygame.MOUSEBUTTONDOWN:
                if esc_button.checkForInput(pygame.mouse.get_pos()):
                    fade(screen, play)
                if gen_button.checkForInput(pygame.mouse.get_pos()):
                    user_statistics = {
                        "Number of Engine Stalls": engine_stall_count,
                        "Time Spent Revving Excessively": round(time_above_6700, 0),
                        "Average RPM": avg_rpm,
                        "Total Drive Time (seconds)": round(elapsed_time, 2),
                        "Engine Damage Level": round(eng_damage, 1)
                    }
                    generate_pdf_report(user_statistics)
        
        for button in [esc_button, gen_button]:
            button.update()
            button.changeColor(pygame.mouse.get_pos())

        pygame.display.update()

#----------------------------- CREATING THE PDF REPORT ----------------------------#
def generate_pdf_report(user_stats):
    # Initialize the Tkinter root window (hidden)
    root = Tk()
    root.withdraw()  # Hide the root window

    # Open a file dialog to choose the save location
    file_path = asksaveasfilename(
        defaultextension=".pdf",  # Default file extension
        filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],  # File type filters
        title="Save PDF Report As"  # Dialog title
    )

    # Check if the user selected a file path
    if not file_path:
        print("Save operation cancelled.")
        return

    # Create a PDF document at the selected file path
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Times-Bold", 16)  # Times New Roman Bold for the title
    title_text = "Stick Shift Simulator - Session Report"
    title_width = c.stringWidth(title_text, "Times-Bold", 16)  # Calculate the width of the title
    title_x = (width - title_width) / 2  # Center the title horizontally
    c.drawString(title_x, height - 50, title_text)  # Draw the centered title

    # Draw statistics
    y_position = height - 100
    for stat, value in user_stats.items():
        # Draw the stat label in Times New Roman Bold
        c.setFont("Times-Bold", 12)  # Times New Roman Bold for labels
        c.drawString(100, y_position, f"{stat}:")

        # Draw the value in regular Times New Roman
        c.setFont("Times-Roman", 12)  # Regular Times New Roman for values
        # Calculate the x-position for the value (right after the label)
        label_width = c.stringWidth(f"{stat}:", "Times-Bold", 12)
        c.drawString(100 + label_width + 5, y_position, str(value))

        y_position -= 20  # Move down for the next stat

    # Save the PDF
    c.save()
    print(f"PDF saved successfully at {file_path}")




main_menu()


