import os, sys, pygame, json 
# json files work well with python dictionaries

def load_existing_save(savefile):
    with open(resource_path(savefile), 'r+') as file: #os.path.join(savefile)
        controls = json.load(file)
    return controls

def write_save(data):
    with open(resource_path('save.json'), 'w') as file:
        json.dump(data, file)

'''def write_save(data):
    with open(os.path.join(os.getcwd(),'save.json'), 'w') as file:
        json.dump(data, file)'''

def load_save():
    try:
    # Save is loaded 
        save = load_existing_save('save.json')
    except:
    # No save file, so create one
        save = create_save()
        write_save(save)
    return save


def create_save(): # Runs when the player has no previous savefile, default controls
    new_save = {
    "controls":{ # control string mapped to a profile string, either 0 or 1
        "0" : {"ENGINE": pygame.K_f, "THROTTLE": pygame.K_w, "BRAKE": pygame.K_s,  # profile 0
                "CLUTCH": pygame.K_LSHIFT, "SHIFT-UP": pygame.K_e, "SHIFT-DOWN": pygame.K_q,
                "NAV-UP": pygame.K_UP, "NAV-DOWN": pygame.K_DOWN,
                "NAV-LEFT": pygame.K_LEFT, "NAV-RIGHT": pygame.K_RIGHT, "EDIT": pygame.K_SPACE},
        "1" : {"ENGINE": pygame.K_f, "THROTTLE": pygame.K_w, "BRAKE": pygame.K_s,  # profile 1
                "CLUTCH": pygame.K_LSHIFT, "SHIFT-UP": pygame.K_e, "SHIFT-DOWN": pygame.K_q,
                "NAV-UP": pygame.K_UP, "NAV-DOWN": pygame.K_DOWN,
                "NAV-LEFT": pygame.K_LEFT, "NAV-RIGHT": pygame.K_RIGHT, "EDIT": pygame.K_SPACE} 
        },
    "current_profile": 0
    } 
    return new_save

def reset_keys(actions): # resets all keybinds in the "actions" dictionary to False
    for action in actions:
        actions[action] = False
    return actions

# Not related to the custom controls, but this function converts absolute file paths to relative
def resource_path(relative_path):
    """Get absolute path to resource (works for dev and PyInstaller bundle)."""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)