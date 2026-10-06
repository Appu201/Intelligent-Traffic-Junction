"""
dashboard.py - the information panel on the right (kept separate from the junction view).

It only *reads* data through the TrafficManager API, so it will keep working
unchanged when the data later also goes to the QNX RTOS.
"""
import pygame

import settings as cfg


def _font(size, bold=False):
    return pygame.font.SysFont("segoeui,helvetica,arial,dejavusans", size, bold=bold)


class Button:
    def __init__(self, rect, label, action):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.action = action

    def draw(self, surface, font, active_color=None):
        hover = self.rect.collidepoint(pygame.mouse.get_pos())
        if active_color:
            fill = active_color
        else:
            fill = cfg.COLOR_BUTTON_HOVER if hover else cfg.COLOR_BUTTON
        pygame.draw.rect(surface, fill, self.rect, border_radius=8)
        pygame.draw.rect(surface, (255, 255, 255, 40) if not active_color else active_color, self.rect, 1, border_radius=8)
        txt_color = (14, 18, 24) if active_color else cfg.COLOR_TEXT
        img = font.render(self.label, True, txt_color)
        surface.blit(img, img.get_rect(center=self.rect.center))


class Dashboard:
    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        self.f_title = _font(21, True)
        self.f_head = _font(20, True)
        self.f_text = _font(17)
        self.f_small = _font(14)
        self.f_big = _font(52, True)
        self.f_btn = _font(17, True)

        pad = 16
        bw = (self.rect.width - 2 * pad - 2 * 10) // 3
        by = self.rect.bottom - 92
        self.buttons = [
            Button((self.rect.x + pad + i * (bw + 10), by, bw, 44), label, action)
            for i, (label, action) in enumerate((("START", "start"), ("PAUSE", "pause"), ("RESET", "reset")))
        ]

    def handle_click(self, pos):
        """Return 'start' / 'pause' / 'reset' if a button was clicked, else None."""
        for b in self.buttons:
            if b.rect.collidepoint(pos):
                return b.action
        return None

    # ------------------------------------------------------------------ helpers
    def _text(self, surface, text, font, color, pos, anchor="topleft"):
        img = font.render(text, True, color)
        r = img.get_rect()
        setattr(r, anchor, pos)
        surface.blit(img, r)
        return r

    def _pill(self, surface, text, color, topright):
        img = self.f_small.render(text, True, (12, 16, 22))
        r = pygame.Rect(0, 0, img.get_width() + 22, 24)
        r.topright = topright
        pygame.draw.rect(surface, color, r, border_radius=12)
        surface.blit(img, img.get_rect(center=r.center))

    # ------------------------------------------------------------------ drawing
    def draw(self, surface, manager, running):
        r = self.rect
        pygame.draw.rect(surface, cfg.COLOR_PANEL_BG, r)
        pygame.draw.line(surface, (60, 70, 86), r.topleft, r.bottomleft, 2)
        x0, w = r.x + 16, r.width - 32

        # title block
        pygame.draw.line(surface, cfg.COLOR_ACCENT, (x0, 14), (x0 + w, 14), 2)
        self._text(surface, "INTELLIGENT TRAFFIC JUNCTION", self.f_title, cfg.COLOR_TEXT, (r.centerx, 24), "midtop")
        pygame.draw.line(surface, cfg.COLOR_ACCENT, (x0, 56), (x0 + w, 56), 2)

        # one card per road
        y = 68
        for rid in cfg.ROAD_IDS:
            self._road_card(surface, rid, manager, pygame.Rect(x0, y, w, 86))
            y += 94

        # active road block
        self._active_block(surface, manager, pygame.Rect(x0, y + 2, w, 118))
        y += 128

        # totals
        box = pygame.Rect(x0, y, w, 74)
        pygame.draw.rect(surface, cfg.COLOR_CARD_BG, box, border_radius=10)
        self._text(surface, "Total Vehicles", self.f_small, cfg.COLOR_TEXT_MUTED, (box.x + 14, box.y + 8))
        self._text(surface, str(manager.get_total_vehicles()), self.f_head, cfg.COLOR_TEXT, (box.x + 14, box.y + 28))
        self._text(surface, f"Passed: {manager.get_total_passed()}", self.f_small, cfg.COLOR_TEXT_MUTED, (box.x + 14, box.y + 52))
        self._text(surface, "Simulation Time", self.f_small, cfg.COLOR_TEXT_MUTED, (box.right - 14, box.y + 8), "topright")
        self._text(surface, f"{int(manager.sim_time)} s", self.f_head, cfg.COLOR_TEXT, (box.right - 14, box.y + 28), "topright")
        mm, ss = divmod(int(manager.sim_time), 60)
        self._text(surface, f"{mm:02d}:{ss:02d}", self.f_small, cfg.COLOR_TEXT_MUTED, (box.right - 14, box.y + 52), "topright")

        # buttons + status
        green, amber = cfg.COLOR_SIGNAL[cfg.GREEN], cfg.COLOR_SIGNAL[cfg.YELLOW]
        for b in self.buttons:
            active = green if (b.action == "start" and running) else amber if (b.action == "pause" and not running) else None
            b.draw(surface, self.f_btn, active)
        status = "RUNNING" if running else "PAUSED"
        self._text(surface, f"Status: {status}", self.f_small, green if running else amber, (x0, r.bottom - 38))
        self._text(surface, "SPACE = Pause/Resume   R = Reset", self.f_small, cfg.COLOR_TEXT_MUTED,
                   (x0 + w, r.bottom - 38), "topright")

    def _road_card(self, surface, rid, manager, rect):
        state = manager.get_signal_state(rid)
        color = cfg.COLOR_SIGNAL[state]
        pygame.draw.rect(surface, cfg.COLOR_CARD_BG, rect, border_radius=10)
        pygame.draw.rect(surface, color, (rect.x, rect.y + 8, 5, rect.height - 16), border_radius=3)

        self._text(surface, cfg.ROAD_NAMES[rid], self.f_head, cfg.COLOR_TEXT, (rect.x + 18, rect.y + 8))
        self._pill(surface, state, color, (rect.right - 12, rect.y + 10))

        self._text(surface, f"Vehicles: {manager.get_vehicle_count(rid)}", self.f_text, cfg.COLOR_TEXT, (rect.x + 18, rect.y + 36))
        self._text(surface, f"Queue: {manager.get_queue_length(rid)}", self.f_text, cfg.COLOR_TEXT_MUTED,
                   (rect.right - 12, rect.y + 36), "topright")
        if state == cfg.RED:
            self._text(surface, f"Green in: {manager.get_remaining_seconds(rid)} s", self.f_text, cfg.COLOR_TEXT_MUTED,
                       (rect.x + 18, rect.y + 58))
        else:
            self._text(surface, f"Timer: {manager.get_remaining_seconds(rid)} s", self.f_text, color, (rect.x + 18, rect.y + 58))

    def _active_block(self, surface, manager, rect):
        rid = manager.active_road
        state = manager.get_signal_state(rid)
        color = cfg.COLOR_SIGNAL[state]
        pygame.draw.rect(surface, cfg.COLOR_CARD_BG, rect, border_radius=10)
        pygame.draw.rect(surface, color, rect, 2, border_radius=10)

        self._text(surface, f"CURRENT ACTIVE ROAD: {rid}", self.f_head, cfg.COLOR_TEXT, (rect.x + 14, rect.y + 10))
        self._text(surface, f"SIGNAL: {state}", self.f_text, color, (rect.x + 14, rect.y + 42))
        self._text(surface, "TIME REMAINING", self.f_small, cfg.COLOR_TEXT_MUTED, (rect.x + 14, rect.y + 68))
        self._text(surface, f"{manager.get_remaining_seconds(rid)} s", self.f_big, color, (rect.right - 14, rect.y + 34), "topright")

        bar = pygame.Rect(rect.x + 14, rect.bottom - 18, rect.width - 28, 7)
        pygame.draw.rect(surface, (14, 17, 22), bar, border_radius=4)
        fill = bar.copy()
        fill.width = max(0, int(bar.width * manager.get_phase_progress()))
        pygame.draw.rect(surface, color, fill, border_radius=4)
