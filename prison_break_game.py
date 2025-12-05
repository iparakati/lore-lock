
import sys
import json

# Data injected by compiler
GAME_DATA = {'title': 'Prison Break', 'start_room': 'Damp Stone Cell', 'rooms': {'Damp Stone Cell': {'name': 'Damp Stone Cell', 'description': 'You wake up on a hard slab in a damp stone cell. The air is cold and smells strongly of brine and mold.', 'items': ['stone slab']}, 'Corridor': {'name': 'The Corridor', 'description': 'A dimly lit corridor, silent except for the drip of water. Torches flicker weakly on the walls.', 'items': []}}, 'doors': {'iron bars': {'name': 'iron bars', 'aliases': ['bars'], 'description': 'Thick iron bars blocking the way.', 'locked': True, 'key': 'rusty shiv', 'connections': {'Damp Stone Cell': 'north', 'Corridor': 'south'}, 'status_descriptions': {'locked': 'They appear to be locked.', 'closed': 'Iron bars block the north exit.'}}}, 'items': {'rusty shiv': {'name': 'rusty shiv', 'aliases': ['shiv'], 'description': 'A jagged piece of metal, sharp enough to cut but not meant for heavy fighting.', 'location': 'off-stage'}, 'stone slab': {'name': 'Stone Slab', 'aliases': ['slab'], 'description': 'It seems loose. You might be able to move it.', 'location': 'Damp Stone Cell', 'properties': {'fixed': False}, 'interactions': {'push': [{'condition': "items['rusty shiv']['location'] == 'off-stage'", 'message': 'You shift the heavy stone slab. Underneath, you discover a rusty shiv!', 'actions': [{'type': 'move', 'target': 'rusty shiv', 'destination': 'current_location'}, {'type': 'set_property', 'target': 'stone slab', 'property': 'fixed', 'value': True}]}], 'attack': [{'message': "It's stone. You'll only hurt your hands."}]}}}, 'test_sequence': ['examine slab', 'push slab', 'take shiv', 'unlock bars with shiv', 'open bars', 'north'], 'win_condition': {'type': 'location', 'target': 'Corridor'}}

