import pygame
import sys
import config
from pieces import Piece, SHAPES
from board import Board
from bot import Bot
from stats import Stats
from particles import ParticleManager
from audio_manager import AudioManager
import random

def main() -> None:
    pygame.init()
    
    # --- NEW: Apply Stream Mode (Frameless Window) ---
    flags = pygame.NOFRAME if config.STREAM_MODE else 0
    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), flags)
    
    pygame.display.set_caption(f"Block Stacker - {config.ACTIVE_THEME.name.title()} Mode")
    clock = pygame.time.Clock()

    title_font = pygame.font.SysFont("consolas", 36, bold=True)
    value_font = pygame.font.SysFont("consolas", 28)

    board = Board()
    bot = Bot()
    stats = Stats()
    particles = ParticleManager()
    audio = AudioManager()
    
    def spawn_piece() -> Piece:
        shape_name = random.choice(list(SHAPES.keys()))
        return Piece(shape_name, config.GRID_COLS // 2 - 1, 0)

    current_piece = spawn_piece()

    best_rot, best_x = bot.get_best_move(board, current_piece)
    for _ in range(best_rot):
        current_piece.rotate()
    current_piece.x = best_x

    board_pixel_width = config.GRID_COLS * config.CELL_SIZE
    offset_x = (config.SCREEN_WIDTH - board_pixel_width) // 2
    offset_y = 50 

    fall_time = 0
    fall_speed = config.BASE_FALL_SPEED // 4

    def draw_text(surface, text, font, color, x, y):
        text_obj = font.render(text, True, color)
        surface.blit(text_obj, (x, y))

    running = True
    while running:
        delta_time = clock.tick(config.TARGET_FPS)
        fall_time += delta_time

        particles.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                # --- NEW: Escape key to safely quit in Frameless mode ---
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    while board.is_valid_position(current_piece):
                        current_piece.y += 1
                    current_piece.y -= 1
                    fall_time = fall_speed 

        if fall_time >= fall_speed:
            fall_time = 0
            current_piece.y += 1
            
            if not board.is_valid_position(current_piece):
                current_piece.y -= 1 
                board.lock_piece(current_piece)
                
                audio.play("drop")
                
                cleared_data = board.clear_lines()
                if cleared_data:
                    stats.add_lines(len(cleared_data))
                    audio.play("clear")
                    
                    for y_index, row_colors in cleared_data:
                        particles.spawn_line_clear(y_index, row_colors, offset_x, offset_y)
                
                current_piece = spawn_piece()
                
                if not board.is_valid_position(current_piece):
                    print("Game Over! Auto-restarting...")
                    audio.play("gameover")
                    board = Board()
                    stats.reset()
                    current_piece = spawn_piece() 

                best_rot, best_x = bot.get_best_move(board, current_piece)
                for _ in range(best_rot):
                    current_piece.rotate()
                current_piece.x = best_x

        # --- RENDERING ---
        screen.fill(config.ACTIVE_THEME.bg_color)

        board_rect = pygame.Rect(offset_x, offset_y, config.GRID_COLS * config.CELL_SIZE, config.GRID_ROWS * config.CELL_SIZE)
        pygame.draw.rect(screen, (0, 0, 0), board_rect)
        pygame.draw.rect(screen, config.ACTIVE_THEME.grid_color, board_rect, 2)

        for r in range(config.GRID_ROWS):
            for c in range(config.GRID_COLS):
                if board.grid[r][c] is not None:
                    rect = pygame.Rect(offset_x + c * config.CELL_SIZE, offset_y + r * config.CELL_SIZE, config.CELL_SIZE, config.CELL_SIZE)
                    pygame.draw.rect(screen, board.grid[r][c], rect)
                    pygame.draw.rect(screen, config.ACTIVE_THEME.grid_color, rect, 1)

        for block_x, block_y in current_piece.get_blocks():
            pixel_x = offset_x + (block_x * config.CELL_SIZE)
            pixel_y = offset_y + (block_y * config.CELL_SIZE)
            rect = pygame.Rect(pixel_x, pixel_y, config.CELL_SIZE, config.CELL_SIZE)
            pygame.draw.rect(screen, current_piece.color, rect)
            pygame.draw.rect(screen, config.ACTIVE_THEME.grid_color, rect, 1)

        particles.draw(screen)

        text_c = config.ACTIVE_THEME.text_color
        draw_text(screen, "SCORE", title_font, text_c, 50, 100)
        draw_text(screen, str(stats.score), value_font, text_c, 50, 140)
        draw_text(screen, "LEVEL", title_font, text_c, 50, 220)
        draw_text(screen, str(stats.level), value_font, text_c, 50, 260)

        right_panel_x = offset_x + board_pixel_width + 50
        draw_text(screen, "LINES", title_font, text_c, right_panel_x, 100)
        draw_text(screen, str(stats.lines), value_font, text_c, right_panel_x, 140)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()