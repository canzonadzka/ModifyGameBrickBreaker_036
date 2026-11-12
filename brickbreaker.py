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


SFX = {}
SPR = {}


# ----------------------------------------------------------------- sprites
def bevel(w, h, base, light, dark):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(s, base, (0, 0, w, h), border_radius=4)
    pygame.draw.line(s, light, (3, 1), (w - 4, 1), 2)
    pygame.draw.line(s, light, (1, 3), (1, h - 4), 2)
    pygame.draw.line(s, dark, (3, h - 2), (w - 4, h - 2), 2)
    pygame.draw.line(s, dark, (w - 2, 3), (w - 2, h - 4), 2)
    return s


def makeBrick(w, h):
    s = bevel(w, h, (200, 80, 20), (240, 140, 80), (110, 40, 10))
    mortar = (90, 35, 10)
    pygame.draw.line(s, mortar, (3, h // 2), (w - 4, h // 2), 2)
    pygame.draw.line(s, mortar, (w // 2, 3), (w // 2, h // 2), 2)
    pygame.draw.line(s, mortar, (w // 4, h // 2), (w // 4, h - 4), 2)
    pygame.draw.line(s, mortar, (3 * w // 4, h // 2), (3 * w // 4, h - 4), 2)
    return s


def makeQuestion(w, h, used=False):
    if used:
        s = bevel(w, h, (150, 100, 50), (190, 140, 90), (80, 50, 20))
    else:
        s = bevel(w, h, (250, 185, 50), (255, 235, 150), (170, 100, 10))
    for (x, y) in [(5, 5), (w - 6, 5), (5, h - 6), (w - 6, h - 6)]:
        pygame.draw.circle(s, (110, 60, 10), (x, y), 2)
    if not used:
        shadow = questionFont.render("?", True, (150, 80, 0))
        mark = questionFont.render("?", True, WHITE)
        cx, cy = w // 2, h // 2
        s.blit(shadow, shadow.get_rect(center=(cx + 1, cy + 1)))
        s.blit(mark, mark.get_rect(center=(cx, cy)))
    return s


def makeHard(w, h, damage=0):
    s = bevel(w, h, (140, 140, 150), (215, 215, 225), (60, 60, 75))
    pygame.draw.rect(s, (105, 105, 118), (6, 5, w - 12, h - 10),
                     border_radius=2)
    pygame.draw.rect(s, (70, 70, 85), (6, 5, w - 12, h - 10), 1,
                     border_radius=2)
    crack = (40, 40, 50)
    if damage >= 1:
        pygame.draw.lines(s, crack, False,
                          [(w // 3, 2), (w // 3 + 6, h // 3),
                           (w // 3 - 3, h // 2), (w // 3 + 4, h - 3)], 2)
    if damage >= 2:
        pygame.draw.lines(s, crack, False,
                          [(2 * w // 3, 2), (2 * w // 3 - 6, h // 3),
                           (2 * w // 3 + 3, 2 * h // 3),
                           (2 * w // 3 - 4, h - 3)], 2)
    return s


def makeMushroom(size):
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    k = size / 26.0

    def P(v):
        return int(v * k)

    pygame.draw.rect(s, (245, 225, 185), (P(7), P(14), P(12), P(10)),
                     border_radius=P(4))
    pygame.draw.rect(s, (200, 170, 120), (P(7), P(14), P(12), P(10)), 1,
                     border_radius=P(4))
    pygame.draw.ellipse(s, (200, 25, 25), (P(1), P(1), P(24), P(18)))
    pygame.draw.ellipse(s, (255, 90, 80), (P(5), P(3), P(9), P(5)))
    pygame.draw.circle(s, WHITE, (P(7), P(11)), P(3))
    pygame.draw.circle(s, WHITE, (P(19), P(11)), P(3))
    pygame.draw.circle(s, WHITE, (P(14), P(7)), P(3))
    pygame.draw.ellipse(s, (130, 10, 10), (P(1), P(1), P(24), P(18)),
                        max(1, P(1)))
    return s


def makeBall(radius):
    d = radius * 2 + 2
    s = pygame.Surface((d, d), pygame.SRCALPHA)
    cx = cy = d // 2
    for r in range(radius, 0, -1):
        t = 1 - r / radius
        col = lerpColor((140, 15, 10), (255, 200, 60), t ** 0.8)
        off = int((radius - r) * 0.35)
        pygame.draw.circle(s, col, (cx - off, cy - off), r)
    pygame.draw.circle(s, (255, 255, 230),
                       (cx - radius // 3, cy - radius // 3),
                       max(1, radius // 4))
    return s


def makePipe(width, h=24):
    s = pygame.Surface((width, h), pygame.SRCALPHA)
    rim = 12
    for yy in range(h - 4):
        t = yy / (h - 5)
        shade = max(0.30, 1.0 - abs(t - 0.30) * 1.4)
        col = (int(20 + 50 * shade), int(60 + 150 * shade),
               int(20 + 40 * shade))
        pygame.draw.line(s, col, (rim - 2, yy + 2), (width - rim + 2, yy + 2))
    pygame.draw.line(s, (5, 60, 10), (rim - 2, 1), (width - rim + 2, 1))
    pygame.draw.line(s, (5, 60, 10), (rim - 2, h - 3), (width - rim + 2, h - 3))
    for x0 in (0, width - rim):
        pygame.draw.rect(s, (40, 190, 60), (x0, 0, rim, h), border_radius=4)
        pygame.draw.rect(s, (150, 255, 150), (x0 + 2, 2, 3, h - 4),
                         border_radius=1)
        pygame.draw.rect(s, (10, 80, 20), (x0, 0, rim, h), 2,
                         border_radius=4)
    return s


def makeCloud(scale):
    w, h = int(110 * scale), int(50 * scale)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    blobs = [(0.28, 0.62, 0.30), (0.5, 0.42, 0.38),
             (0.72, 0.60, 0.30), (0.5, 0.62, 0.30)]
    for fx, fy, fr in blobs:
        pygame.draw.circle(s, (205, 222, 245),
                           (int(fx * w), int(fy * h) + 3), int(fr * h))
    for fx, fy, fr in blobs:
        pygame.draw.circle(s, WHITE, (int(fx * w), int(fy * h)), int(fr * h))
    return s


def drawHill(surf, cx, base, w, h):
    rect = pygame.Rect(cx - w // 2, base - h, w, h * 2)
    pygame.draw.ellipse(surf, (20, 110, 30), rect)
    pygame.draw.ellipse(surf, (40, 160, 50), rect.inflate(-10, -10).move(-4, -3))
    pygame.draw.ellipse(surf, (95, 210, 90),
                        pygame.Rect(int(cx - w * 0.28), base - h + 10,
                                    int(w * 0.30), int(h * 0.35)))


def makeBackground():
    bg = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        bg.fill(lerpColor((70, 130, 250), (190, 225, 255), y / HEIGHT),
                (0, y, WIDTH, 1))
    drawHill(bg, 120, GROUND_Y, 260, 130)
    drawHill(bg, 470, GROUND_Y, 200, 90)
    drawHill(bg, 330, GROUND_Y, 120, 55)
    return bg


def makeGround():
    gh = HEIGHT - GROUND_Y
    g = pygame.Surface((WIDTH, gh))
    g.fill((90, 35, 10))
    tile = makeBrick(30, gh)
    for x in range(0, WIDTH, 30):
        g.blit(tile, (x, 0))
    pygame.draw.line(g, (255, 170, 90), (0, 0), (WIDTH, 0), 2)
    return g


def buildSprites():
    SPR["brick"] = makeBrick(BLOCK_W, BLOCK_H)
    SPR["question"] = makeQuestion(BLOCK_W, BLOCK_H, False)
    SPR["used"] = makeQuestion(BLOCK_W, BLOCK_H, True)
    SPR["hard"] = [makeHard(BLOCK_W, BLOCK_H, d) for d in range(3)]
    shadow = pygame.Surface((BLOCK_W, BLOCK_H), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 70), (0, 0, BLOCK_W, BLOCK_H),
                     border_radius=4)
    SPR["shadow"] = shadow
    SPR["mushroom"] = makeMushroom(26)
    SPR["mushroom_small"] = makeMushroom(18)

    ball = makeBall(9)
    SPR["ball"] = ball
    trail = []
    for i in range(5):
        size = int(ball.get_width() * (0.35 + 0.12 * i))
        t = pygame.transform.smoothscale(ball, (size, size))
        t.set_alpha(35 + i * 18)
        trail.append(t)
    SPR["trail"] = trail

    SPR["bg"] = makeBackground()
    SPR["ground"] = makeGround()
    SPR["clouds"] = [makeCloud(1.0), makeCloud(0.7)]

    # ----------------------------------------------------------------- objects
class Paddle:
    HEIGHT = 24
    Y = 425

    def __init__(self):
        self.width = 100
        self.speed = 9.0
        self.x = (WIDTH - self.width) / 2
        self.cache = {}

    def sprites(self):
        if self.width not in self.cache:
            shadow = pygame.Surface((self.width, 10), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, 80), (0, 0, self.width, 10))
            self.cache[self.width] = (makePipe(self.width), shadow)
        return self.cache[self.width]

    def getRect(self):
        return pygame.Rect(int(self.x), self.Y, self.width, self.HEIGHT)

    def clamp(self):
        self.x = max(0, min(WIDTH - self.width, self.x))

    def move(self, direction):
        self.x += direction * self.speed
        self.clamp()

    def setCenter(self, cx):
        self.x = cx - self.width / 2
        self.clamp()

    def setWidth(self, w):
        cx = self.x + self.width / 2
        self.width = w
        self.x = cx - w / 2
        self.clamp()

    def draw(self, surf):
        surf.blit(self.sprites()[0], (int(self.x), self.Y))

    def drawShadow(self, surf):
        surf.blit(self.sprites()[1], (int(self.x), GROUND_Y + 2))


class Block:
    HEALTH = {"brick": 1, "question": 2, "hard": 3}

    def __init__(self, x, y, kind):
        self.rect = pygame.Rect(x, y, BLOCK_W, BLOCK_H)
        self.kind = kind
        self.health = self.HEALTH[kind]

    def sprite(self):
        if self.kind == "brick":
            return SPR["brick"]
        if self.kind == "question":
            return SPR["question"] if self.health == 2 else SPR["used"]
        return SPR["hard"][3 - self.health]

    def hit(self):
        self.health -= 1

    def isDestroyed(self):
        return self.health <= 0

    def draw(self, surf):
        surf.blit(SPR["shadow"], (self.rect.x + 4, self.rect.y + 5))
        surf.blit(self.sprite(), self.rect)


class Ball:
    def __init__(self):
        self.radius = 9
        self.speed = 5.0
        self.posx = self.posy = 0.0
        self.xFac, self.yFac = 0.7, -1
        self.trail = []

    def attach(self, prect):
        self.posx = prect.centerx
        self.posy = prect.top - self.radius - 1
        self.xFac = random.choice([-0.7, 0.7])
        self.yFac = -1
        self.trail = []

    def update(self):
        self.trail.append((self.posx, self.posy))
        self.trail = self.trail[-5:]

        self.posx += self.xFac * self.speed
        self.posy += self.yFac * self.speed

        if self.posx <= self.radius:
            self.posx = self.radius
            self.xFac = abs(self.xFac)
        elif self.posx >= WIDTH - self.radius:
            self.posx = WIDTH - self.radius
            self.xFac = -abs(self.xFac)

        if self.posy <= TOP + self.radius:
            self.posy = TOP + self.radius
            self.yFac = abs(self.yFac)

    def getRect(self):
        return pygame.Rect(int(self.posx - self.radius),
                           int(self.posy - self.radius),
                           self.radius * 2, self.radius * 2)

    # Bounce angle depends on where the ball hits the pipe
    def bounceOffPaddle(self, prect):
        offset = (self.posx - prect.centerx) / (prect.width / 2)
        offset = max(-1, min(1, offset))
        self.xFac = offset * 1.3
        if abs(self.xFac) < 0.2:
            self.xFac = 0.2 if self.xFac >= 0 else -0.2
        self.yFac = -1
        self.posy = prect.top - self.radius - 1

    # Bounce on the side that was hit and push the ball out of the block
    def bounceOffBlock(self, brect):
        r = self.getRect()
        overlapX = min(r.right, brect.right) - max(r.left, brect.left)
        overlapY = min(r.bottom, brect.bottom) - max(r.top, brect.top)
        if overlapX < overlapY:
            if r.centerx < brect.centerx:
                self.posx -= overlapX
            else:
                self.posx += overlapX
            self.xFac *= -1
        else:
            if r.centery < brect.centery:
                self.posy -= overlapY
            else:
                self.posy += overlapY
            self.yFac *= -1

    def draw(self, surf, launched):
        if launched:
            for i, (tx, ty) in enumerate(self.trail):
                spr = SPR["trail"][i]
                surf.blit(spr, (tx - spr.get_width() / 2,
                                ty - spr.get_height() / 2))
        spr = SPR["ball"]
        surf.blit(spr, (self.posx - spr.get_width() / 2,
                        self.posy - spr.get_height() / 2))


class Mushroom:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.vy = -3.0

    def update(self):
        self.vy = min(3.5, self.vy + 0.12)
        self.y += self.vy

    def getRect(self):
        return pygame.Rect(int(self.x - 13), int(self.y - 13), 26, 26)

    def draw(self, surf):
        surf.blit(SPR["mushroom"], self.getRect())


class Debris:
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-6, -2)
        self.life = 40
        self.color = color
        self.size = random.randint(3, 6)

    def update(self):
        self.vy += 0.35
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, surf):
        pygame.draw.rect(surf, self.color,
                         (int(self.x), int(self.y), self.size, self.size))


class CoinPop:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.vy = -7.0
        self.age = 0
        self.life = 36

    def update(self):
        self.vy += 0.3
        self.y += self.vy
        self.age += 1
        self.life -= 1

    def draw(self, surf):
        w = max(3, int(12 * abs(math.cos(self.age * 0.5))))
        rect = pygame.Rect(0, 0, w, 18)
        rect.center = (int(self.x), int(self.y))
        pygame.draw.ellipse(surf, (160, 110, 0), rect.inflate(2, 2))
        pygame.draw.ellipse(surf, (255, 215, 40), rect)
        pygame.draw.line(surf, (255, 245, 170),
                         (rect.centerx, rect.top + 3),
                         (rect.centerx, rect.bottom - 3), 1)


class FloatText:
    def __init__(self, text, x, y):
        self.text = text
        self.x, self.y = x, y
        self.life = 40

    def update(self):
        self.y -= 1
        self.life -= 1

    def draw(self, surf):
        drawText(surf, self.text, smallFont, WHITE,
                 (int(self.x), int(self.y)), center=True)


# ------------------------------------------------------------------ levels
def makeLevel(level):
    blocks = []
    weightHard = min(8 + level * 4, 35)
    weightQuestion = 16
    weightBrick = 100 - weightHard - weightQuestion
    for row in range(6):
        for col in range(10):
            if random.random() < 0.06:
                continue
            kind = random.choices(["brick", "question", "hard"],
                                  weights=[weightBrick, weightQuestion,
                                           weightHard])[0]
            blocks.append(Block(3 + col * 60, 50 + row * 30, kind))
    if not blocks:
        blocks.append(Block(3, 50, "brick"))
    return blocks


DEBRIS_COLORS = {"brick": (200, 80, 20), "question": (250, 185, 50),
                 "hard": (140, 140, 150)}
POINTS = {"brick": 10, "question": 50, "hard": 30}