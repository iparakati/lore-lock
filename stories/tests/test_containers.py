
import unittest
import sys
import os

# Ensure the 'stories/games' directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../games')))

from game_containers import World, AIClient

class MockAIClient:
    def __init__(self, config_file):
        self.enabled = True
    def map_command(self, user_input, valid_cmds):
        return None # Fail by default for tests

class TestGame(unittest.TestCase):
    def test_story(self):
        from game_containers import GAME_DATA
        # Monkey patch
        import game_containers
        game_containers.AIClient = MockAIClient

        game = World(GAME_DATA)

        print(f"\nTesting Story: {GAME_DATA.get('title', 'Untitled')}")

        commands = ['look', 'take red gem', 'open glass box', 'take red gem', 'put red gem in steel safe', 'open steel safe', 'put red gem in steel safe', 'look', 'close steel safe', 'look']
        for cmd in commands:
            print(f"> {cmd}")
            game.parse(cmd)

        win = {'type': 'location', 'target': 'Lab'}
        if win and win.get('type') == 'location':
            self.assertEqual(game.get_player_room().id, win['target'])

    def tearDown(self):
        if os.path.exists("savegame.json"): os.remove("savegame.json")

if __name__ == '__main__':
    unittest.main()
