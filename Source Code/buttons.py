import pygame
import sys
import os
from util import resource_path

pygame.init()
flags = pygame.RESIZABLE
screen = pygame.display.set_mode((1280,720), flags)


background_path = resource_path("Images/background_img.png") # os.path.join("Source Code", "Images", "background_img.png") # Maybe add option for user to toggle their background image
background = pygame.image.load(background_path)


pygame.display.set_caption("Button")
button_font = pygame.font.SysFont("JetBrains Mono", 30)
title_font = pygame.font.SysFont("ERODED PERSONAL USE Regular", 130)



class DefaultButton:
    def __init__(self, image, x_pos, y_pos, text_input, text_color, surface):
        self.image = image
        self.x_pos = x_pos
        self.y_pos = y_pos
        self.rect = self.image.get_rect(center=(self.x_pos, self.y_pos))
        self.text_input = text_input
        self.text_color = text_color
        self.text = button_font.render(self.text_input, True, "white")
        self.text_rect = self.text.get_rect(center=(self.x_pos, self.y_pos))
        self.surface = surface


    def update(self):
        self.surface.blit(self.image, self.rect)
        self.surface.blit(self.text, self.text_rect)

    def checkForInput(self, position): # checks if mouse pos is within the coordinates of the button
        if position[0] in range(self.rect.left, self.rect.right) and position[1] in range(self.rect.top, self.rect.bottom): # position is a tuple, [0] is x coord and [1] is y coord
            print("Button Press!")
            return True
        return False
    
    def changeColor(self, position):
        if position[0] in range(self.rect.left, self.rect.right) and position[1] in range(self.rect.top, self.rect.bottom):
            self.text = button_font.render(self.text_input, True, [241, 128, 72])
        else:
            self.text = button_font.render(self.text_input, True, self.text_color)
    
    def centerOnScreen(self, screen_width, screen_height, x_offset, y_offset):
        self.x_pos = screen_width // 2 + x_offset
        self.y_pos = screen_height // 2 + y_offset
        self.rect = self.image.get_rect(center=(self.x_pos, self.y_pos))
        self.text_rect = self.text.get_rect(center=(self.x_pos, self.y_pos))

class SubButton: # Make this so that clicking will change the color of the button completely
    def __init__(self, image1, image2, x_pos, y_pos, text_input): # removed text input for now
        self.image1 = image1
        self.image2 = image2
        self.x_pos = x_pos
        self.y_pos = y_pos
        self.rect = self.image1.get_rect(center=(self.x_pos, self.y_pos))
        self.text_input = text_input
        self.text = button_font.render(self.text_input, True, "white")
        self.text_rect = self.text.get_rect(center=(self.x_pos, self.y_pos))
    
    def update(self):
        screen.blit(self.image1, self.rect)
        screen.blit(self.text, self.text_rect)

    def checkForInput(self, position): # checks if mouse pos is within the coordinates of the button
        if position[0] in range(self.rect.left, self.rect.right) and position[1] in range(self.rect.top, self.rect.bottom): # position is a tuple, [0] is x coord and [1] is y coord
            print("Button Press!")
            '''self.image = self.image2'''
            screen.blit(self.image1, self.rect)
            return True
        return False
    
    def changeColor(self, position):
        if position[0] in range(self.rect.left, self.rect.right) and position[1] in range(self.rect.top, self.rect.bottom):
            self.text = button_font.render(self.text_input, True, [241, 128, 72])
        else:
            self.text = button_font.render(self.text_input, True, (71, 68, 66))
    
    def centerOnScreen(self, screen_width, screen_height, x_offset, y_offset):
        self.x_pos = screen_width // 2 + x_offset
        self.y_pos = screen_height // 2 + y_offset
        self.rect = self.image1.get_rect(center=(self.x_pos, self.y_pos))
        self.text_rect = self.text.get_rect(center=(self.x_pos, self.y_pos))

    def changeImage(self, image1, image2):            # add image 1, image 2 --> call this function when mouse pointer is clicked, remove from check for input -- keep track of mouse click, if div by 2, reset to old image
        if self.image1 == image1:
            self.image1 = image2
        else:
            self.image1 = image1

'''
# IDEA
Resemble menu screen like a car console (start in the middle, other options on either side)
'''