# Game State
class GameState:
    def __init__(self, data):
        # We assume a deep copy is needed if we run tests multiple times in same process,
        # but for this script it's fine.
        # But if we modify 'data' during play, we should be careful if we restart.
        # We will do a cheap copy via json dump/load if needed, but here we just rely on fresh instance.
        import copy
        self.rooms = copy.deepcopy(data['rooms'])
        self.doors = copy.deepcopy(data.get('doors', {}))
        self.items = copy.deepcopy(data.get('items', {}))
        self.player_location = data['start_room']
        self.inventory = []
        self.data = data # Store original data reference if needed

    def get_current_room(self):
        return self.rooms[self.player_location]

    def get_item(self, item_name):
        # Check inventory
        for item_id in self.inventory:
            item = self.items[item_id]
            if self._match_name(item, item_name):
                return item

        # Check current room
        room = self.get_current_room()
        if 'items' in room:
            for item_id in room['items']:
                item = self.items[item_id]
                if self._match_name(item, item_name):
                    return item
        return None

    def _match_name(self, obj, name):
        name = name.lower()
        if obj['name'].lower() == name: return True
        if 'aliases' in obj:
            for alias in obj['aliases']:
                if alias.lower() == name: return True
        return False

    def move_player(self, direction):
        room = self.get_current_room()

        for door_id, door in self.doors.items():
            if self.player_location in door['connections']:
                conn_dir = door['connections'][self.player_location]
                if conn_dir == direction:
                    if door.get('locked', False):
                        print("The door is locked.")
                        return
                    if door.get('closed', True):
                         if not door.get('is_open', False):
                             print("The door is closed.")
                             return

                    # Find destination
                    for room_id, dir_val in door['connections'].items():
                        if room_id != self.player_location:
                            self.player_location = room_id
                            self.look()
                            return
        print("You can't go that way.")

    def look(self):
        room = self.get_current_room()
        print(room['name'])
        print(room['description'])

        # Additional description for doors
        for door_id, door in self.doors.items():
             if self.player_location in door['connections']:
                 pass

    def execute_custom_action(self, verb, noun):
        # Find item
        item_obj = self.get_item(noun)

        if not item_obj:
            # Check doors
             for door_id, door in self.doors.items():
                if self.player_location in door['connections']:
                    if self._match_name(door, noun):
                        # Door actions
                        if verb == 'open':
                            if door.get('locked', False):
                                print("It's locked.")
                            else:
                                door['is_open'] = True
                                print("You open the " + door['name'] + ".")
                        elif verb == 'unlock':
                             # Logic for unlocking handled in general or needs specific 'unlock with' parsing
                             pass
                        return True

        if item_obj and 'interactions' in item_obj:
            if verb in item_obj['interactions']:
                interaction = item_obj['interactions'][verb]
                # interactions is a list of potential outcomes based on conditions
                for outcome in interaction:
                    if self.check_condition(outcome.get('condition', 'True')):
                        print(outcome['message'])
                        self.apply_actions(outcome.get('actions', []))
                        return True
        return False

    def check_condition(self, condition_str):
        # A very unsafe but effective eval for this controlled environment
        # We need to expose 'items', 'rooms' to the eval context
        items = self.items
        rooms = self.rooms
        return eval(condition_str)

    def apply_actions(self, actions):
        for action in actions:
            if action['type'] == 'move':
                # Remove from current location
                item_id = action['target']
                dest = action['destination']

                # Remove from wherever it is
                # This is tricky without back-references.
                # We'll just scan rooms and inventory
                if item_id in self.inventory:
                    self.inventory.remove(item_id)
                else:
                    for r_id, r in self.rooms.items():
                        if 'items' in r and item_id in r['items']:
                            r['items'].remove(item_id)

                if dest == 'current_location':
                    self.rooms[self.player_location].setdefault('items', []).append(item_id)
                elif dest == 'inventory':
                    self.inventory.append(item_id)
                # handle off-stage implicitly by not adding anywhere

                self.items[item_id]['location'] = dest # Update internal tracker if needed

            elif action['type'] == 'set_property':
                self.items[action['target']]['properties'][action['property']] = action['value']

    def parse_command(self, command):
        parts = command.lower().split()
        if not parts: return
        verb = parts[0]

        if verb in ['n', 'north']:
            self.move_player('north')
        elif verb in ['s', 'south']:
            self.move_player('south')
        elif verb in ['e', 'east']:
            self.move_player('east')
        elif verb in ['w', 'west']:
            self.move_player('west')
        elif verb == 'look':
            self.look()
        elif verb in ['x', 'examine']:
            if len(parts) < 2: print("Examine what?"); return
            noun = " ".join(parts[1:])
            # Search inventory and room
            item = self.get_item(noun)
            if item:
                print(item['description'])
                return

            # Check doors
            for door_id, door in self.doors.items():
                 if self.player_location in door['connections']:
                     if self._match_name(door, noun):
                         desc = door['description']
                         if door.get('locked', False):
                             desc += " " + door['status_descriptions'].get('locked', '')
                         elif not door.get('is_open', False): # Closed
                             desc += " " + door['status_descriptions'].get('closed', '')
                         print(desc)
                         return
            print("You see nothing special.")

        elif verb == 'i' or verb == 'inventory':
            if not self.inventory:
                print("You are carrying nothing.")
            else:
                print("You are carrying: " + ", ".join(self.inventory))
        elif verb == 'take':
            if len(parts) < 2: print("Take what?"); return
            noun = " ".join(parts[1:])
            # Basic take logic
            room = self.get_current_room()
            if 'items' in room:
                for item_id in room['items']:
                    item = self.items[item_id]
                    if self._match_name(item, noun):
                         if item.get('properties', {}).get('fixed', False):
                             print("You can't take that.")
                             return
                         room['items'].remove(item_id)
                         self.inventory.append(item_id)
                         print("Taken.")
                         return
            print("You can't see that here.")

        elif verb == 'unlock':
             # syntax: unlock bars with shiv
             if 'with' not in parts: print("Unlock what with what?"); return
             with_index = parts.index('with')
             noun = " ".join(parts[1:with_index])
             key_name = " ".join(parts[with_index+1:])

             # Find door
             target_door = None
             for d_id, d in self.doors.items():
                 if self.player_location in d['connections']:
                     if self._match_name(d, noun):
                         target_door = d
                         break

             if not target_door:
                 print("You can't see that here.")
                 return

             # Check key in inventory
             has_key = False
             key_item = None
             for item_id in self.inventory:
                 item = self.items[item_id]
                 if self._match_name(item, key_name):
                     has_key = True
                     key_item = item
                     break

             if not has_key:
                 print("You don't have that.")
                 return

             if target_door['key'] == key_item['name'] or target_door['key'] in [i for i in self.inventory if self.items[i] == key_item]: # simplistic key check, relying on ID or name match
                  # Check if the key ID matches what the door expects
                  # The door 'key' field holds the ID (or name in this schema) of the key item
                  # We should compare names or IDs.
                  # For this schema, door.key = "rusty shiv" (ID/name)
                  # key_item['name'] = "rusty shiv"

                  # We find the key ID for the held item
                  found_key_id = None
                  for k, v in self.items.items():
                      if v == key_item:
                          found_key_id = k
                          break

                  if found_key_id == target_door['key'] or key_item['name'] == target_door['key']:
                       target_door['locked'] = False
                       print("You unlock the " + target_door['name'] + ".")
                  else:
                       print("It doesn't fit.")
             else:
                  print("It doesn't fit.")

        else:
            if len(parts) > 1:
                noun = " ".join(parts[1:])
                if self.execute_custom_action(verb, noun):
                    return
            print("I don't understand that command.")

def main():
    game = GameState(GAME_DATA)
    game.look()

    while True:
        try:
            cmd = input("> ")
            if cmd == "quit": break
            game.parse_command(cmd)
        except EOFError:
            break

if __name__ == "__main__":
    main()
