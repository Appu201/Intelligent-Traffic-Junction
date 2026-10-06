"""
intersection.py - junction geometry, vehicle paths and the static scene.

Layout (top-down, default left-hand traffic):

                 Road B (enters at the top, travels down)
                          |  |
                          |  |
           ---------------+--+---------------
                          [  ]        Road C (enters from the right,
           ---------------+--+---------    turns left/right onto the main road)
                          |  |
                          |  |
                 Road A (enters at the bottom, travels up)

Road A and Road B are the two directions of the main road; Road C is the
side road of the T-junction.  Because there is no road on the left, Road C
vehicles "continue through the junction" by turning onto the main road
(left -> towards the bottom, right -> towards the top).
"""
import random

import pygame

import settings as cfg
from road import Lane, Path, Road


class Intersection:
    def __init__(self):
        cx, cy = cfg.JUNCTION_CENTER
        lw = cfg.LANE_WIDTH
        side = -1 if cfg.LEFT_HAND_TRAFFIC else 1

        self.cx, self.cy, self.lw, self.side = cx, cy, lw, side
        self.box = pygame.Rect(cx - lw, cy - lw, 2 * lw, 2 * lw)      # the junction box

        # centre lines of the lanes (northbound = Road A, southbound = Road B, westbound = Road C)
        self.north_x = cx + side * lw / 2
        self.south_x = cx - side * lw / 2
        self.west_y = cy - side * lw / 2

        self.roads = {}
        self.paths = {}
        self._build_roads()
        self._build_paths()
        self.background = self._render_background()

    # ------------------------------------------------------------------ roads
    def _build_roads(self):
        W, H = cfg.SIM_WIDTH, cfg.SIM_HEIGHT
        m, sw, lw, s = cfg.OFFSCREEN_MARGIN, cfg.SIDEWALK_WIDTH, self.lw, self.side
        box, cx, cy = self.box, self.cx, self.cy

        a_stop = box.bottom + cfg.STOP_OFFSET
        self.roads["A"] = Road(
            "A", cfg.ROAD_NAMES["A"],
            Lane((self.north_x, H + m), (self.north_x, a_stop), (0, -1), lw),
            ((self.north_x - lw / 2, a_stop), (self.north_x + lw / 2, a_stop)),
            (cx + s * (lw + sw / 2), a_stop + 40), False, (s * 40, 0))

        b_stop = box.top - cfg.STOP_OFFSET
        self.roads["B"] = Road(
            "B", cfg.ROAD_NAMES["B"],
            Lane((self.south_x, -m), (self.south_x, b_stop), (0, 1), lw),
            ((self.south_x - lw / 2, b_stop), (self.south_x + lw / 2, b_stop)),
            (cx - s * (lw + sw / 2), b_stop - 40), False, (-s * 40, 0))

        c_stop = box.right + cfg.STOP_OFFSET
        self.roads["C"] = Road(
            "C", cfg.ROAD_NAMES["C"],
            Lane((W + m, self.west_y), (c_stop, self.west_y), (-1, 0), lw),
            ((c_stop, self.west_y - lw / 2), (c_stop, self.west_y + lw / 2)),
            (c_stop + 40, cy - s * (lw + sw / 2)), True, (0, -s * 30))

    # ------------------------------------------------------------------ paths
    @staticmethod
    def _bezier(p0, p1, p2, samples):
        pts = []
        for i in range(1, samples + 1):
            t = i / samples
            u = 1.0 - t
            pts.append((u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                        u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]))
        return pts

    def _build_paths(self):
        W, H, m = cfg.SIM_WIDTH, cfg.SIM_HEIGHT, cfg.OFFSCREEN_MARGIN
        box = self.box
        a, b, c = self.roads["A"], self.roads["B"], self.roads["C"]

        # Road A: bottom -> top, straight through
        p = Path([a.lane.start, a.lane.stop, (self.north_x, box.top), (self.north_x, -m)])
        p.mark(1, 2)
        self.paths[("A", "straight")] = p

        # Road B: top -> bottom, straight through
        p = Path([b.lane.start, b.lane.stop, (self.south_x, box.bottom), (self.south_x, H + m)])
        p.mark(1, 2)
        self.paths[("B", "straight")] = p

        # Road C: right -> left, then turn onto the main road
        wy = self.west_y
        entry = (box.right, wy)
        for turn, exit_x, exit_y, end_y in (
            ("left", self.south_x, box.bottom, H + m),     # heading west, left = south
            ("right", self.north_x, box.top, -m),          # heading west, right = north
        ):
            curve = self._bezier(entry, (exit_x, wy), (exit_x, exit_y), cfg.CURVE_SAMPLES)
            pts = [c.lane.start, c.lane.stop, entry] + curve + [(exit_x, end_y)]
            p = Path(pts)
            p.mark(1, len(pts) - 2)                        # vertex before the final off-screen point
            self.paths[("C", turn)] = p

    def get_path(self, road_id, turn="straight"):
        return self.paths[(road_id, turn)]

    # ------------------------------------------------------------------ dynamic drawing
    def draw_signals(self, surface, signals, font):
        for rid, road in self.roads.items():
            signals[rid].draw(surface, road.signal_pos, road.signal_horizontal, road.timer_offset, font)

    # ------------------------------------------------------------------ static scene
    @staticmethod
    def _dashed(surf, color, p0, p1, dash=22, gap=18, width=3):
        """Dashed axis-aligned line."""
        (x0, y0), (x1, y1) = p0, p1
        if x0 == x1:
            y = min(y0, y1)
            while y < max(y0, y1):
                pygame.draw.line(surf, color, (x0, y), (x0, min(y + dash, max(y0, y1))), width)
                y += dash + gap
        else:
            x = min(x0, x1)
            while x < max(x0, x1):
                pygame.draw.line(surf, color, (x, y0), (min(x + dash, max(x0, x1)), y0), width)
                x += dash + gap

    @staticmethod
    def _tree(surf, rng, x, y):
        r = rng.randint(9, 15)
        shadow = pygame.Surface((r * 3, r * 3), pygame.SRCALPHA)
        pygame.draw.circle(shadow, (0, 0, 0, 55), (int(r * 1.7), int(r * 1.7)), r)
        surf.blit(shadow, (x - r * 1.5 + 3, y - r * 1.5 + 4))
        g = rng.randint(-14, 14)
        pygame.draw.circle(surf, (34 + g, 92 + g, 50 + g), (x, y), r)
        pygame.draw.circle(surf, (48 + g, 118 + g, 64 + g), (x - r // 3, y - r // 3), int(r * 0.62))

    def _render_background(self):
        W, H = cfg.SIM_WIDTH, cfg.SIM_HEIGHT
        cx, cy, lw, s = self.cx, self.cy, self.lw, self.side
        sw, R = cfg.SIDEWALK_WIDTH, cfg.CORNER_RADIUS
        box = self.box
        rng = random.Random(7)
        surf = pygame.Surface((W, H))
        surf.fill(cfg.COLOR_GROUND)

        main_x0, main_x1 = cx - lw, cx + lw
        side_y0, side_y1 = cy - lw, cy + lw
        main_road = pygame.Rect(main_x0, 0, 2 * lw, H)
        side_road = pygame.Rect(main_x1, side_y0, W - main_x1, 2 * lw)
        walk_main = main_road.inflate(2 * sw, 0)
        walk_side = pygame.Rect(main_x1, side_y0 - sw, W - main_x1, 2 * lw + 2 * sw)

        # --- city blocks (west block with buildings, east blocks with trees)
        blocks = (
            pygame.Rect(0, 0, walk_main.left, H),
            pygame.Rect(walk_main.right, 0, W - walk_main.right, walk_side.top),
            pygame.Rect(walk_main.right, walk_side.bottom, W - walk_main.right, H - walk_side.bottom),
        )
        for blk in blocks:
            surf.fill(cfg.COLOR_BLOCK, blk)
        west = blocks[0]
        y = 18
        while y < H - 70:
            bh = rng.randint(80, 108)
            bw = rng.randint(120, west.width - 40)
            bx = rng.randint(14, west.width - bw - 24)
            shadow = pygame.Surface((bw, bh), pygame.SRCALPHA)
            shadow.fill((0, 0, 0, 60))
            surf.blit(shadow, (bx + 7, y + 7))
            tone = rng.randint(120, 168)
            pygame.draw.rect(surf, (tone, tone - 6, tone - 14), (bx, y, bw, bh), border_radius=3)
            pygame.draw.rect(surf, (tone - 38, tone - 42, tone - 48), (bx + 8, y + 8, bw - 16, bh - 16), 2)
            pygame.draw.rect(surf, (tone - 22, tone - 26, tone - 32), (bx + 14, y + 14, 26, 18))
            y += bh + rng.randint(26, 40)
        for blk in blocks:
            for _ in range(max(4, blk.width * blk.height // 9000)):
                tx = rng.randint(blk.left + 14, blk.right - 14)
                ty = rng.randint(blk.top + 14, blk.bottom - 14)
                if blk is west and tx < west.right - 60 and rng.random() < 0.8:
                    continue                       # keep most of the west block free for buildings
                self._tree(surf, rng, tx, ty)

        # --- sidewalks, kerbs and asphalt
        surf.fill(cfg.COLOR_SIDEWALK, walk_main)
        surf.fill(cfg.COLOR_SIDEWALK, walk_side)
        surf.fill(cfg.COLOR_ASPHALT, main_road)
        surf.fill(cfg.COLOR_ASPHALT, side_road)
        for sx, sy, ex, ey in ((walk_main.left, 0, walk_main.left, H), (walk_main.right - 1, 0, walk_main.right - 1, walk_side.top),
                               (walk_main.right - 1, walk_side.bottom, walk_main.right - 1, H),
                               (walk_side.left, walk_side.top, W, walk_side.top), (walk_side.left, walk_side.bottom - 1, W, walk_side.bottom - 1)):
            pygame.draw.line(surf, cfg.COLOR_KERB, (sx, sy), (ex, ey), 2)

        # rounded kerbs where Road C meets the main road
        for px, py, sy in ((main_x1, side_y0, -1), (main_x1, side_y1, 1)):
            sq = pygame.Rect(px, py - R if sy < 0 else py, R, R)
            surf.fill(cfg.COLOR_ASPHALT, sq)
            surf.set_clip(sq)
            pygame.draw.circle(surf, cfg.COLOR_SIDEWALK, (px + R, py + sy * R), R)
            pygame.draw.circle(surf, cfg.COLOR_KERB, (px + R, py + sy * R), R, 2)
            surf.set_clip(None)

        # asphalt grain
        for rect in (main_road, side_road):
            for _ in range(rect.width * rect.height // 10):
                x = rng.randrange(rect.left, rect.right)
                y = rng.randrange(rect.top, rect.bottom)
                v = rng.randint(-8, 8)
                surf.set_at((x, y), (cfg.COLOR_ASPHALT[0] + v, cfg.COLOR_ASPHALT[1] + v, cfg.COLOR_ASPHALT[2] + v))

        # --- markings
        white, yellow = cfg.COLOR_LINE_WHITE, cfg.COLOR_LINE_YELLOW
        # road-edge lines (broken where the side road opens)
        pygame.draw.line(surf, white, (main_x0 + 4, 0), (main_x0 + 4, H), 2)
        pygame.draw.line(surf, white, (main_x1 - 4, 0), (main_x1 - 4, side_y0 - R), 2)
        pygame.draw.line(surf, white, (main_x1 - 4, side_y1 + R), (main_x1 - 4, H), 2)
        pygame.draw.line(surf, white, (main_x1 + R, side_y0 + 4), (W, side_y0 + 4), 2)
        pygame.draw.line(surf, white, (main_x1 + R, side_y1 - 4), (W, side_y1 - 4), 2)

        # centre lines stop before the zebra crossings
        off = cfg.STOP_OFFSET + 6
        self._dashed(surf, yellow, (cx, 0), (cx, box.top - off))
        self._dashed(surf, yellow, (cx, box.bottom + off), (cx, H))
        self._dashed(surf, yellow, (box.right + off, cy), (W, cy))

        # zebra crossings between the junction box and each stop line
        for x in range(main_x0 + 5, main_x1 - 8, 13):
            pygame.draw.rect(surf, white, (x, box.bottom + 5, 8, 20))
            pygame.draw.rect(surf, white, (x, box.top - 25, 8, 20))
        for y in range(side_y0 + 5, side_y1 - 8, 13):
            pygame.draw.rect(surf, white, (box.right + 5, y, 20, 8))

        # stop lines across each inbound lane
        for road in self.roads.values():
            pygame.draw.line(surf, white, road.stop_line[0], road.stop_line[1], 5)

        # --- road name chips
        font = pygame.font.SysFont("segoeui,helvetica,arial,dejavusans", 15, bold=True)
        chips = (
            ("A", (walk_main.left - 74, H - 26), (0, -1)),
            ("B", (walk_main.right + 74, 26), (0, 1)),
            ("C", (W - 74, walk_side.top - 24), (-1, 0)),
        )
        for rid, (x, y), (dx, dy) in chips:
            img = font.render(cfg.ROAD_NAMES[rid], True, (240, 242, 246))
            rect = img.get_rect(center=(x, y))
            rect.centerx += 8 if dx < 0 else -8              # leave room for the arrow
            bg = rect.inflate(54, 10)
            pygame.draw.rect(surf, (14, 16, 20), bg, border_radius=8)
            pygame.draw.rect(surf, (90, 98, 112), bg, 1, border_radius=8)
            surf.blit(img, rect)
            ax, ay = bg.right - 14, bg.centery
            if dx:
                ax = bg.left + 14 if dx < 0 else bg.right - 14
                pts = [(ax + 5 * dx * -1, ay - 5), (ax + 5 * dx * -1, ay + 5), (ax + 5 * dx, ay)]
            else:
                pts = [(ax - 5, ay + 5 * dy * -1), (ax + 5, ay + 5 * dy * -1), (ax, ay + 5 * dy)]
            pygame.draw.polygon(surf, cfg.COLOR_SIGNAL[cfg.GREEN], pts)

        return surf
