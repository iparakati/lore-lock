
import unittest
import sys
import io
import os
from contextlib import redirect_stdout
from prison_break_game import World, AIClient

class MockAIClient:
    def __init__(self, config_file):
        self.enabled = True
    def map_command(self, user_input, valid_cmds):
        if "move slab" in user_input: return "push slab"
        if "hug" in user_input: return None
        return None

class TestGame(unittest.TestCase):
    def test_sequence(self):
        # Import data locally to avoid module level issues
        from prison_break_game import GAME_DATA

        # Monkey patch
        import prison_break_game
        prison_break_game.AIClient = MockAIClient

        game = World(GAME_DATA)

        commands = ['help', 'examine slab', 'push slab', 'take shiv', 'open box', 'put shiv in box', 'save', 'look', 'load', 'examine box', 'take shiv', 'unlock bars with shiv', 'open bars', 'north', 'help']

        print("\n--- Game Trace ---")
        for cmd in commands:
            print(f"> {cmd}")
            game.parse_command(cmd)
        print("--- End Trace ---")

        # Check win condition
        win_condition = {'type': 'location', 'target': 'Corridor'}
        if win_condition and win_condition.get('type') == 'location':
            self.assertEqual(game.player_location, win_condition['target'])

    def tearDown(self):
        if os.path.exists("savegame.json"):
            os.remove("savegame.json")

if __name__ == '__main__':
    unittest.main()
