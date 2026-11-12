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


    # ------------------------------------------------------------ AUDIO START
AUDIO_OK = pygame.mixer.get_init() is not None
SEMITONES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def noteFreq(name):
    if name == "R":
        return 0
    n = SEMITONES[name[0]]
    i = 1
    if name[i] == "#":
        n += 1
        i += 1
    elif name[i] == "b":
        n -= 1
        i += 1
    octave = int(name[i:])
    midi = 12 * (octave + 1) + n
    return 440.0 * 2 ** ((midi - 69) / 12)


def waveValue(wave, p):
    if wave == "square":
        return 1.0 if p < 0.5 else -1.0
    if wave == "triangle":
        return 4.0 * abs(p - 0.5) - 1.0
    return random.uniform(-1.0, 1.0)


def renderNotes(notes, wave="square", volume=0.3, decay=1.0):
    buf = array.array("h")
    for freq, dur in notes:
        n = int(SAMPLE_RATE * dur)
        phase = 0.0
        for i in range(n):
            t = i / n
            if freq <= 0:
                v = 0.0
            else:
                phase += freq / SAMPLE_RATE
                v = waveValue(wave, phase % 1.0)
            env = min(1.0, i / 80.0) * (1.0 - t) ** decay
            buf.append(int(v * env * volume * 32767))
    return buf


def renderSlide(f0, f1, dur, wave="square", volume=0.3, decay=1.0):
    buf = array.array("h")
    n = int(SAMPLE_RATE * dur)
    phase = 0.0
    for i in range(n):
        t = i / n
        phase += (f0 + (f1 - f0) * t) / SAMPLE_RATE
        v = waveValue(wave, phase % 1.0)
        env = min(1.0, i / 80.0) * (1.0 - t) ** decay
        buf.append(int(v * env * volume * 32767))
    return buf


def mix(a, b):
    n = max(len(a), len(b))
    out = array.array("h", [0]) * n
    for i in range(n):
        v = (a[i] if i < len(a) else 0) + (b[i] if i < len(b) else 0)
        out[i] = max(-32767, min(32767, v))
    return out


def toSound(buf):
    channels = pygame.mixer.get_init()[2]
    if channels == 2:
        stereo = array.array("h")
        for s in buf:
            stereo.append(s)
            stereo.append(s)
        buf = stereo
    return pygame.mixer.Sound(buffer=buf.tobytes())


# Original chiptune loop (made for this game)
def buildMusic():
    eighth = 0.2
    bars = [
        "C5 E5 G5 E5 C5 E5 G5 R",
        "A4 C5 E5 C5 A4 C5 E5 R",
        "F4 A4 C5 A4 F4 A4 C5 R",
        "G4 B4 D5 B4 G4 B4 D5 G5",
        "C5 D5 E5 G5 E5 D5 C5 R",
        "A4 B4 C5 E5 C5 B4 A4 R",
        "F4 G4 A4 C5 A4 G4 F4 A4",
        "G4 B4 D5 G5 D5 B4 G4 R",
    ]
    melody = []
    for bar in bars:
        for name in bar.split():
            melody.append((noteFreq(name), eighth))

    bassBars = ["C3 G3 C3 G3", "A2 E3 A2 E3",
                "F2 C3 F2 C3", "G2 D3 G2 D3"] * 2
    bass = []
    for bar in bassBars:
        for name in bar.split():
            bass.append((noteFreq(name), eighth * 2))

    return mix(renderNotes(melody, "square", 0.14, 0.6),
               renderNotes(bass, "triangle", 0.30, 0.3))


def buildSounds():
    if not AUDIO_OK:
        return {}
    nf = noteFreq
    s = {}
    s["bounce"] = toSound(renderSlide(300, 520, 0.08, "square", 0.25, 1.0))
    s["hit"] = toSound(mix(
        renderNotes([(1, 0.07)], "noise", 0.35, 1.5),
        renderSlide(180, 90, 0.09, "triangle", 0.4, 1.0)))
    s["break"] = toSound(mix(
        renderNotes([(1, 0.22)], "noise", 0.45, 1.2),
        renderSlide(220, 60, 0.22, "triangle", 0.45, 1.0)))
    s["coin"] = toSound(renderNotes(
        [(nf("B5"), 0.07), (nf("E6"), 0.30)], "square", 0.22, 1.2))
    s["powerup"] = toSound(renderNotes(
        [(nf(n), 0.06) for n in ["C5", "E5", "G5", "C6", "E6", "G6"]],
        "square", 0.22, 0.8))
    s["launch"] = toSound(renderSlide(250, 700, 0.12, "square", 0.22, 0.8))
    s["lose"] = toSound(renderSlide(700, 150, 0.6, "square", 0.25, 0.6))
    s["gameover"] = toSound(renderNotes(
        [(nf("G4"), 0.18), (nf("E4"), 0.18), (nf("C4"), 0.18),
         (nf("G3"), 0.5)], "triangle", 0.45, 0.7))
    s["clear"] = toSound(renderNotes(
        [(nf(n), 0.1) for n in ["C5", "E5", "G5", "C6", "G5", "C6"]]
        + [(nf("E6"), 0.4)], "square", 0.22, 0.7))
    s["music"] = toSound(buildMusic())
    s["music"].set_volume(0.35)
    return s
# -------------------------------------------------------------- AUDIO END