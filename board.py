import config
from pieces import Piece
from typing import List, Tuple, Optional

class Board:
    """Manages the playfield grid, handles block collisions, and clears full lines."""
    
    def __init__(self):
        self.grid: List[List[Optional[Tuple[int, int, int]]]] = [
            [None for _ in range(config.GRID_COLS)]
            for _ in range(config.GRID_ROWS)
        ]

    def is_valid_position(self, piece: Piece) -> bool:
        for x, y in piece.get_blocks():
            if x < 0 or x >= config.GRID_COLS:
                return False
            if y >= config.GRID_ROWS:
                return False
            if y >= 0 and self.grid[y][x] is not None:
                return False
        return True

    def lock_piece(self, piece: Piece) -> None:
        for x, y in piece.get_blocks():
            if 0 <= y < config.GRID_ROWS:
                self.grid[y][x] = piece.color

    def clear_lines(self) -> List[Tuple[int, List[Tuple[int, int, int]]]]:
        """
        Removes full rows and pushes blocks down.
        RETURNS: A list of the cleared lines so particles can spawn.
        Each item is: (y_index, list_of_RGB_colors_in_that_row)
        """
        cleared_info = []
        y = config.GRID_ROWS - 1
        
        while y >= 0:
            if all(cell is not None for cell in self.grid[y]):
                # Save the exact row index and its colors before we delete it!
                cleared_info.append((y, list(self.grid[y])))
                
                del self.grid[y]
                self.grid.insert(0, [None for _ in range(config.GRID_COLS)])
            else:
                y -= 1

        return cleared_info