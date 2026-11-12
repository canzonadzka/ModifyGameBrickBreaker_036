import array
import math
import os
import random

import pygame

SAMPLE_RATE = 22050
pygame.mixer.pre_init(SAMPLE_RATE, -16, 1, 512)
pygame.init()

# Screen
WIDTH, HEIGHT = 600, 500
FPS = 60
TOP = 36            # top edge of the play area (below the HUD)
GROUND_Y = 470      # top of the ground
BLOCK_W, BLOCK_H = 54, 24

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Super Block Breaker")
clock = pygame.time.Clock()

font = pygame.font.Font(None, 28)
smallFont = pygame.font.Font(None, 22)
midFont = pygame.font.Font(None, 36)
titleFont = pygame.font.Font(None, 72)
bigFont = pygame.font.Font(None, 84)
questionFont = pygame.font.Font(None, 30)

HS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "highscore.txt")


# ---------------------------------------------------------------- helpers
def lerp(a, b, t):
    return a + (b - a) * t


def lerpColor(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


def loadHighScore():
    try:
        with open(HS_FILE, "r") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return 0


def saveHighScore(value):
    try:
        with open(HS_FILE, "w") as f:
            f.write(str(value))
    except OSError:
        pass


def drawText(surf, text, textFont, color, pos, center=False,
             shadow=(0, 0, 0)):
    img = textFont.render(text, True, color)
    sh = textFont.render(text, True, shadow)
    rect = img.get_rect(center=pos) if center else img.get_rect(topleft=pos)
    surf.blit(sh, rect.move(2, 2))
    surf.blit(img, rect)


# Extruded text gives a 3D look
def draw3dText(surf, text, textFont, center, front, back, depth=6):
    imgBack = textFont.render(text, True, back)
    imgFront = textFont.render(text, True, front)
    rect = imgFront.get_rect(center=center)
    for d in range(depth, 0, -1):
        surf.blit(imgBack, rect.move(d, d))
    surf.blit(imgFront, rect)


def dim(surf, alpha):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, alpha))
    surf.blit(overlay, (0, 0))

    