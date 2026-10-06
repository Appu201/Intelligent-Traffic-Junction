"""
traffic_manager.py - signal sequencing + the traffic-information API.

Signal cycle (fixed timing for now):

    Road A: GREEN 30 s -> YELLOW 3 s -> RED
    Road B: GREEN 30 s -> YELLOW 3 s -> RED
    Road C: GREEN 30 s -> YELLOW 3 s -> RED      ... then back to Road A

Only the *active* road is ever non-RED, so two roads can never be GREEN (or
GREEN + YELLOW) at the same time.

Public API (also exposed as module-level functions at the bottom of this
file) - this is what the future TCP / QNX RTOS link will call:

    get_vehicle_count(road_id)      vehicles currently on the road (approach + inside junction)
    get_queue_length(road_id)       vehicles stopped / crawling before the stop line
    get_signal_state(road_id)       "RED" | "YELLOW" | "GREEN"
    get_remaining_time(road_id)     seconds left in the current state (RED: until it turns GREEN)
    set_signal(road_id, state)      external control hook (safety-checked, see docstring)
"""
import math

import settings as cfg
from traffic_signal import TrafficSignal


class TrafficManager:
    def __init__(self, vehicles):
        self.vehicles = vehicles                     # shared list owned by the Simulation
        self.signals = {rid: TrafficSignal(rid) for rid in cfg.ROAD_IDS}
        self.sequence = list(cfg.SIGNAL_SEQUENCE)
        self.green_time = dict(cfg.GREEN_TIME)
        self.yellow_time = cfg.YELLOW_TIME
        self.manual_mode = False                     # True while an external controller drives the signals

        self.index = 0
        self.phase = cfg.GREEN
        self.phase_total = 0.0
        self.phase_left = 0.0
        self.sim_time = 0.0
        self.passed = {rid: 0 for rid in cfg.ROAD_IDS}

        self.reset()
        register_manager(self)

    # ------------------------------------------------------------------ lifecycle
    def reset(self):
        """Road A GREEN with a full timer, B and C RED, statistics cleared."""
        self.manual_mode = False
        self.index = 0
        self.phase = cfg.GREEN
        self.phase_total = self.phase_left = self.green_time[self.sequence[0]]
        self.sim_time = 0.0
        self.passed = {rid: 0 for rid in cfg.ROAD_IDS}
        self._sync_signals()

    def update(self, dt):
        """Advance the simulation clock and the signal cycle by dt seconds."""
        self.sim_time += dt
        if self.manual_mode:
            return
        self.phase_left -= dt
        while self.phase_left <= 0.0:                # while-loop: survives a long frame
            overflow = -self.phase_left
            self._next_phase()
            self.phase_left -= overflow
        self._sync_signals()

    def _next_phase(self):
        if self.phase == cfg.GREEN:                  # GREEN -> YELLOW (same road)
            self.phase = cfg.YELLOW
            self.phase_total = self.phase_left = self.yellow_time
        else:                                        # YELLOW -> next road GREEN, this road RED
            self.index = (self.index + 1) % len(self.sequence)
            self.phase = cfg.GREEN
            self.phase_total = self.phase_left = self.green_time[self.sequence[self.index]]

    def _sync_signals(self):
        active = self.sequence[self.index]
        for rid, sig in self.signals.items():
            sig.state = self.phase if rid == active else cfg.RED
            sig.remaining = self._remaining(rid)

    def _remaining(self, road_id):
        active = self.sequence[self.index]
        if road_id == active:
            return max(self.phase_left, 0.0)
        # RED road: time until its GREEN starts
        t = self.phase_left
        if self.phase == cfg.GREEN:
            t += self.yellow_time
        n = len(self.sequence)
        steps = (self.sequence.index(road_id) - self.index) % n
        for k in range(1, steps):
            t += self.green_time[self.sequence[(self.index + k) % n]] + self.yellow_time
        return t

    def record_passed(self, road_id):
        self.passed[road_id] += 1

    # ------------------------------------------------------------------ signal info
    @property
    def active_road(self):
        return self.sequence[self.index]

    def get_signal_state(self, road_id):
        return self.signals[road_id].state

    def get_remaining_time(self, road_id):
        """Seconds left in the road's current state (RED: seconds until GREEN)."""
        return self.signals[road_id].remaining

    def get_remaining_seconds(self, road_id):
        """Same as above, as the whole-second countdown shown on screen (30 ... 1)."""
        return self.signals[road_id].countdown

    def get_phase_progress(self):
        """Fraction of the current GREEN/YELLOW phase that is left (1.0 -> 0.0)."""
        return self.phase_left / self.phase_total if self.phase_total else 0.0

    def set_green_time(self, road_id, seconds):
        """Change a road's GREEN duration (used later when the RTOS decides the timing)."""
        self.green_time[road_id] = float(seconds)

    # ------------------------------------------------------------------ external control hook
    def set_signal(self, road_id, state, duration=None):
        """Force one road's signal (for the future QNX RTOS link).

        Safety interlock: GREEN / YELLOW is refused (returns False) while any
        other road is not RED, so conflicting greens are impossible.  A
        successful call switches the manager to manual mode: the automatic
        30/3 s cycle pauses until resume_auto() is called.
        """
        if road_id not in self.signals or state not in (cfg.RED, cfg.YELLOW, cfg.GREEN):
            return False
        if state != cfg.RED and any(r != road_id and s.state != cfg.RED for r, s in self.signals.items()):
            return False
        self.manual_mode = True
        sig = self.signals[road_id]
        sig.state = state
        sig.remaining = float(duration) if duration is not None else 0.0
        return True

    def resume_auto(self):
        """Hand control back to the automatic cycle (continues from the non-RED road, else restarts at A)."""
        active = [rid for rid, s in self.signals.items() if s.state != cfg.RED]
        if active:
            rid = active[0]
            self.index = self.sequence.index(rid)
            self.phase = self.signals[rid].state
            self.phase_left = self.signals[rid].remaining or (
                self.yellow_time if self.phase == cfg.YELLOW else self.green_time[rid])
            self.phase_total = self.yellow_time if self.phase == cfg.YELLOW else self.green_time[rid]
        else:
            self.index = 0
            self.phase = cfg.GREEN
            self.phase_total = self.phase_left = self.green_time[self.sequence[0]]
        self.manual_mode = False
        self._sync_signals()

    # ------------------------------------------------------------------ traffic info
    def get_vehicle_count(self, road_id):
        """Vehicles of this road that have not yet fully cleared the junction."""
        return sum(1 for v in self.vehicles if v.origin == road_id and not v.cleared)

    def get_queue_length(self, road_id):
        """Vehicles of this road standing (or crawling) in front of the stop line."""
        return sum(1 for v in self.vehicles if v.origin == road_id and v.is_queued())

    def get_total_vehicles(self):
        return sum(self.get_vehicle_count(rid) for rid in cfg.ROAD_IDS)

    def get_total_passed(self):
        return sum(self.passed.values())

    def get_traffic_snapshot(self):
        """One dict with everything the RTOS side will need, e.g. for a JSON message."""
        return {
            "time": round(self.sim_time, 2),
            "active_road": self.active_road,
            "roads": {
                rid: {
                    "vehicles": self.get_vehicle_count(rid),
                    "queue": self.get_queue_length(rid),
                    "signal": self.get_signal_state(rid),
                    "remaining": round(self.get_remaining_time(rid), 2),
                    "passed": self.passed[rid],
                }
                for rid in cfg.ROAD_IDS
            },
        }


# --------------------------------------------------------------------------
# Module-level API: thin wrappers around the running TrafficManager so other
# code (e.g. a TCP server thread) can simply `from traffic_manager import ...`.
# --------------------------------------------------------------------------
_manager = None


def register_manager(manager):
    global _manager
    _manager = manager


def _require():
    if _manager is None:
        raise RuntimeError("No TrafficManager has been created yet")
    return _manager


def get_vehicle_count(road_id):
    return _require().get_vehicle_count(road_id)


def get_queue_length(road_id):
    return _require().get_queue_length(road_id)


def get_signal_state(road_id):
    return _require().get_signal_state(road_id)


def get_remaining_time(road_id):
    return _require().get_remaining_time(road_id)


def set_signal(road_id, state, duration=None):
    return _require().set_signal(road_id, state, duration)
