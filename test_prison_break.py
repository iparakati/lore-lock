
import unittest
import sys
import io
from contextlib import redirect_stdout
from prison_break_game import GameState

class TestGame(unittest.TestCase):
    def test_sequence(self):
        # Import data locally to avoid module level issues
        from prison_break_game import GAME_DATA
        game = GameState(GAME_DATA)

        commands = ['examine slab', 'push slab', 'take shiv', 'unlock bars with shiv', 'open bars', 'north']

        # Capture output to debug if needed
        # We print it to ensure the developer can see the game trace if test fails or runs

        print("\n--- Game Trace ---")
        for cmd in commands:
            print(f"> {cmd}")
            # We trap stdout to prevent cluttering unless we want to assert on it
            # For now, let's just let it print to stdout so we can see what's happening
            game.parse_command(cmd)
        print("--- End Trace ---")

        # Check win condition
        win_condition = {'type': 'location', 'target': 'Corridor'}
        if win_condition and win_condition.get('type') == 'location':
            self.assertEqual(game.player_location, win_condition['target'])

if __name__ == '__main__':
    unittest.main()
