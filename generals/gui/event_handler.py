import pygame

from generals import config as c
from .rendering import Renderer


class EventHandler:
    def __init__(self, renderer: Renderer, from_replay=False):
        """
        Initialize the event handler.

        Args:
            renderer: the Renderer object
            from_replay: bool, whether the game is from a replay
        """
        self.renderer = renderer
        self.from_replay = from_replay

    def handle_events(self):
        """
        Handle pygame GUI events
        """
        control_events = {
            "time_change": 0,
        }
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_q
            ):
                pygame.quit()
                quit()

            if event.type == pygame.KEYDOWN and self.from_replay:
                self.__handle_key_controls(event, control_events)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.__handle_mouse_click()

        return control_events


    def __handle_key_controls(self, event, control_events):
        """
        Handle key controls for replay mode.
        Control game speed, pause, and replay frames.
        """
        match event.key:
            # Speed up game right arrow is pressed
            case pygame.K_RIGHT:
                self.renderer.game_speed = max(1 / 128, self.renderer.game_speed / 2)
            # Slow down game left arrow is pressed
            case pygame.K_LEFT:
                self.renderer.game_speed = min(32.0, self.renderer.game_speed * 2)
            # Toggle play/pause
            case pygame.K_SPACE:
                self.renderer.paused = not self.renderer.paused
            case pygame.K_r:
                control_events["restart"] = True
            # Control replay frames
            case pygame.K_h:
                control_events["time_change"] = -1
                self.renderer.paused = True
            case pygame.K_l:
                control_events["time_change"] = 1
                self.renderer.paused = True


    def __handle_mouse_click(self):
        """
        Handle mouse click event.
        """
        agents = self.renderer.game.agents

        x, y = pygame.mouse.get_pos()
        for i, agent in enumerate(agents):
            # if clicked agents row in the right panel
            if (
                    x >= self.renderer.display_grid_width
                    and y >= (i + 1) * c.GUI_ROW_HEIGHT
                    and y < (i + 2) * c.GUI_ROW_HEIGHT
            ):
                self.renderer.agent_fov[agent] = not self.renderer.agent_fov[agent]
                break
