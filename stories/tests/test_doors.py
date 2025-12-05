
import unittest
import sys
import os

# Ensure the 'stories/games' directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../games')))

from game_doors import World, AIClient

class MockAIClient:
    def __init__(self, config_file):
        self.enabled = True
    def map_command(self, user_input, valid_cmds):
        return None # Fail by default for tests

class TestGame(unittest.TestCase):
    def test_story(self):
        from game_doors import GAME_DATA
        # Monkey patch
        import game_doors
        game_doors.AIClient = MockAIClient

        game = World(GAME_DATA)

        print(f"\nTesting Story: {GAME_DATA.get('title', 'Untitled')}")

        commands = ['east', 'take brass key', 'unlock oak door with brass key', 'open oak door', 'east', 'look']
        for cmd in commands:
            print(f"> {cmd}")
            game.parse(cmd)

        win = {'type': 'location', 'target': 'Bedroom'}
        if win and win.get('type') == 'location':
            self.assertEqual(game.get_player_room().id, win['target'])

    def tearDown(self):
        if os.path.exists("savegame.json"): os.remove("savegame.json")

if __name__ == '__main__':
    unittest.main()
