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
    # --- ANTI-CRACKING AUDIO PRE-INIT ---
    # 44100 Hz, 16-bit, Stereo, 2048 buffer size (stops clipping/stutter)
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.init()
    
    # ==========================================
    # --- TRUE FULLSCREEN & DYNAMIC SCALING ---
    # ==========================================
    info = pygame.display.Info()
    config.SCREEN_WIDTH = info.current_w
    config.SCREEN_HEIGHT = info.current_h
    
    # Scale the blocks so the grid fills 85% of the screen height perfectly
    config.CELL_SIZE = int((config.SCREEN_HEIGHT * 0.85) / config.GRID_ROWS)

    flags = pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE
    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), flags)
    
    pygame.display.set_caption(f"Block Stacker - {config.ACTIVE_THEME.palette_name}")
    
    icon = pygame.Surface((32, 32))
    icon.fill(config.ACTIVE_THEME.piece_colors[0])
    pygame.draw.rect(icon, config.ACTIVE_THEME.bg_color, (4, 4, 24, 24))
    pygame.display.set_icon(icon)

    clock = pygame.time.Clock()

    board = Board()
    bot = Bot()
    stats = Stats()
    particles = ParticleManager()
    audio = AudioManager()
    renderer = Renderer(screen)
    menu = SettingsMenu(screen)
    
    # Start the ambient music for the initial theme
    audio.play_ambient()
    
    # Milestone tracker for dynamic palette shifting
    next_theme_milestone = 50 

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
        
        # --- AUDIO BREATHE UPDATE ---
        audio.update()

        # ==========================================
        # 1. MENU STATE (Paused)
        # ==========================================
        if menu.is_open:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    menu.is_open = False
                
                action = menu.handle_event(event)
                
                if action == "quit":
                    running = False
                    
                # --- APPLY CUSTOM THEME INJECTION ---
                elif action == "apply_custom_theme":
                    # Force a config reload of the custom themes to grab the newest one
                    config.load_custom_themes()
                    
                    # Search the newly loaded themes for the one you just named
                    for t in config.ZEN_THEMES:
                        if t.palette_name == menu.last_applied_theme_name:
                            config.ACTIVE_THEME = t
                            break
                    
                    # Ensure the old global toggles are OFF so the Theme object handles the images
                    config.CUSTOM_BG_ENABLED = False
                    config.CUSTOM_BOARD_BG_ENABLED = False
                    
                    menu.update_labels()
                    pygame.display.set_caption(f"Block Stacker - {config.ACTIVE_THEME.palette_name}")
                    audio.play_ambient(force_refresh=True)
                    
                    # Reset the board to showcase the new theme cleanly
                    board = Board()
                    stats.reset()
                    next_theme_milestone = 50 
                    current_piece = spawn_piece()
                    next_piece = spawn_piece()
                    target_rot, target_x = bot.get_best_move(board, current_piece)
                    rotations_done = 0
                    bot_aligned = False
                
                elif action == "cycle_theme":
                    # Ensure the old global toggles are OFF so the Theme object handles the images
                    config.CUSTOM_BG_ENABLED = False
                    config.CUSTOM_BOARD_BG_ENABLED = False
                    
                    if config.ACTIVE_THEME.name == "zen":
                        config.ACTIVE_THEME = random.choice(config.SATISFYING_THEMES)
                    else:
                        config.ACTIVE_THEME = random.choice(config.ZEN_THEMES)
                        
                    menu.update_labels()
                    pygame.display.set_caption(f"Block Stacker - {config.ACTIVE_THEME.palette_name}")
                    audio.play_ambient(force_refresh=True)
                    
                    board = Board()
                    stats.reset()
                    next_theme_milestone = 50 
                    current_piece = spawn_piece()
                    next_piece = spawn_piece()
                    target_rot, target_x = bot.get_best_move(board, current_piece)
                    rotations_done = 0
                    bot_aligned = False
                
                elif action == "cycle_font":
                    config.ACTIVE_FONT_INDEX = (config.ACTIVE_FONT_INDEX + 1) % len(config.AVAILABLE_FONTS)
                    menu.update_labels()
                    renderer.update_fonts() 
                    
                elif action == "toggle_audio":
                    if not config.MASTER_AUDIO_ENABLED:
                        pygame.mixer.music.fadeout(500)
                    else:
                        audio.play_ambient()
                        
                elif action == "load_ambient":
                    # Force the new track to play immediately upon upload
                    audio.play_ambient(force_refresh=True)

            renderer.render(board, current_piece, next_piece, stats, particles)
            menu.draw()
            pygame.display.flip()  
            continue  

        # ==========================================
        # 2. GAMEPLAY STATE
        # ==========================================
        fall_time += delta_time
        bot_time += delta_time 
        particles.update()

        dynamic_multiplier = config.ACTIVE_THEME.fall_multiplier
        if config.ACTIVE_THEME.name == "zen":
            dynamic_multiplier = min(config.ACTIVE_THEME.fall_multiplier, 0.15 + (current_piece.y * 0.25))
        
        current_base_speed = config.BASE_FALL_SPEED * dynamic_multiplier

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    menu.is_open = True 
                
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

        if menu.bot_enabled:
            if not bot_aligned and bot_time >= config.BOT_MOVE_DELAY:
                bot_time = 0
                
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
            
            fall_speed = config.BOT_SOFT_DROP_SPEED * dynamic_multiplier
        else:
            fall_speed = current_base_speed

        if fall_time >= fall_speed:
            fall_time = 0
            current_piece.y += 1
            
            if not board.is_valid_position(current_piece):
                current_piece.y -= 1 
                bot_is_sliding = menu.bot_enabled and not bot_aligned
                
                if bot_is_sliding:
                    orig_x = current_piece.x
                    current_piece.x += 1 if current_piece.x < target_x else -1
                    if not board.is_valid_position(current_piece):
                        bot_is_sliding = False 
                    current_piece.x = orig_x
                
                if not bot_is_sliding:
                    board.lock_piece(current_piece)
                    
                    # --- DROP AUDIO & PHYSICS ---
                    audio.play_sfx("drop")
                    blocks = current_piece.get_blocks()
                    if blocks:
                        lowest_y = max(b[1] for b in blocks)
                        center_x = sum(b[0] for b in blocks) / len(blocks)
                        renderer.trigger_impact(center_x, lowest_y, force=1.2)
                    
                    cleared_data = board.clear_lines()
                    if cleared_data:
                        stats.add_lines(len(cleared_data))
                        
                        # --- CLEAR AUDIO & PHYSICS ---
                        audio.play_sfx("clear")
                        renderer.trigger_impact(config.GRID_COLS / 2, cleared_data[0][0], force=2.5)
                        
                        for y_index, row_colors in cleared_data:
                            particles.spawn_line_clear(y_index, row_colors, renderer.offset_x, renderer.offset_y)

                        # ==========================================
                        # --- SEAMLESS EVOLUTION (THEME SHIFT) ---
                        # ==========================================
                        if stats.lines >= next_theme_milestone:
                            next_theme_milestone += 50
                            
                            if config.ACTIVE_THEME.name == "zen":
                                config.ACTIVE_THEME = random.choice(config.ZEN_THEMES)
                            else:
                                config.ACTIVE_THEME = random.choice(config.SATISFYING_THEMES)
                                
                            menu.update_labels()
                            pygame.display.set_caption(f"Block Stacker - {config.ACTIVE_THEME.palette_name}")
                            audio.play_ambient() 
                            
                    current_piece = next_piece
                    next_piece = spawn_piece()
                    
                    if not board.is_valid_position(current_piece):
                        print("Game Over! Auto-restarting...")
                        board = Board()
                        stats.reset()
                        next_theme_milestone = 50
                        current_piece = spawn_piece() 
                        next_piece = spawn_piece()

                    target_rot, target_x = bot.get_best_move(board, current_piece)
                    rotations_done = 0
                    bot_aligned = False

        fall_progress = min(1.0, fall_time / fall_speed) if fall_speed > 0 else 0.0
        renderer.render(board, current_piece, next_piece, stats, particles, fall_progress)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()