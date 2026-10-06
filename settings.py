"""
settings.py - every tunable value of the junction simulation lives here.

Nothing else in the project hard-codes screen sizes, timings, colours or
vehicle parameters, so the whole behaviour can be tuned from this one file.
"""

# --------------------------------------------------------------------------
# Window
# --------------------------------------------------------------------------
SIM_WIDTH = 920                      # simulation (junction) area
SIM_HEIGHT = 720
PANEL_WIDTH = 380                    # dashboard area, kept separate from the simulation
SCREEN_WIDTH = SIM_WIDTH + PANEL_WIDTH
SCREEN_HEIGHT = SIM_HEIGHT
FPS = 60
MAX_DT = 0.05                        # clamp delta time so a lag spike can never teleport vehicles
WINDOW_TITLE = "Intelligent Traffic Junction - Basic Simulation"
AUTO_START = True                    # False -> start paused, press START / SPACE
RANDOM_SEED = None                   # set an int for a repeatable traffic pattern

# --------------------------------------------------------------------------
# Roads
# --------------------------------------------------------------------------
ROAD_IDS = ("A", "B", "C")
ROAD_NAMES = {"A": "ROAD A", "B": "ROAD B", "C": "ROAD C"}

# --------------------------------------------------------------------------
# Traffic signals
# --------------------------------------------------------------------------
RED, YELLOW, GREEN = "RED", "YELLOW", "GREEN"
SIGNAL_SEQUENCE = ("A", "B", "C")    # A -> B -> C -> A -> ...
GREEN_TIME = {"A": 30.0, "B": 30.0, "C": 30.0}   # seconds (fixed for now, RTOS will change later)
YELLOW_TIME = 3.0                    # seconds

# --------------------------------------------------------------------------
# Junction geometry (top-down, pixels)
# --------------------------------------------------------------------------
# Road A (bottom -> top) and Road B (top -> bottom) are the two directions of
# the vertical main road.  Road C joins from the right (T-junction).
LEFT_HAND_TRAFFIC = True             # India drives on the left; False -> right-hand traffic
JUNCTION_CENTER = (340, 310)
LANE_WIDTH = 42                      # one lane per direction
SIDEWALK_WIDTH = 22
STOP_OFFSET = 34                     # junction-box edge -> stop line (zebra crossing sits in between)
CORNER_RADIUS = 16                   # kerb rounding where Road C meets the main road
OFFSCREEN_MARGIN = 40                # vehicles spawn / despawn this far outside the simulation area
CURVE_SAMPLES = 24                   # points used to sample a turning path

# --------------------------------------------------------------------------
# Vehicles
# --------------------------------------------------------------------------
# length / width in px, speed range in px/s, accel & brake in px/s^2,
# weight = relative probability of being spawned
VEHICLE_TYPES = {
    "car":   {"length": 32, "width": 17, "speed": (105, 130), "accel": 95,  "brake": 230, "weight": 52},
    "suv":   {"length": 37, "width": 19, "speed": (100, 125), "accel": 85,  "brake": 220, "weight": 16},
    "bike":  {"length": 24, "width": 10, "speed": (115, 140), "accel": 130, "brake": 260, "weight": 12},
    "truck": {"length": 56, "width": 21, "speed": (85, 105),  "accel": 50,  "brake": 170, "weight": 11},
    "bus":   {"length": 62, "width": 22, "speed": (85, 100),  "accel": 55,  "brake": 170, "weight": 9},
}
VEHICLE_COLORS = [
    (200, 52, 52), (46, 110, 200), (236, 236, 232), (170, 175, 182), (44, 44, 50),
    (232, 190, 44), (52, 150, 92), (226, 126, 42), (44, 160, 170), (132, 84, 172),
]
BUS_COLORS = [(226, 168, 36), (196, 60, 52), (52, 112, 190)]

MIN_GAP = 7                          # bumper-to-bumper distance kept when stopped (px)
STOP_MARGIN = 3                      # front bumper stops this far before the stop line (px)
LOOKAHEAD = 150                      # how far ahead a vehicle looks for a leader (px)
LATERAL_MARGIN = 6                   # extra side clearance when deciding "is that vehicle in my way"
COMFORT_BRAKE = 0.8                  # fraction of a vehicle's brake used for normal stopping
HARD_BRAKE = 520                     # max deceleration when a target speed drops suddenly (px/s^2)
TURN_SPEED = 50                      # speed cap while turning (px/s)
QUEUE_SPEED_THRESHOLD = 6            # slower than this (px/s) before the stop line = "queued"

# --------------------------------------------------------------------------
# Traffic generation: (min, max) seconds between new vehicles on each road
# --------------------------------------------------------------------------
SPAWN_INTERVAL = {"A": (4.0, 9.0), "B": (5.0, 10.0), "C": (3.0, 8.0)}
SPAWN_CLEARANCE = 6                  # extra free space needed at the entrance before spawning
C_LEFT_TURN_PROBABILITY = 0.5        # Road C vehicles turn left (south) or right (north)

# --------------------------------------------------------------------------
# Colours
# --------------------------------------------------------------------------
COLOR_GROUND = (46, 78, 54)
COLOR_BLOCK = (60, 98, 64)
COLOR_SIDEWALK = (170, 170, 162)
COLOR_KERB = (112, 112, 106)
COLOR_ASPHALT = (54, 56, 60)
COLOR_LINE_WHITE = (232, 232, 226)
COLOR_LINE_YELLOW = (228, 192, 54)
COLOR_SIGNAL = {RED: (228, 56, 56), YELLOW: (247, 193, 38), GREEN: (48, 206, 102)}

COLOR_PANEL_BG = (21, 25, 32)
COLOR_CARD_BG = (31, 37, 47)
COLOR_TEXT = (232, 236, 242)
COLOR_TEXT_MUTED = (140, 150, 166)
COLOR_ACCENT = (86, 156, 255)
COLOR_BUTTON = (44, 52, 66)
COLOR_BUTTON_HOVER = (60, 70, 88)
