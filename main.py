import pygame
import sys
import config
import random
from pieces import Piece, SHAPES
from board import Board
from bot import Bot
from stats import Stats
from particles import ParticleManager
from audio_manager import AudioManager
from renderer import Renderer
from settings_menu import SettingsMenu

def main() -> None:
    pygame.init()
    
    # ==========================================
    # --- TRUE FULLSCREEN & DYNAMIC SCALING ---
    # ==========================================
    # 1. Ask the OS for the monitor's native resolution
    info = pygame.display.Info()
    config.SCREEN_WIDTH = info.current_w
    config.SCREEN_HEIGHT = info.current_h
    
    # 2. Scale the blocks so the grid fills 85% of the screen height perfectly
    config.CELL_SIZE = int((config.SCREEN_HEIGHT * 0.85) / config.GRID_ROWS)

    # 3. Boot into Hardware-Accelerated Fullscreen
    flags = pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE
    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), flags)
    # ==========================================
    
    # Title uses the specific aesthetic palette name
    pygame.display.set_caption(f"Block Stacker - {config.ACTIVE_THEME.palette_name}")
    
    icon = pygame.Surface((32, 32))
    icon.fill(config.ACTIVE_THEME.piece_colors[0])
    pygame.draw.rect(icon, config.ACTIVE_THEME.bg_color, (4, 4, 24, 24))
    pygame.display.set_icon(icon)

    clock = pygame.time.Clock()

    # --- Initialize Engine Components ---
    board = Board()
    bot = Bot()
    stats = Stats()
    particles = ParticleManager()
    audio = AudioManager()
    renderer = Renderer(screen)
    menu = SettingsMenu(screen)
    
    def spawn_piece() -> Piece:
        shape_name = random.choice(list(SHAPES.keys()))
        return Piece(shape_name, config.GRID_COLS // 2 - 1, 0)

    current_piece = spawn_piece()
    next_piece = spawn_piece()

    target_rot, target_x = bot.get_best_move(board, current_piece)
    rotations_done = 0
    bot_aligned = False
    
    fall_time = 0
    bot_time = 0

    running = True
    while running:
        delta_time = clock.tick(config.TARGET_FPS)

        # ==========================================
        # 1. MENU STATE (Paused)
        # ==========================================
        if menu.is_open:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    menu.is_open = False
                
                # Intercept signals from the Settings Menu
                action = menu.handle_event(event)
                
                if action == "quit":
                    running = False
                
                elif action == "cycle_theme":
                    # Random Theme Pooling
                    if config.ACTIVE_THEME.name == "zen":
                        config.ACTIVE_THEME = random.choice(config.SATISFYING_THEMES)
                    else:
                        config.ACTIVE_THEME = random.choice(config.ZEN_THEMES)
                        
                    menu.update_labels()
                    pygame.display.set_caption(f"Block Stacker - {config.ACTIVE_THEME.palette_name}")
                    
                    # Wipe the board cleanly to apply new colors smoothly
                    board = Board()
                    stats.reset()
                    current_piece = spawn_piece()
                    next_piece = spawn_piece()
                    target_rot, target_x = bot.get_best_move(board, current_piece)
                    rotations_done = 0
                    bot_aligned = False
                
                elif action == "cycle_font":
                    # Loop through available fonts and trigger a render update
                    config.ACTIVE_FONT_INDEX = (config.ACTIVE_FONT_INDEX + 1) % len(config.AVAILABLE_FONTS)
                    menu.update_labels()
                    renderer.update_fonts() 

            # Draw background game, then menu overlay
            renderer.render(board, current_piece, next_piece, stats, particles)
            menu.draw()
            pygame.display.flip()  # Safe to flip here while the game is paused
            continue  

        # ==========================================
        # 2. GAMEPLAY STATE
        # ==========================================
        fall_time += delta_time
        bot_time += delta_time 
        particles.update()

        # --- Dynamic Fluid Resistance Math ---
        dynamic_multiplier = config.ACTIVE_THEME.fall_multiplier
        if config.ACTIVE_THEME.name == "zen":
            # Start fast, slow down as it sinks deeper into the fluid
            dynamic_multiplier = min(config.ACTIVE_THEME.fall_multiplier, 0.15 + (current_piece.y * 0.25))
        
        current_base_speed = config.BASE_FALL_SPEED * dynamic_multiplier

        # --- Input & Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    menu.is_open = True 
                
                # Manual Player Controls (Only active if bot is toggled OFF)
                if not menu.bot_enabled:
                    orig_x, orig_y = current_piece.x, current_piece.y
                    
                    if event.key == pygame.K_LEFT:
                        current_piece.x -= 1
                    elif event.key == pygame.K_RIGHT:
                        current_piece.x += 1
                    elif event.key == pygame.K_DOWN:
                        current_piece.y += 1
                        fall_time = 0
                    elif event.key == pygame.K_UP:
                        current_piece.rotate()
                        if not board.is_valid_position(current_piece):
                            current_piece.rotate(); current_piece.rotate(); current_piece.rotate()
                    elif event.key == pygame.K_SPACE:
                        while board.is_valid_position(current_piece):
                            current_piece.y += 1
                        current_piece.y -= 1
                        fall_time = current_base_speed 

                    if not board.is_valid_position(current_piece):
                        current_piece.x, current_piece.y = orig_x, orig_y

        # --- AI BOT LOGIC (Simultaneous Execution) ---
        if menu.bot_enabled:
            if not bot_aligned and bot_time >= config.BOT_MOVE_DELAY:
                bot_time = 0
                
                # Rotate and Move X concurrently
                if rotations_done < target_rot:
                    current_piece.rotate()
                    if not board.is_valid_position(current_piece):
                        current_piece.rotate(); current_piece.rotate(); current_piece.rotate()
                    else:
                        rotations_done += 1
                
                if current_piece.x < target_x:
                    current_piece.x += 1
                    if not board.is_valid_position(current_piece):
                        current_piece.x -= 1 
                elif current_piece.x > target_x:
                    current_piece.x -= 1
                    if not board.is_valid_position(current_piece):
                        current_piece.x += 1 
                
                if rotations_done == target_rot and current_piece.x == target_x:
                    bot_aligned = True
            
            # Diagonal swooping integration
            fall_speed = config.BOT_SOFT_DROP_SPEED * dynamic_multiplier
        else:
            fall_speed = current_base_speed

        # --- GRAVITY & TERRAIN HUGGING ---
        if fall_time >= fall_speed:
            fall_time = 0
            current_piece.y += 1
            
            if not board.is_valid_position(current_piece):
                current_piece.y -= 1 
                
                # Terrain Hugging: Slide horizontally across blocks if not aligned yet
                bot_is_sliding = menu.bot_enabled and not bot_aligned
                
                if bot_is_sliding:
                    orig_x = current_piece.x
                    current_piece.x += 1 if current_piece.x < target_x else -1
                    if not board.is_valid_position(current_piece):
                        bot_is_sliding = False # Trapped in a corner, force lock
                    current_piece.x = orig_x
                
                if not bot_is_sliding:
                    board.lock_piece(current_piece)
                    audio.play("drop")
                    
                    # Impact Physics Trigger (Localized squish)
                    blocks = current_piece.get_blocks()
                    if blocks:
                        lowest_y = max(b[1] for b in blocks)
                        center_x = sum(b[0] for b in blocks) / len(blocks)
                        renderer.trigger_impact(center_x, lowest_y, force=1.2)
                    
                    cleared_data = board.clear_lines()
                    if cleared_data:
                        stats.add_lines(len(cleared_data))
                        audio.play("clear")
                        
                        # Massive Shockwave Trigger for line clears
                        renderer.trigger_impact(config.GRID_COLS / 2, cleared_data[0][0], force=2.5)
                        
                        for y_index, row_colors in cleared_data:
                            particles.spawn_line_clear(y_index, row_colors, renderer.offset_x, renderer.offset_y)
                    
                    current_piece = next_piece
                    next_piece = spawn_piece()
                    
                    if not board.is_valid_position(current_piece):
                        print("Game Over! Auto-restarting...")
                        audio.play("gameover")
                        board = Board()
                        stats.reset()
                        current_piece = spawn_piece() 
                        next_piece = spawn_piece()

                    target_rot, target_x = bot.get_best_move(board, current_piece)
                    rotations_done = 0
                    bot_aligned = False

        # --- MASTER RENDER CALL ---
        # Calculate exactly how far between grid snaps we are for buttery smooth interpolation
        fall_progress = min(1.0, fall_time / fall_speed) if fall_speed > 0 else 0.0
        renderer.render(board, current_piece, next_piece, stats, particles, fall_progress)

        # THIS IS THE BOSS FLIP! 
        # By doing it here, we prevent the double-flip flickering glitch.
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()