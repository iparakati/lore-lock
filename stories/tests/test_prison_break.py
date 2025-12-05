
import unittest
import sys
import os

# Ensure the 'stories/games' directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../games')))

from game_prison_break import World, AIClient

class MockAIClient:
    def __init__(self, config_file):
        self.enabled = True
    def map_command(self, user_input, valid_cmds):
        return None # Fail by default for tests

class TestGame(unittest.TestCase):
    def test_story(self):
        from game_prison_break import GAME_DATA
        # Monkey patch
        import game_prison_break
        game_prison_break.AIClient = MockAIClient

        game = World(GAME_DATA)

        print(f"\nTesting Story: {GAME_DATA.get('title', 'Untitled')}")

        commands = ['look', 'examine slab', 'push slab', 'take shiv', 'open box', 'put shiv in box', 'close box', 'look', 'open box', 'take shiv', 'ask guard about freedom', 'unlock bars with shiv', 'open bars', 'north', 'look']
        for cmd in commands:
            print(f"> {cmd}")
            game.parse(cmd)

        win = {'type': 'location', 'target': 'Corridor'}
        if win and win.get('type') == 'location':
            self.assertEqual(game.get_player_room().id, win['target'])

    def tearDown(self):
        if os.path.exists("savegame.json"): os.remove("savegame.json")

if __name__ == '__main__':
    unittest.main()
