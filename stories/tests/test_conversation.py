
import unittest
import sys
import os

# Ensure the 'stories/games' directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../games')))

from game_conversation import World, AIClient

class MockAIClient:
    def __init__(self, config_file):
        self.enabled = True
    def map_command(self, user_input, valid_cmds):
        return None # Fail by default for tests

class TestGame(unittest.TestCase):
    def test_story(self):
        from game_conversation import GAME_DATA
        # Monkey patch
        import game_conversation
        game_conversation.AIClient = MockAIClient

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
