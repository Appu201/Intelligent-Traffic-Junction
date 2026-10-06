"""
vehicle_generator.py - creates vehicles at the three road entrances.

Each road has its own random timer (see SPAWN_INTERVAL in settings.py).
A vehicle is only created when the entrance is free, so a long queue simply
stops new vehicles from appearing instead of stacking them on top of each other.
"""
import random

import settings as cfg
from vehicle import Vehicle


class VehicleGenerator:
    def __init__(self, intersection, vehicles):
        self.intersection = intersection
        self.vehicles = vehicles
        self.rng = random.Random(cfg.RANDOM_SEED)
        self._types = list(cfg.VEHICLE_TYPES)
        self._weights = [cfg.VEHICLE_TYPES[t]["weight"] for t in self._types]
        self.timers = {}
        self.reset()

    def reset(self):
        # first vehicles appear quickly, then at the configured pace
        self.timers = {rid: self.rng.uniform(0.3, 2.0) for rid in cfg.ROAD_IDS}

    def update(self, dt):
        for rid in cfg.ROAD_IDS:
            self.timers[rid] -= dt
            if self.timers[rid] > 0.0:
                continue
            if self._spawn(rid):
                self.timers[rid] = self.rng.uniform(*cfg.SPAWN_INTERVAL[rid])
            else:
                self.timers[rid] = 0.4                      # entrance busy -> try again shortly

    def _spawn(self, road_id):
        if road_id == "C":
            turn = "left" if self.rng.random() < cfg.C_LEFT_TURN_PROBABILITY else "right"
        else:
            turn = "straight"
        path = self.intersection.get_path(road_id, turn)

        vtype = self.rng.choices(self._types, self._weights)[0]
        spec = cfg.VEHICLE_TYPES[vtype]

        # entrance must be free: the nearest vehicle's rear bumper has to be a safe distance
        # from where the new vehicle's front bumper will be
        for v in self.vehicles:
            if v.origin == road_id and v.s - v.length / 2 - spec["length"] / 2 < cfg.MIN_GAP + cfg.SPAWN_CLEARANCE:
                return False

        palette = cfg.BUS_COLORS if vtype == "bus" else cfg.VEHICLE_COLORS
        color = self.rng.choice(palette)
        self.vehicles.append(Vehicle(vtype, color, path, road_id, turn, self.rng))
        return True
