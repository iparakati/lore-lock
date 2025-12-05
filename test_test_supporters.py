
import unittest
import sys
import os
from test_supporters_game import World, AIClient

class MockAIClient:
    def __init__(self, config_file):
        self.enabled = True
    def map_command(self, user_input, valid_cmds):
        return None # Fail by default for tests

class TestGame(unittest.TestCase):
    def test_story(self):
        from test_supporters_game import GAME_DATA
        # Monkey patch
        import test_supporters_game
        test_supporters_game.AIClient = MockAIClient

        game = World(GAME_DATA)

        print(f"\nTesting Story: {GAME_DATA.get('title', 'Untitled')}")

        commands = ['look', 'take apple', 'put apple in basket', 'look', 'take apple', 'put apple on table', 'look']
        for cmd in commands:
            print(f"> {cmd}")
            game.parse(cmd)

        win = {'type': 'location', 'target': 'Deck'}
        if win and win.get('type') == 'location':
            self.assertEqual(game.get_player_room().id, win['target'])

    def tearDown(self):
        if os.path.exists("savegame.json"): os.remove("savegame.json")

if __name__ == '__main__':
    unittest.main()
