"""
main.py - starts the Pygame application and runs the main loop.

Run with:   python main.py

Controls:   SPACE = pause / resume      R = reset      ESC = quit
            (or click the START / PAUSE / RESET buttons)
"""
import sys

import pygame

import settings as cfg
from dashboard import Dashboard
from intersection import Intersection
from traffic_manager import TrafficManager
from vehicle_generator import VehicleGenerator


class Simulation:
    """The whole traffic world (no window code), so it can also be run headless for tests."""

    def __init__(self):
        self.intersection = Intersection()
        self.vehicles = []                                           # shared with the manager and generator
        self.manager = TrafficManager(self.vehicles)
        self.generator = VehicleGenerator(self.intersection, self.vehicles)
        self.signal_font = pygame.font.SysFont("segoeui,helvetica,arial,dejavusans", 15, bold=True)

    def reset(self):
        """Timer back to 30 s, Road A GREEN, B / C RED, vehicles and statistics cleared."""
        self.vehicles.clear()                                        # in place: references stay valid
        self.manager.reset()
        self.generator.reset()

    def update(self, dt):
        self.manager.update(dt)                                      # signals + clock
        self.generator.update(dt)                                    # new vehicles

        self.vehicles.sort(key=lambda v: -v.s)                       # leaders move first
        for v in self.vehicles:
            v.update(dt, self.vehicles, self.manager)

        for v in self.vehicles:                                      # statistics
            if v.cleared and not v.counted:
                v.counted = True
                self.manager.record_passed(v.origin)
        self.vehicles[:] = [v for v in self.vehicles if not v.finished]

    def draw(self, surface):
        surface.blit(self.intersection.background, (0, 0))
        for v in self.vehicles:
            v.draw(surface)
        self.intersection.draw_signals(surface, self.manager.signals, self.signal_font)


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(cfg.WINDOW_TITLE)
        self.screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()

        self.sim = Simulation()
        self.sim_view = self.screen.subsurface(pygame.Rect(0, 0, cfg.SIM_WIDTH, cfg.SIM_HEIGHT))   # clips off-screen vehicles
        self.dashboard = Dashboard(pygame.Rect(cfg.SIM_WIDTH, 0, cfg.PANEL_WIDTH, cfg.SCREEN_HEIGHT))
        self.running = cfg.AUTO_START                                # simulation running (not paused)
        self.alive = True
        self.big_font = pygame.font.SysFont("segoeui,helvetica,arial,dejavusans", 44, bold=True)

    # ------------------------------------------------------------------ input
    def do_action(self, action):
        if action == "start":
            self.running = True
        elif action == "pause":
            self.running = False
        elif action == "reset":
            self.sim.reset()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.alive = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.running = not self.running
                elif event.key == pygame.K_r:
                    self.do_action("reset")
                elif event.key == pygame.K_ESCAPE:
                    self.alive = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                action = self.dashboard.handle_click(event.pos)
                if action:
                    self.do_action(action)

    # ------------------------------------------------------------------ draw
    def draw(self):
        self.sim.draw(self.sim_view)
        if not self.running:
            veil = pygame.Surface((cfg.SIM_WIDTH, cfg.SIM_HEIGHT), pygame.SRCALPHA)
            veil.fill((0, 0, 0, 90))
            self.sim_view.blit(veil, (0, 0))
            img = self.big_font.render("PAUSED", True, (255, 255, 255))
            self.sim_view.blit(img, img.get_rect(center=(cfg.SIM_WIDTH // 2, 60)))
        self.dashboard.draw(self.screen, self.sim.manager, self.running)
        pygame.display.flip()

    # ------------------------------------------------------------------ main loop
    def run(self):
        while self.alive:
            dt = min(self.clock.tick(cfg.FPS) / 1000.0, cfg.MAX_DT)  # delta time, never sleeps
            self.handle_events()
            if self.running:
                self.sim.update(dt)
            self.draw()
        pygame.quit()


def main():
    App().run()


if __name__ == "__main__":
    main()
    sys.exit(0)
