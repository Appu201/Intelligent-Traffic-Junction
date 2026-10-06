"""
vehicle.py - vehicle behaviour (car-following, stopping at signals) and drawing.

Each vehicle follows a Path (see road.py) and only stores its arc-length
position ``s`` and its ``speed``.  Every frame it decides a target speed from:

  1. the vehicle ahead      -> keep a safe gap, never overlap
  2. the signal             -> stop at the stop line on RED; on YELLOW decide once: stop, or go if it
                               cannot stop comfortably and will clear the line before RED
  3. the junction itself    -> do not enter while a vehicle of another road is still inside
  4. turning                -> slow down in the curve

and then accelerates / brakes smoothly towards it.  Movement is always
``speed * dt`` so nothing teleports and frame-rate changes do not matter.
"""
import math

import pygame

import settings as cfg


# --------------------------------------------------------------------------
# Sprites
# --------------------------------------------------------------------------
def _shade(color, factor):
    return tuple(max(0, min(255, int(c * factor))) for c in color)


def _lights(surf, L, W, head, tail, single=False):
    """Headlights at the front (+x) and brake lights at the rear (x = 0)."""
    if single:
        pygame.draw.rect(surf, head, (L - 2, W // 2 - 1, 2, 2))
        pygame.draw.rect(surf, tail, (0, W // 2 - 1, 2, 2))
        return
    pygame.draw.rect(surf, head, (L - 3, 1, 3, 4), border_radius=1)
    pygame.draw.rect(surf, head, (L - 3, W - 5, 3, 4), border_radius=1)
    pygame.draw.rect(surf, tail, (0, 1, 3, 4), border_radius=1)
    pygame.draw.rect(surf, tail, (0, W - 5, 3, 4), border_radius=1)


def build_sprite(vtype, color, length, width, braking):
    """Top-down sprite facing +x (to the right); rotated later to the path heading."""
    L, W = int(length), int(width)
    surf = pygame.Surface((L, W), pygame.SRCALPHA)
    glass = (26, 38, 56)
    head = (255, 245, 192)
    tail = (255, 56, 46) if braking else (122, 24, 24)

    if vtype == "bike":
        pygame.draw.ellipse(surf, (28, 28, 32), (0, 1, L, max(2, W - 2)))
        pygame.draw.ellipse(surf, color, (int(L * 0.28), 0, int(L * 0.42), W))
        pygame.draw.circle(surf, (22, 22, 26), (int(L * 0.52), W // 2), max(2, W // 4))
        _lights(surf, L, W, head, tail, single=True)

    elif vtype == "truck":
        cab_len = int(L * 0.30)
        trailer = pygame.Rect(0, 0, L - cab_len - 2, W)
        pygame.draw.rect(surf, (208, 211, 215), trailer, border_radius=2)
        pygame.draw.rect(surf, (118, 122, 128), trailer, 1, border_radius=2)
        for x in range(8, trailer.right - 3, 9):
            pygame.draw.line(surf, (170, 174, 180), (x, 2), (x, W - 3), 1)
        cab = pygame.Rect(L - cab_len, 1, cab_len, W - 2)
        pygame.draw.rect(surf, color, cab, border_radius=4)
        pygame.draw.rect(surf, _shade(color, 0.55), cab, 1, border_radius=4)
        pygame.draw.rect(surf, glass, (L - int(cab_len * 0.48), 3, int(cab_len * 0.30), W - 6), border_radius=2)
        _lights(surf, L, W, head, tail)

    elif vtype == "bus":
        body = pygame.Rect(0, 0, L, W)
        pygame.draw.rect(surf, color, body, border_radius=5)
        pygame.draw.rect(surf, _shade(color, 0.55), body, 1, border_radius=5)
        pygame.draw.rect(surf, _shade(color, 1.18), (6, 3, L - 22, W - 6), border_radius=3)
        for x in (int(L * 0.25), int(L * 0.55)):
            pygame.draw.rect(surf, _shade(color, 0.8), (x, W // 2 - 3, 12, 6), border_radius=2)
        pygame.draw.rect(surf, glass, (L - 11, 2, 7, W - 4), border_radius=2)
        pygame.draw.rect(surf, glass, (3, 3, 3, W - 6), border_radius=1)
        _lights(surf, L, W, head, tail)

    else:  # car / suv
        suv = vtype == "suv"
        body = pygame.Rect(0, 0, L, W)
        pygame.draw.rect(surf, color, body, border_radius=5)
        pygame.draw.rect(surf, _shade(color, 0.55), body, 1, border_radius=5)
        wind_x = 0.64 if suv else 0.60
        rear_x = 0.10 if suv else 0.14
        pygame.draw.rect(surf, glass, (int(L * wind_x), 2, int(L * 0.18), W - 4), border_radius=2)
        pygame.draw.rect(surf, glass, (int(L * rear_x), 2, int(L * 0.14), W - 4), border_radius=2)
        roof_x0 = int(L * (rear_x + 0.14))
        pygame.draw.rect(surf, _shade(color, 1.16), (roof_x0, 3, int(L * wind_x) - roof_x0, W - 6), border_radius=2)
        _lights(surf, L, W, head, tail)

    return surf


# --------------------------------------------------------------------------
# Vehicle
# --------------------------------------------------------------------------
class Vehicle:
    _counter = 0

    def __init__(self, vtype, color, path, origin, turn, rng):
        spec = cfg.VEHICLE_TYPES[vtype]
        self.id = Vehicle._counter
        Vehicle._counter += 1

        self.vtype = vtype
        self.color = color
        self.path = path
        self.origin = origin            # road id the vehicle entered from ("A", "B", "C")
        self.turn = turn                # "straight", "left" or "right"

        self.length = spec["length"]
        self.width = spec["width"]
        self.max_speed = rng.uniform(*spec["speed"])
        self.accel = spec["accel"]
        self.brake = spec["brake"] * cfg.COMFORT_BRAKE      # comfortable deceleration

        self.s = 0.0                    # arc-length position of the vehicle centre
        self.speed = self.max_speed * 0.6
        self.x, self.y, self.hx, self.hy = path.at(0.0)

        self.crossed = False            # front has passed the stop line
        self.cleared = False            # rear has left the junction box
        self.finished = False           # left the screen -> remove
        self.counted = False            # already added to the "passed" statistic
        self.decision = None            # yellow-light decision: None / "stop" / "go"
        self.braking = False
        self.cross_state = None         # signal state at the moment the stop line was crossed

        self._sprites = {}

    # ------------------------------------------------------------------ queries
    def in_junction(self):
        return self.crossed and not self.cleared

    def is_queued(self):
        return (not self.crossed) and self.speed < cfg.QUEUE_SPEED_THRESHOLD

    # ------------------------------------------------------------------ behaviour
    def _find_leader(self, vehicles):
        """Nearest vehicle ahead, moving the same way and overlapping my lane."""
        best_f, leader = None, None
        hx, hy = self.hx, self.hy
        reach = cfg.LOOKAHEAD
        for u in vehicles:
            if u is self or u.finished:
                continue
            dx, dy = u.x - self.x, u.y - self.y
            if dx > reach or dx < -reach or dy > reach or dy < -reach:
                continue
            f = dx * hx + dy * hy                       # distance ahead along my heading
            if f <= 0.0 or f > reach:
                continue
            if hx * u.hx + hy * u.hy < 0.2:             # oncoming / crossing traffic is not a leader
                continue
            lateral = abs(dx * hy - dy * hx)
            if lateral > (self.width + u.width) / 2.0 + cfg.LATERAL_MARGIN:
                continue
            if best_f is None or f < best_f:
                best_f, leader = f, u
        if leader is None:
            return None, None
        return leader, best_f - (self.length + leader.length) / 2.0

    def _junction_busy(self, vehicles):
        """True while a vehicle of another road is still inside the junction box."""
        for u in vehicles:
            if u is not self and u.origin != self.origin and u.in_junction():
                return True
        return False

    def _decide_on_yellow(self, dist, leader, traffic):
        """Made ONCE, the moment my signal turns YELLOW: "stop" or "go".

        Go only if I could not stop comfortably AND will reach the stop line
        before the yellow ends (0.5 s safety margin).  Otherwise stop - so a
        vehicle can never slip through just after the signal turned RED.
        """
        if dist >= self.speed ** 2 / (2.0 * self.brake):
            return "stop"                                       # can stop comfortably
        if leader is not None and not leader.crossed and leader.decision != "go":
            return "stop"                                       # the vehicle ahead is stopping, so am I
        time_to_line = dist / max(self.speed, 1.0)
        if time_to_line <= traffic.get_remaining_time(self.origin) - 0.5:
            return "go"
        return "stop"

    def _stop_distance(self, vehicles, leader, traffic):
        """Distance to the point where I must stop, or None if I may go."""
        if self.crossed:
            return None
        dist = max(self.path.s_stop - cfg.STOP_MARGIN - (self.s + self.length / 2.0), 0.0)
        state = traffic.get_signal_state(self.origin)

        if state == cfg.GREEN:
            self.decision = None
            return dist if self._junction_busy(vehicles) else None

        if self.decision == "go":                       # committed on yellow: clear the junction
            return None

        if state == cfg.YELLOW and self.decision is None:
            self.decision = self._decide_on_yellow(dist, leader, traffic)
            if self.decision == "go":
                return None

        return dist                                     # RED, or YELLOW with decision "stop"

    def update(self, dt, vehicles, traffic):
        """Advance by dt seconds. ``traffic`` is the TrafficManager (signal state / remaining time)."""
        if dt <= 0.0:
            return

        target = self.max_speed
        max_advance = float("inf")                      # hard limit: never overlap / never cross a red line
        waiting = False

        leader, gap = self._find_leader(vehicles)
        if leader is not None:
            free = max(gap - cfg.MIN_GAP, 0.0)
            # speed from which I can still match the leader's speed after `free` pixels
            target = min(target, math.sqrt(leader.speed ** 2 + 2.0 * self.brake * free))
            max_advance = min(max_advance, free)
            waiting = True

        stop_dist = self._stop_distance(vehicles, leader, traffic)
        if stop_dist is not None:
            target = min(target, math.sqrt(2.0 * self.brake * stop_dist))
            max_advance = min(max_advance, stop_dist)
            waiting = True

        if self.turn != "straight":
            front = self.s + self.length / 2.0
            rear = self.s - self.length / 2.0
            if front > self.path.s_stop - 30.0 and rear < self.path.s_zone_end:
                target = min(target, cfg.TURN_SPEED)

        previous = self.speed
        if self.speed < target:
            self.speed = min(target, self.speed + self.accel * dt)
        else:
            self.speed = max(target, self.speed - cfg.HARD_BRAKE * dt)

        step = self.speed * dt
        if step > max_advance:                          # blocked: real speed is what we actually moved
            step = max_advance
            self.speed = step / dt
        if self.speed < 0.5 and waiting and stop_dist is not None and stop_dist < 0.5:
            self.speed = 0.0

        self.s += step
        self.x, self.y, self.hx, self.hy = self.path.at(self.s)

        self.braking = (previous - self.speed) / dt > 25.0 or (self.speed < 2.0 and waiting)

        front = self.s + self.length / 2.0
        if not self.crossed and front > self.path.s_stop:
            self.crossed = True
            self.cross_state = traffic.get_signal_state(self.origin)
        if self.crossed and not self.cleared and self.s - self.length / 2.0 >= self.path.s_zone_end:
            self.cleared = True
        if self.s >= self.path.length - 0.5:
            self.finished = True

    # ------------------------------------------------------------------ drawing
    def _sprite(self, braking):
        key = bool(braking)
        if key not in self._sprites:
            self._sprites[key] = build_sprite(self.vtype, self.color, self.length, self.width, key)
        return self._sprites[key]

    def draw(self, surface):
        angle = math.degrees(math.atan2(-self.hy, self.hx))
        img = pygame.transform.rotozoom(self._sprite(self.braking), angle, 1.0)
        surface.blit(img, img.get_rect(center=(int(self.x), int(self.y))))
