import pygame, sys
from util import write_save

class Controls_Handler():
    def __init__(self, save, width, height): # save -> dictionary
        self.save_file = save # pointer to the "save" dictionary
        self.curr_block = save["current_profile"] # keeps track of the profile chosen
        self.controls = self.save_file["controls"][str(self.curr_block)]
        self.setup()
        self.width = width // 4
        self.height = height // 4


    def update(self, actions):
        if self.selected:
            self.set_new_control()
        else:
            self.navigate_menu(actions)
    
    def render(self, surface):
        self.draw_text(surface, "Control Profile " + str(self.curr_block+1) , 20, pygame.Color((255,255,255)), self.width / 2, self.height/8) 
        self.display_controls(surface, self.save_file["controls"][str(self.curr_block)])
        if self.curr_block == self.save_file["current_profile"]: self.draw_text(surface, "*" , 20, pygame.Color((255,255,255)), 20, 20)

    def navigate_menu(self, actions):
         # Move the cursor up and down
        if actions["NAV-DOWN"]: self.curr_index = (self.curr_index + 1) % (len(self.save_file["controls"][str(self.curr_block)]) + 1) # The %  ensures that the current index doesnt go out of bounds, and has a looping behavior
        if actions["NAV-UP"]: self.curr_index = (self.curr_index - 1) % (len(self.save_file["controls"][str(self.curr_block)]) + 1)
        # Switch between profiles
        if actions["NAV-LEFT"]: self.curr_block = (self.curr_block -1) % len(self.save_file["controls"]) 
        if actions["NAV-RIGHT"]: self.curr_block = (self.curr_block +1) % len(self.save_file["controls"]) 
        # Handle Selection
        if actions["EDIT"] or actions["ENGINE"]:
             # Set the current profile to be the main one
            if self.cursor_dict[self.curr_index] == "Set Current Profile":
                self.controls = self.save_file["controls"][str(self.curr_block)]
                self.save_file["current_profile"] = self.curr_block
                write_save(self.save_file)
            else: 
                self.selected = True
    
    def set_new_control(self):
        selected_control = self.cursor_dict[self.curr_index]
        done = False
        while not done:
            for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        done = True
                        pygame.quit()
                        sys.exit()
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            done = True
                            pygame.quit()
                            sys.exit()
                        elif event.key not in self.save_file["controls"][str(self.curr_block)].values():
                            self.save_file["controls"][str(self.curr_block)][selected_control] = event.key
                            write_save(self.save_file)
                            self.selected = False
                            done = True



    def display_controls(self, surface, controls):
        color = (255,13,5) if self.selected else (191, 189, 187) 
        pygame.draw.rect(surface, color, (80, self.height/4 - 10 + (self.curr_index*20), self.width - 150, 20) )
        i = 0
        for control in controls:
            self.draw_text(surface, control + ' - ' + pygame.key.name(controls[control]),20, 
                            pygame.Color((47, 129, 222)), self.width / 2, self.height/4 + i)
            i += 20
        self.draw_text(surface, "SET CURRENT PROFILE", 15, pygame.Color((230,230,230)), self.width / 2, self.height/4 + i)


    def setup(self):
        self.selected = False # Checks if player has selected a control to change or not
        self.font = pygame.font.SysFont("JETBRAINS MONO", 15)
        self.cursor_dict = {} # Empty dictionary
        self.curr_index = 0
        i = 0
        for control in self.controls: # iterates through all control options in self.controls
            self.cursor_dict[i] = control # maps a number to each control: 1 -> W, etc.
            i += 1
        self.cursor_dict[i] = "Set Current Profile"

    def draw_text(self, surface, text, size, color, x, y):
        text_surface = self.font.render(text, False, color, size) 
        text_surface.set_colorkey((0,0,0))
        text_rect = text_surface.get_rect()
        text_rect.center = (x, y)
        surface.blit(text_surface, text_rect)

