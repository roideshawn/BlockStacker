import pygame
import random
import config
from typing import Tuple, List

class Particle:
    """A single visual effect speck."""
    def __init__(self, x: float, y: float, color: Tuple[int, int, int]):
        self.x = x
        self.y = y
        self.color = color
        self.theme = config.ACTIVE_THEME.name
        
        # --- DUAL MODE PHYSICS ---
        if self.theme == "zen":
            # Zen: gentle, slow floating embers
            self.dx = random.uniform(-0.5, 0.5)
            self.dy = random.uniform(-1.0, -0.2)
            self.lifespan = random.randint(60, 100)
            self.size = random.uniform(2.0, 4.0)
        else:
            # Satisfying: explosive, fast burst with heavy gravity
            self.dx = random.uniform(-3.0, 3.0)
            self.dy = random.uniform(-4.0, 1.0)
            self.lifespan = random.randint(30, 60)
            self.size = random.uniform(3.0, 6.0)
            
        self.max_lifespan = self.lifespan

    def update(self) -> bool:
        """Moves the particle. Returns False when it's time to die."""
        self.x += self.dx
        self.y += self.dy
        
        # Add gravity only for the satisfying mode
        if self.theme == "satisfying":
            self.dy += 0.2  
            
        self.lifespan -= 1
        return self.lifespan > 0

    def draw(self, surface: pygame.Surface) -> None:
        # We shrink the particle's radius as its lifespan decreases.
        # This is incredibly fast for integrated graphics compared to alpha blending!
        current_size = max(0.1, self.size * (self.lifespan / self.max_lifespan))
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(current_size))


class ParticleManager:
    """Manages thousands of particles efficiently."""
    def __init__(self):
        self.particles: List[Particle] = []

    def spawn_line_clear(self, grid_y: int, colors: List[Tuple[int, int, int]], offset_x: int, offset_y: int) -> None:
        """Spawns a burst of particles exactly across the line that just vanished."""
        pixel_y = offset_y + (grid_y * config.CELL_SIZE) + (config.CELL_SIZE // 2)
        
        for col, color in enumerate(colors):
            pixel_x = offset_x + (col * config.CELL_SIZE) + (config.CELL_SIZE // 2)
            
            # Spawn 8 particles per block for a beautifully dense effect
            for _ in range(8):
                self.particles.append(Particle(pixel_x, pixel_y, color))

    def update(self) -> None:
        # List comprehension: Keep only the particles that return True (still alive)
        self.particles = [p for p in self.particles if p.update()]

    def draw(self, surface: pygame.Surface) -> None:
        for p in self.particles:
            p.draw(surface)