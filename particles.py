import pygame
import random
import math
import config
from typing import Tuple, List

class AmbientParticle:
    """Microscopic dust that drifts behind the game board."""
    def __init__(self):
        self.reset(random_y=True)
        
    def reset(self, random_y=False):
        self.x = random.uniform(0, config.SCREEN_WIDTH)
        # If random_y is true, spawn anywhere (for boot). Otherwise, spawn at the bottom.
        self.y = random.uniform(0, config.SCREEN_HEIGHT) if random_y else config.SCREEN_HEIGHT + random.uniform(10, 50)
        self.size = random.uniform(0.5, 2.5)
        self.speed_y = random.uniform(-0.8, -0.1) # Drift upward
        self.speed_x = random.uniform(-0.3, 0.3)
        self.base_alpha = random.uniform(30, 100)
        self.pulse_speed = random.uniform(0.001, 0.003)
        self.time_offset = random.uniform(0, 10000)

    def update(self) -> None:
        self.y += self.speed_y
        self.x += self.speed_x + math.sin((pygame.time.get_ticks() + self.time_offset) * 0.001) * 0.1
        
        # Recycle when floating off screen
        if self.y < -10 or self.x < -10 or self.x > config.SCREEN_WIDTH + 10:
            self.reset()

    def draw(self, surface: pygame.Surface, bloom_surf: pygame.Surface, scale: float) -> None:
        # Breathing alpha effect
        current_time = pygame.time.get_ticks()
        pulse = math.sin((current_time + self.time_offset) * self.pulse_speed)
        alpha = int(self.base_alpha + (pulse * 30))
        alpha = max(0, min(255, alpha))
        
        color = (150, 200, 255, alpha) if config.ACTIVE_THEME.name == "zen" else (0, 255, 200, alpha)
        
        # Draw tiny glowing orbs
        surf = pygame.Surface((int(self.size * 2), int(self.size * 2)), pygame.SRCALPHA)
        pygame.draw.circle(surf, color, (int(self.size), int(self.size)), int(self.size))
        surface.blit(surf, (int(self.x), int(self.y)), special_flags=pygame.BLEND_RGB_ADD)
        
        # Subtle bloom
        if bloom_surf:
            b_color = tuple(int(c * (alpha / 255.0)) for c in color[:3])
            pygame.draw.circle(bloom_surf, b_color, (int(self.x / scale), int(self.y / scale)), max(1, int(self.size / scale)))

