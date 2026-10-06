"""
road.py - roads, lanes and the poly-line paths vehicles follow.

A Path is parametrised by arc length ``s`` (pixels from the start of the path),
so a vehicle only has to remember a single number to know where it is.
"""
import bisect
import math
from dataclasses import dataclass


class Path:
    """Poly-line followed by a vehicle.

    s_stop      arc length of the stop line on this path
    s_zone_end  arc length where the path leaves the junction box
                (between s_stop and s_zone_end a vehicle is "inside the junction")
    """

    def __init__(self, points):
        pts = []
        for x, y in points:
            p = (float(x), float(y))
            if not pts or math.hypot(p[0] - pts[-1][0], p[1] - pts[-1][1]) > 1e-6:
                pts.append(p)          # drop duplicate points -> no zero-length segments
        self.points = pts
        self.cum = [0.0]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            self.cum.append(self.cum[-1] + math.hypot(x1 - x0, y1 - y0))
        self.length = self.cum[-1]
        self.s_stop = 0.0
        self.s_zone_end = self.length

    def mark(self, stop_index, exit_index):
        """Record which polyline vertices are the stop line and the junction exit."""
        self.s_stop = self.cum[stop_index]
        self.s_zone_end = self.cum[exit_index]

    def at(self, s):
        """Return (x, y, heading_x, heading_y) at arc length s."""
        s = max(0.0, min(s, self.length))
        i = bisect.bisect_right(self.cum, s) - 1
        i = min(i, len(self.points) - 2)
        x0, y0 = self.points[i]
        x1, y1 = self.points[i + 1]
        seg = self.cum[i + 1] - self.cum[i]
        t = (s - self.cum[i]) / seg
        return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, (x1 - x0) / seg, (y1 - y0) / seg


@dataclass(frozen=True)
class Lane:
    """Inbound lane of a road: from where vehicles appear to the stop line."""
    start: tuple         # off-screen spawn point (lane centre)
    stop: tuple          # lane centre at the stop line
    direction: tuple     # unit vector of travel
    width: float

    @property
    def approach_length(self):
        return math.hypot(self.stop[0] - self.start[0], self.stop[1] - self.start[1])


@dataclass
class Road:
    """One approach road of the junction (A, B or C) and its signal placement."""
    road_id: str
    name: str
    lane: Lane
    stop_line: tuple             # ((x1, y1), (x2, y2)) painted across the inbound lane
    signal_pos: tuple            # centre of the signal head
    signal_horizontal: bool      # lamps laid out horizontally (side road) or vertically
    timer_offset: tuple          # where the countdown tag sits relative to the head

    def queue_capacity(self, vehicle_pitch=40.0):
        """Rough number of cars that fit between the screen edge and the stop line."""
        return int(self.lane.approach_length // vehicle_pitch)
