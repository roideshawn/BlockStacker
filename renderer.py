import pygame
import config
import math
import random
from pieces import Piece
from board import Board
from stats import Stats
from particles import ParticleManager
from typing import Tuple

class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.board_pixel_width = config.GRID_COLS * config.CELL_SIZE
        
        self.base_offset_x = (config.SCREEN_WIDTH - self.board_pixel_width) // 2
        self.base_offset_y = (config.SCREEN_HEIGHT - (config.GRID_ROWS * config.CELL_SIZE)) // 2 
        self.offset_x = self.base_offset_x
        self.offset_y = self.base_offset_y
        
        self.trauma = 0.0  
        self.impacts = []
        self.shockwaves = [] # --- NEW: Manages expanding rings of light
        
        self.smooth_x = 0.0
        self.active_piece_ref = None

        self.bloom_scale = 4.0 
        self.bloom_surf = pygame.Surface((int(config.SCREEN_WIDTH / self.bloom_scale), 
                                          int(config.SCREEN_HEIGHT / self.bloom_scale)))
        
        self.glass_layer = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        self.vignette_surf = self._create_vignette() 

        self.image_cache = {}
        self.update_fonts()

    def _create_vignette(self) -> pygame.Surface:
        w, h = 200, 200  
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w / 2, h / 2
        max_dist = math.hypot(cx, cy)
        
        for y in range(h):
            for x in range(w):
                dist = math.hypot(x - cx, y - cy)
                ratio = min(1.0, dist / max_dist)
                alpha = int(255 * (ratio ** 2.5)) 
                surf.set_at((x, y), (0, 0, 0, alpha))
                
        return pygame.transform.smoothscale(surf, (config.SCREEN_WIDTH, config.SCREEN_HEIGHT))

    def update_fonts(self) -> None:
        font_name = config.AVAILABLE_FONTS[config.ACTIVE_FONT_INDEX]
        try:
            self.title_font = pygame.font.SysFont(font_name, 36, bold=True)
            self.value_font = pygame.font.SysFont(font_name, 28)
        except:
            self.title_font = pygame.font.SysFont("consolas", 36, bold=True)
            self.value_font = pygame.font.SysFont("consolas", 28)

    def _draw_background(self) -> None:
        theme = config.ACTIVE_THEME
        path_to_load = config.CUSTOM_BG_PATH if config.CUSTOM_BG_ENABLED else theme.bg_image_path
        
        if path_to_load:
            if path_to_load not in self.image_cache:
                try:
                    img = pygame.image.load(path_to_load).convert()
                    img_w, img_h = img.get_size()
                    screen_aspect = config.SCREEN_WIDTH / config.SCREEN_HEIGHT
                    img_aspect = img_w / img_h

                    if img_aspect > screen_aspect:
                        new_h = config.SCREEN_HEIGHT
                        new_w = int(new_h * img_aspect)
                    else:
                        new_w = config.SCREEN_WIDTH
                        new_h = int(new_w / img_aspect)

                    scaled_img = pygame.transform.smoothscale(img, (new_w, new_h))
                    final_surf = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
                    
                    x_offset = (config.SCREEN_WIDTH - new_w) // 2
                    y_offset = (config.SCREEN_HEIGHT - new_h) // 2
                    final_surf.blit(scaled_img, (x_offset, y_offset))
                    
                    self.image_cache[path_to_load] = final_surf
                except Exception as e:
                    self.image_cache[path_to_load] = None 

            if self.image_cache[path_to_load]:
                self.screen.blit(self.image_cache[path_to_load], (0, 0))
                return

        self.screen.fill(theme.bg_color)

    def _draw_board_background(self) -> None:
        theme = config.ACTIVE_THEME
        path_to_load = config.CUSTOM_BOARD_BG_PATH if config.CUSTOM_BOARD_BG_ENABLED else theme.board_image_path
        
        board_height = config.GRID_ROWS * config.CELL_SIZE
        board_rect = pygame.Rect(self.offset_x, self.offset_y, self.board_pixel_width, board_height)

        if path_to_load:
            if path_to_load not in self.image_cache:
                try:
                    img = pygame.image.load(path_to_load).convert()
                    img_w, img_h = img.get_size()
                    
                    board_aspect = self.board_pixel_width / board_height
                    img_aspect = img_w / img_h

                    if img_aspect > board_aspect:
                        new_h = board_height
                        new_w = int(new_h * img_aspect)
                    else:
                        new_w = self.board_pixel_width
                        new_h = int(new_w / img_aspect)

                    scaled_img = pygame.transform.smoothscale(img, (new_w, new_h))
                    final_surf = pygame.Surface((self.board_pixel_width, board_height))
                    
                    x_offset = (self.board_pixel_width - new_w) // 2
                    y_offset = (board_height - new_h) // 2
                    final_surf.blit(scaled_img, (x_offset, y_offset))
                    
                    self.image_cache[path_to_load] = final_surf
                except Exception as e:
                    self.image_cache[path_to_load] = None 

            if self.image_cache[path_to_load]:
                self.screen.blit(self.image_cache[path_to_load], (self.offset_x, self.offset_y))
                return

        pygame.draw.rect(self.screen, theme.board_bg_color, board_rect)

    def trigger_impact(self, grid_x: float, grid_y: float, force: float = 1.0) -> None:
        self.impacts.append({
            'x': grid_x, 'y': grid_y, 
            'time': pygame.time.get_ticks(), 'force': force
        })
        self.trauma = min(1.0, self.trauma + (force * 0.2))
        
        # --- NEW: Spawn an expanding light shockwave ---
        # The higher the force (e.g. 4-line clear), the bigger the wave
        pixel_x = self.base_offset_x + (grid_x * config.CELL_SIZE)
        pixel_y = self.base_offset_y + (grid_y * config.CELL_SIZE)
        
        target_radius = (config.CELL_SIZE * 4.0) * force
        if config.ACTIVE_THEME.name == "satisfying":
            target_radius *= 1.5 # Huge splash in satisfying mode
            
        self.shockwaves.append({
            'x': pixel_x, 'y': pixel_y,
            'radius': config.CELL_SIZE * 0.5,
            'max_radius': target_radius,
            'thickness': int(8 * force),
            'alpha': 255
        })

    def _get_ghost_y(self, board: Board, current_piece: Piece) -> int:
        original_y = current_piece.y
        while board.is_valid_position(current_piece):
            current_piece.y += 1
        ghost_y = current_piece.y - 1
        current_piece.y = original_y  
        return ghost_y

    def _draw_3d_block(self, surface: pygame.Surface, x: float, y: float, 
                       color: Tuple[int, int, int], is_ghost: bool = False,
                       grid_r: int = 0, grid_c: int = 0, 
                       neighbors: Tuple[bool, bool, bool, bool] = (False, False, False, False)) -> None:
        
        size = config.CELL_SIZE
        max_radius = int(size * 0.4) if config.ACTIVE_THEME.name == "zen" else int(size * 0.15)
        
        top_touch, right_touch, bottom_touch, left_touch = neighbors
        tl = 0 if (top_touch or left_touch) else max_radius
        tr = 0 if (top_touch or right_touch) else max_radius
        bl = 0 if (bottom_touch or left_touch) else max_radius
        br = 0 if (bottom_touch or right_touch) else max_radius

        wobble_w = 0.0
        wobble_h = 0.0
        offset_x = 0.0
        offset_y = 0.0
        
        if config.ACTIVE_THEME.name == "zen" and not is_ghost:
            current_time = pygame.time.get_ticks()
            for imp in self.impacts:
                t = current_time - imp['time']
                dist = math.sqrt((grid_c - imp['x'])**2 + (grid_r - imp['y'])**2)
                t_delayed = t - (dist * 20) 
                
                if t_delayed > 0:
                    amplitude = math.exp(-t_delayed / 337.0) * imp['force']
                    wave = amplitude * math.sin(t_delayed / 47.0)  
                    
                    if abs(grid_c - imp['x']) <= 1.0 and grid_r >= imp['y']:
                        wobble_w -= wave * 5.0  
                        wobble_h += wave * 5.0  
                        offset_y += wave * 8.0  
                    else:
                        force_falloff = max(0, 1.0 - (dist * 0.12))
                        wobble_w -= wave * 3.0 * force_falloff
                        wobble_h += wave * 3.0 * force_falloff
                        
                        if grid_c < imp['x']: offset_x -= wave * 4.0 * force_falloff
                        elif grid_c > imp['x']: offset_x += wave * 4.0 * force_falloff
                        if grid_r > imp['y']: offset_y += wave * 4.0 * force_falloff

            breath = math.sin((current_time / 1080.0) + (grid_c * 0.1)) * 0.5
            wobble_w += breath
            wobble_h -= breath

        draw_x = x - wobble_w + offset_x
        draw_y = y - wobble_h + offset_y
        draw_size_w = size + (wobble_w * 2)
        draw_size_h = size + (wobble_h * 2)

        rect = pygame.Rect(int(draw_x), int(draw_y), int(draw_size_w), int(draw_size_h))

        if is_ghost:
            mixed_color = tuple(max(0, c - 150) for c in color)
            pygame.draw.rect(surface, mixed_color, rect, width=2, border_radius=max_radius)
            return

        light = tuple(min(255, c + 110) for c in color) 
        dark = tuple(max(0, int(c * 0.55)) for c in color)

        pygame.draw.rect(surface, dark, rect, 
                         border_top_left_radius=tl, border_top_right_radius=tr, 
                         border_bottom_left_radius=bl, border_bottom_right_radius=br)
        
        highlight_rect = pygame.Rect(int(draw_x), int(draw_y), int(draw_size_w - 2), int(draw_size_h - 2))
        pygame.draw.rect(surface, light, highlight_rect, 
                         border_top_left_radius=tl, border_top_right_radius=tr, 
                         border_bottom_left_radius=bl, border_bottom_right_radius=br)
        
        core_rect = pygame.Rect(int(draw_x + 2), int(draw_y + 2), int(draw_size_w - 4), int(draw_size_h - 4))
        pygame.draw.rect(surface, color, core_rect, 
                         border_top_left_radius=tl, border_top_right_radius=tr, 
                         border_bottom_left_radius=bl, border_bottom_right_radius=br)

        bloom_color = tuple(int(c * 0.7) for c in color) 
        b_x = (draw_x + 2) / self.bloom_scale
        b_y = (draw_y + 2) / self.bloom_scale
        b_w = (draw_size_w - 4) / self.bloom_scale
        b_h = (draw_size_h - 4) / self.bloom_scale
        b_radius = int(max_radius / self.bloom_scale)
        b_rect = pygame.Rect(int(b_x), int(b_y), int(b_w), int(b_h))
        
        pygame.draw.rect(self.bloom_surf, bloom_color, b_rect, border_radius=b_radius)

    def render(self, board: Board, current_piece: Piece, next_piece: Piece, stats: Stats, particles: ParticleManager, fall_progress: float = 0.0) -> None:
        current_time = pygame.time.get_ticks()
        self.impacts = [imp for imp in self.impacts if current_time - imp['time'] < 1000]

        self.trauma = max(0.0, self.trauma - 0.015) 
        shake = (self.trauma ** 2) * 25.0 * config.ACTIVE_THEME.shake_multiplier
        
        cam_x, cam_y = 0.0, 0.0
        if shake > 0:
            cam_x += random.uniform(-1.0, 1.0) * shake
            cam_y += random.uniform(-1.0, 1.0) * shake
            
        if config.ACTIVE_THEME.name == "zen":
            cam_x += math.sin(current_time / 1800.0) * 4.0
            cam_y += math.cos(current_time / 2300.0) * 3.0
            
        self.offset_x = self.base_offset_x + int(cam_x)
        self.offset_y = self.base_offset_y + int(cam_y)

        # 1. Base Layers
        self._draw_background()
        self.bloom_surf.fill((0, 0, 0)) 
        self.glass_layer.fill((0, 0, 0, 0))
        self._draw_board_background()

        # 2. NEW: Ambient Nebula Layer (Drawn behind the grid and blocks!)
        particles.draw_ambient(self.screen, self.bloom_surf, self.bloom_scale)

        # 3. Grid Lines
        board_rect = pygame.Rect(self.offset_x, self.offset_y, self.board_pixel_width, config.GRID_ROWS * config.CELL_SIZE)
        pygame.draw.rect(self.screen, config.ACTIVE_THEME.grid_color, board_rect, 2)

        # 4. Solid Blocks (GLASS LAYER)
        for r in range(config.GRID_ROWS):
            for c in range(config.GRID_COLS):
                if board.grid[r][c] is not None:
                    pixel_x = self.offset_x + c * config.CELL_SIZE
                    pixel_y = self.offset_y + r * config.CELL_SIZE
                    
                    top = (r > 0 and board.grid[r-1][c] is not None)
                    bottom = (r < config.GRID_ROWS - 1 and board.grid[r+1][c] is not None)
                    left = (c > 0 and board.grid[r][c-1] is not None)
                    right = (c < config.GRID_COLS - 1 and board.grid[r][c+1] is not None)
                    
                    self._draw_3d_block(self.glass_layer, pixel_x, pixel_y, board.grid[r][c], 
                                        grid_r=r, grid_c=c, neighbors=(top, right, bottom, left))

        # 5. Active Piece (GLASS LAYER)
        piece_blocks = current_piece.get_blocks()
        if self.active_piece_ref is not current_piece:
            self.smooth_x = float(current_piece.x)
            self.active_piece_ref = current_piece
            
        easing = 0.065 if config.ACTIVE_THEME.name == "zen" else 0.45
        self.smooth_x += (current_piece.x - self.smooth_x) * easing
        smooth_x_offset = (self.smooth_x - current_piece.x) * config.CELL_SIZE
        smooth_y_offset = fall_progress * config.CELL_SIZE
        
        sway_x = 0.0
        if config.ACTIVE_THEME.name == "zen":
            continuous_y = current_piece.y + fall_progress
            depth_factor = 1.0 + (continuous_y * 0.15) 
            sway_x = math.sin((current_time / 607.0) + (continuous_y * 0.5)) * (3.5 * depth_factor)
            sway_x = max(-12.0, min(12.0, sway_x))

        for block_x, block_y in piece_blocks:
            pixel_x = self.offset_x + (block_x * config.CELL_SIZE) + sway_x + smooth_x_offset
            pixel_y = self.offset_y + (block_y * config.CELL_SIZE) + smooth_y_offset
            
            top = (block_x, block_y - 1) in piece_blocks
            bottom = (block_x, block_y + 1) in piece_blocks
            left = (block_x - 1, block_y) in piece_blocks
            right = (block_x + 1, block_y) in piece_blocks
            
            self._draw_3d_block(self.glass_layer, pixel_x, pixel_y, current_piece.color, 
                                grid_r=block_y, grid_c=block_x, neighbors=(top, right, bottom, left))

        # 6. Apply Tinted Glass
        self.glass_layer.set_alpha(config.ACTIVE_THEME.block_alpha)
        self.screen.blit(self.glass_layer, (0, 0))

        # 7. Ghost Piece
        ghost_y = self._get_ghost_y(board, current_piece)
        original_y = current_piece.y
        current_piece.y = ghost_y
        for block_x, block_y in current_piece.get_blocks():
            pixel_x = self.offset_x + (block_x * config.CELL_SIZE)
            pixel_y = self.offset_y + (block_y * config.CELL_SIZE)
            self._draw_3d_block(self.screen, pixel_x, pixel_y, current_piece.color, is_ghost=True)
        current_piece.y = original_y  

        # ==========================================
        # --- NEW: KINETIC SHOCKWAVE PASS ---
        # ==========================================
        for sw in self.shockwaves[:]:
            # Rapid ease-out expansion
            sw['radius'] += (sw['max_radius'] - sw['radius']) * 0.15 
            sw['alpha'] -= 8  # Quick fade
            
            if sw['alpha'] <= 0:
                self.shockwaves.remove(sw)
            else:
                sw_surf = pygame.Surface((int(sw['max_radius']*2), int(sw['max_radius']*2)), pygame.SRCALPHA)
                
                # Draw sharp, glowing ring
                color = (255, 255, 255, max(0, sw['alpha']))
                pygame.draw.circle(sw_surf, color, (int(sw['max_radius']), int(sw['max_radius'])), int(sw['radius']), max(1, sw['thickness']))
                
                # We factor in camera offset so shockwaves shake with the board!
                screen_x = (sw['x'] - self.base_offset_x) + self.offset_x
                screen_y = (sw['y'] - self.base_offset_y) + self.offset_y
                self.screen.blit(sw_surf, (screen_x - sw['max_radius'], screen_y - sw['max_radius']), special_flags=pygame.BLEND_RGB_ADD)
                
                # Add to bloom surf for extreme glow
                b_color = (150, 150, 150)
                pygame.draw.circle(self.bloom_surf, b_color, (int(screen_x / self.bloom_scale), int(screen_y / self.bloom_scale)), int(sw['radius'] / self.bloom_scale), max(1, int(sw['thickness'] / self.bloom_scale)))
        # ==========================================

        # 8. Particles & Additive Bloom
        particles.draw(self.screen, self.bloom_surf, self.bloom_scale)
        scaled_bloom = pygame.transform.smoothscale(self.bloom_surf, (config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        self.screen.blit(scaled_bloom, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

        # 9. Chromatic Aberration
        ab_mult = config.ACTIVE_THEME.aberration_multiplier
        if self.trauma > 0.15 and ab_mult > 0:
            ab_shift = int((self.trauma ** 2) * 18 * ab_mult)
            red_surf = scaled_bloom.copy()
            red_surf.fill((255, 0, 0), special_flags=pygame.BLEND_RGB_MULT)
            blue_surf = scaled_bloom.copy()
            blue_surf.fill((0, 150, 255), special_flags=pygame.BLEND_RGB_MULT)
            self.screen.blit(red_surf, (-ab_shift, 0), special_flags=pygame.BLEND_RGB_ADD)
            self.screen.blit(blue_surf, (ab_shift, 0), special_flags=pygame.BLEND_RGB_ADD)

        # 10. Subsurface Reflection
        floor_y = self.offset_y + (config.GRID_ROWS * config.CELL_SIZE)
        capture_height = config.SCREEN_HEIGHT - floor_y  
        if capture_height > 0:
            capture_rect = pygame.Rect(self.offset_x, floor_y - capture_height, self.board_pixel_width, capture_height)
            if capture_rect.top >= 0 and capture_rect.bottom <= self.screen.get_height():
                board_bottom = self.screen.subsurface(capture_rect).copy()
                reflection = pygame.transform.flip(board_bottom, False, True)
                reflection.set_alpha(110) 
                self.screen.blit(reflection, (self.offset_x, floor_y))
                fade_surf = pygame.Surface((self.board_pixel_width, capture_height), pygame.SRCALPHA)
                bg_color = config.ACTIVE_THEME.bg_color
                for y in range(capture_height):
                    ratio = y / capture_height
                    alpha = min(255, int(math.pow(ratio, 1.5) * 255) + 30)
                    pygame.draw.line(fade_surf, (*bg_color, alpha), (0, y), (self.board_pixel_width, y))
                self.screen.blit(fade_surf, (self.offset_x, floor_y))
                pygame.draw.line(self.screen, config.ACTIVE_THEME.grid_color, 
                                 (self.offset_x, floor_y), 
                                 (self.offset_x + self.board_pixel_width, floor_y), 3)

        # 11. Vignette Pass
        if config.ACTIVE_THEME.vignette_alpha > 0:
            self.vignette_surf.set_alpha(config.ACTIVE_THEME.vignette_alpha)
            self.screen.blit(self.vignette_surf, (0, 0))

        # 12. UI Pass
        self._draw_ui(stats, next_piece)

    def _draw_text(self, text: str, font: pygame.font.Font, color: tuple, x: int, y: int) -> None:
        text_obj = font.render(text, True, color)
        self.screen.blit(text_obj, (x, y))

    def _draw_ui(self, stats: Stats, next_piece: Piece) -> None:
        text_c = config.ACTIVE_THEME.text_color
        left_panel_x = self.offset_x - 200 
        if left_panel_x < 20: left_panel_x = 20 
        ui_y = self.offset_y + 40

        self._draw_text("SCORE", self.title_font, text_c, left_panel_x, ui_y)
        self._draw_text(str(stats.score), self.value_font, text_c, left_panel_x, ui_y + 40)
        self._draw_text("LEVEL", self.title_font, text_c, left_panel_x, ui_y + 120)
        self._draw_text(str(stats.level), self.value_font, text_c, left_panel_x, ui_y + 160)

        right_panel_x = self.offset_x + self.board_pixel_width + 50
        self._draw_text("LINES", self.title_font, text_c, right_panel_x, ui_y)
        self._draw_text(str(stats.lines), self.value_font, text_c, right_panel_x, ui_y + 40)
        self._draw_text("NEXT", self.title_font, text_c, right_panel_x, ui_y + 120)
        
        preview_x = right_panel_x
        preview_y = ui_y + 160
        next_blocks = next_piece.get_blocks()
        for block_x, block_y in next_blocks:
            local_x = block_x - next_piece.x
            local_y = block_y - next_piece.y
            pixel_x = preview_x + (local_x * config.CELL_SIZE)
            pixel_y = preview_y + (local_y * config.CELL_SIZE)
            
            top = (block_x, block_y - 1) in next_blocks
            bottom = (block_x, block_y + 1) in next_blocks
            left = (block_x - 1, block_y) in next_blocks
            right = (block_x + 1, block_y) in next_blocks
            self._draw_3d_block(self.glass_layer, pixel_x, pixel_y, next_piece.color, neighbors=(top, right, bottom, left))