class Particle:
    """Explosive physical shards for line clears."""
    def __init__(self, x: float, y: float, color: Tuple[int, int, int], floor_y: float):
        self.x = x
        self.y = y
        self.color = color
        self.theme = config.ACTIVE_THEME.name
        self.floor_y = floor_y
        
        if self.theme == "zen":
            self.dx = random.uniform(-1.0, 1.0)
            self.dy = random.uniform(-1.0, 0.0)
            self.gravity = 0.08  
            self.lifespan = random.randint(135, 200) 
            self.size = random.uniform(5.0, 8.0)
            self.splatted = False
        else:
            self.dx = random.uniform(-8.0, 8.0)
            self.dy = random.uniform(-10.0, 1.0)
            self.gravity = 0.6
            self.lifespan = random.randint(30, 50)
            self.size = random.uniform(5.0, 10.0)
            self.rotation = random.uniform(0, 360)
            self.rot_speed = random.uniform(-25, 25)
            
        self.max_lifespan = self.lifespan

    def update(self) -> bool:
        self.x += self.dx
        self.y += self.dy
        self.dy += self.gravity 
        
        if self.theme == "zen":
            if self.y >= self.floor_y and not getattr(self, 'splatted', False):
                self.y = self.floor_y
                self.dy = 0
                self.dx *= 1.5  
                self.splatted = True
        else:
            self.rotation += self.rot_speed
            if self.y >= self.floor_y:
                self.y = self.floor_y
                self.dy = -self.dy * 0.4  
                self.dx *= 0.7  
                
        self.lifespan -= 1
        return self.lifespan > 0

    def draw(self, surface: pygame.Surface, bloom_surf: pygame.Surface = None, scale: float = 1.0) -> None:
        current_size = max(0.1, self.size * (self.lifespan / self.max_lifespan))
        
        b_x, b_y = self.x / scale, self.y / scale
        b_size = current_size / scale
        b_color = tuple(int(c * 0.5) for c in self.color) 

        if self.theme == "zen":
            alpha = int(180 * (self.lifespan / self.max_lifespan))
            rgba_color = (*self.color, alpha)

            if getattr(self, 'splatted', False):
                time_dead = self.max_lifespan - self.lifespan
                w = int(current_size * 3 + time_dead * 1.2)
                h = int(current_size * 0.8)
                rect = pygame.Rect(int(self.x - w/2), int(self.y - h/2), w, h)
                pygame.draw.ellipse(surface, rgba_color, rect)
                
                if bloom_surf:
                    b_rect = pygame.Rect(int(b_x - (w/2)/scale), int(b_y - (h/2)/scale), int(w/scale), int(h/scale))
                    pygame.draw.ellipse(bloom_surf, b_color, b_rect)
            else:
                stretch = max(1.0, abs(self.dy) * 0.6)
                h = int(current_size * stretch)
                w = int(current_size * 0.85) 
                rect = pygame.Rect(int(self.x - w), int(self.y - h), w * 2, h * 2)
                pygame.draw.ellipse(surface, rgba_color, rect)
                
                if bloom_surf:
                    b_rect = pygame.Rect(int(b_x - w/scale), int(b_y - h/scale), int((w*2)/scale), int((h*2)/scale))
                    pygame.draw.ellipse(bloom_surf, b_color, b_rect)
        else:
            points = []
            bloom_points = []
            for angle in [0, 120, 240]: 
                rad = math.radians(self.rotation + angle)
                px = self.x + math.cos(rad) * current_size
                py = self.y + math.sin(rad) * current_size
                points.append((px, py))
                bloom_points.append((px / scale, py / scale))
                
            if len(points) > 2:
                pygame.draw.polygon(surface, self.color, points)
                if bloom_surf:
                    pygame.draw.polygon(bloom_surf, b_color, bloom_points)


class ParticleManager:
    def __init__(self):
        self.particles: List[Particle] = []
        self.ambient_particles = [AmbientParticle() for _ in range(60)] # --- NEW: Spawns 60 dust motes
        self.fluid_layer = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)

    def spawn_line_clear(self, grid_y: int, colors: List[Tuple[int, int, int]], offset_x: int, offset_y: int) -> None:
        pixel_y = offset_y + (grid_y * config.CELL_SIZE) + (config.CELL_SIZE // 2)
        floor_y = offset_y + (config.GRID_ROWS * config.CELL_SIZE)
        
        for col, color in enumerate(colors):
            pixel_x = offset_x + (col * config.CELL_SIZE) + (config.CELL_SIZE // 2)
            for _ in range(12):
                self.particles.append(Particle(pixel_x, pixel_y, color, floor_y))

    def update(self) -> None:
        self.particles = [p for p in self.particles if p.update()]
        for ap in self.ambient_particles:
            ap.update()

    def draw_ambient(self, surface: pygame.Surface, bloom_surf: pygame.Surface, scale: float) -> None:
        """Draws the slow-drifting background nebula dust."""
        for ap in self.ambient_particles:
            ap.draw(surface, bloom_surf, scale)

    def draw(self, surface: pygame.Surface, bloom_surf: pygame.Surface = None, scale: float = 1.0) -> None:
        if config.ACTIVE_THEME.name == "zen":
            self.fluid_layer.fill((0, 0, 0, 0))
            for p in self.particles:
                p.draw(self.fluid_layer, bloom_surf, scale)
            surface.blit(self.fluid_layer, (0, 0))
        else:
            for p in self.particles:
                p.draw(surface, bloom_surf, scale)