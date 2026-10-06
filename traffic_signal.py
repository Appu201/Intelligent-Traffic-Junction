"""
traffic_signal.py - one signal head: RED / YELLOW / GREEN state, timer and drawing.

The signal itself is "dumb": it only stores what the TrafficManager tells it
(state + remaining seconds) and knows how to draw itself.
"""
import math

import pygame

import settings as cfg


def _dim(color, factor=0.22):
    return tuple(int(c * factor) for c in color)


class TrafficSignal:
    def __init__(self, road_id):
        self.road_id = road_id
        self.state = cfg.RED
        self.remaining = 0.0         # seconds left in the current state (RED: until green)

    @property
    def countdown(self):
        """Whole seconds for display: 30, 29, ... 1 (never shows 0)."""
        return max(0, math.ceil(self.remaining - 1e-9))

    # ------------------------------------------------------------------ drawing
    def draw(self, surface, center, horizontal, timer_offset, font):
        cx, cy = center
        w, h = (64, 22) if horizontal else (22, 64)
        head = pygame.Rect(0, 0, w, h)
        head.center = (int(cx), int(cy))

        # pole / bracket towards the kerb
        pygame.draw.rect(surface, (70, 72, 78), head.inflate(6, 6), border_radius=6)
        pygame.draw.rect(surface, (20, 21, 24), head, border_radius=5)

        order = (cfg.RED, cfg.YELLOW, cfg.GREEN)          # top->bottom or left->right
        for i, name in enumerate(order):
            if horizontal:
                pos = (head.left + 11 + i * 21, head.centery)
            else:
                pos = (head.centerx, head.top + 11 + i * 21)
            base = cfg.COLOR_SIGNAL[name]
            if name == self.state:
                glow = pygame.Surface((36, 36), pygame.SRCALPHA)
                pygame.draw.circle(glow, (*base, 70), (18, 18), 17)
                surface.blit(glow, glow.get_rect(center=pos))
                pygame.draw.circle(surface, base, pos, 7)
                pygame.draw.circle(surface, (255, 255, 255), (pos[0] - 2, pos[1] - 2), 2)
            else:
                pygame.draw.circle(surface, _dim(base), pos, 7)

        # tag with road letter (+ countdown while the road is GREEN / YELLOW)
        text = self.road_id if self.state == cfg.RED else f"{self.road_id}  {self.countdown}"
        img = font.render(text, True, cfg.COLOR_SIGNAL[self.state])
        tag = img.get_rect(center=(int(cx + timer_offset[0]), int(cy + timer_offset[1])))
        bg = tag.inflate(14, 8)
        pygame.draw.rect(surface, (14, 16, 20), bg, border_radius=7)
        pygame.draw.rect(surface, cfg.COLOR_SIGNAL[self.state], bg, 2, border_radius=7)
        surface.blit(img, tag)
