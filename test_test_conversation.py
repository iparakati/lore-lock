
import unittest
import sys
import os
from test_conversation_game import World, AIClient

class MockAIClient:
    def __init__(self, config_file):
        self.enabled = True
    def map_command(self, user_input, valid_cmds):
        return None # Fail by default for tests

class TestGame(unittest.TestCase):
    def test_story(self):
        from test_conversation_game import GAME_DATA
        # Monkey patch
        import test_conversation_game
        test_conversation_game.AIClient = MockAIClient

        game = World(GAME_DATA)

        print(f"\nTesting Story: {GAME_DATA.get('title', 'Untitled')}")

        commands = ['look', 'ask bartender about drink', 'ask bartender about rumors', 'ask bartender about nothing']
        for cmd in commands:
            print(f"> {cmd}")
            game.parse(cmd)

        win = {'type': 'location', 'target': 'Bar'}
        if win and win.get('type') == 'location':
            self.assertEqual(game.get_player_room().id, win['target'])

    def tearDown(self):
        if os.path.exists("savegame.json"): os.remove("savegame.json")

if __name__ == '__main__':
    unittest.main()
