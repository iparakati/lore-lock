
import unittest
import sys
import io
from contextlib import redirect_stdout
from prison_break_game import World

class TestGame(unittest.TestCase):
    def test_sequence(self):
        # Import data locally to avoid module level issues
        from prison_break_game import GAME_DATA
        game = World(GAME_DATA)

        commands = ['examine slab', 'push slab', 'take shiv', 'open box', 'put shiv in box', 'look', 'examine box', 'take shiv', 'unlock bars with shiv', 'open bars', 'north']

        print("\n--- Game Trace ---")
        for cmd in commands:
            print(f"> {cmd}")
            game.parse_command(cmd)
        print("--- End Trace ---")

        # Check win condition
        win_condition = {'type': 'location', 'target': 'Corridor'}
        if win_condition and win_condition.get('type') == 'location':
            self.assertEqual(game.player_location, win_condition['target'])

if __name__ == '__main__':
    unittest.main()
