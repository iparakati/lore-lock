
import sys
import json
import os
import urllib.request
import urllib.error

# Data injected by compiler
GAME_DATA = {'title': 'Prison Break', 'scenes': [{'id': 'Damp Stone Cell', 'name': 'Damp Stone Cell', 'description': 'You wake up on a hard slab in a damp stone cell. The air is cold and smells strongly of brine and mold.', 'help_text': "You are stuck in a cell.\nScene Specific Commands:\n- 'examine slab'\n- 'push slab'\n- 'open box'\n- 'unlock bars with shiv'\n", 'contents': [{'id': 'stone slab', 'name': 'Stone Slab', 'aliases': ['slab'], 'description': 'It seems loose. You might be able to move it.', 'properties': {'fixed': False}, 'interactions': {'push': [{'message': 'You shift the heavy stone slab. Underneath, you discover a rusty shiv!', 'condition': "items['rusty shiv'].location_id == 'off-stage'", 'actions': [{'type': 'move', 'target': 'rusty shiv', 'destination': 'current_location'}, {'type': 'set_property', 'target': 'stone slab', 'property': 'fixed', 'value': True}]}], 'attack': [{'message': "It's stone. You'll only hurt your hands."}]}}, {'id': 'moldy box', 'kind': 'container', 'name': 'moldy box', 'aliases': ['box'], 'description': 'A rotting wooden box.', 'properties': {'open': False}}], 'exits': {'north': {'target': 'Corridor', 'door': 'iron bars'}}}, {'id': 'Corridor', 'name': 'The Corridor', 'description': 'A dimly lit corridor, silent except for the drip of water. Torches flicker weakly on the walls.', 'help_text': "You have escaped!\nScene Specific Commands:\n- 'south' to return\n", 'exits': {'south': {'target': 'Damp Stone Cell', 'door': 'iron bars'}}}], 'off_stage': [{'id': 'rusty shiv', 'name': 'rusty shiv', 'aliases': ['shiv'], 'description': 'A jagged piece of metal, sharp enough to cut but not meant for heavy fighting.'}], 'doors': [{'id': 'iron bars', 'name': 'iron bars', 'aliases': ['bars'], 'description': 'Thick iron bars blocking the way.', 'locked': True, 'key': 'rusty shiv', 'status_descriptions': {'locked': 'They appear to be locked.', 'closed': 'Iron bars block the way.'}}], 'start_room': 'Damp Stone Cell', 'test_sequence': ['help', 'examine slab', 'push slab', 'take shiv', 'open box', 'put shiv in box', 'save', 'look', 'load', 'examine box', 'take shiv', 'unlock bars with shiv', 'open bars', 'north', 'help'], 'win_condition': {'type': 'location', 'target': 'Corridor'}}

DM_CONFIG_FILE = "dm_config.yaml"

class AIClient:
    def __init__(self, config_file):
        self.enabled = False
        self.config = {}
        self._load_env()
        self.api_key = os.environ.get("OPENAI_API_KEY")

        if self.api_key and os.path.exists(config_file):
            try:
                import yaml
                with open(config_file, 'r') as f:
                    self.config = yaml.safe_load(f)
                self.enabled = True
            except ImportError:
                print("Warning: PyYAML not installed, AI features disabled.")
            except Exception as e:
                print(f"Warning: Could not load DM config: {e}")
        elif not self.api_key:
            # print("Note: OPENAI_API_KEY not found. AI disabled.")
            pass

    def _load_env(self):
        if os.path.exists(".env"):
            try:
                with open(".env", "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"): continue
                        if "=" in line:
                            key, val = line.split("=", 1)
                            os.environ[key.strip()] = val.strip()
            except Exception as e:
                print(f"Warning: Failed to load .env: {e}")

    def map_command(self, user_input, valid_commands):
        if not self.enabled: return None

        system_prompt = self.config.get('system_prompt', "You are a helpful AI.")
        model = self.config.get('model', 'gpt-5-nano')
        temperature = self.config.get('temperature', 1)

        context_str = "\n".join([f"- {cmd}" for cmd in valid_commands])
        user_msg = f"User Input: {user_input}\n\nValid Commands:\n{context_str}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg}
        ]

        payload = {
            "model": model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": temperature
        }

        try:
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=json.dumps(payload).encode('utf-8'),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
            )
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                content = json.loads(result['choices'][0]['message']['content'])
                return content.get('command')
        except Exception as e:
            # print(f"AI Error: {e}")
            return None

class Entity:
    def __init__(self, id, data, world):
        self.id = id
        self.name = data['name']
        self.aliases = data.get('aliases', [])
        self.description = data.get('description', "")
        self.location_id = data.get('location', None)
        self.properties = data.get('properties', {})
        self.interactions = data.get('interactions', {})
        self.world = world
        self.kind = data.get('kind', 'thing')
        self.contents = [] # IDs of items inside/on this entity

    def match_name(self, name):
        name = name.lower()
        if self.name.lower() == name: return True
        for alias in self.aliases:
            if alias.lower() == name: return True
        return False

    def get_description(self):
        desc = self.description
        if self.kind == 'container':
             if self.properties.get('open', False):
                 desc += " It is open."
                 if self.contents:
                     names = [self.world.entities[i].name for i in self.contents]
                     desc += " Inside, you see: " + ", ".join(names)
                 else:
                     desc += " It is empty."
             else:
                 desc += " It is closed."
        return desc

    def to_state(self):
        return {
            'location_id': self.location_id,
            'properties': self.properties,
            'contents': self.contents
        }

    def load_state(self, state):
        self.location_id = state['location_id']
        self.properties = state['properties']
        self.contents = state['contents']

class Room(Entity):
    def __init__(self, id, data, world):
        super().__init__(id, data, world)
        self.kind = 'room'
        self.help_text = data.get('help_text', "")
        self.connections = {}

class Door(Entity):
    def __init__(self, id, data, world):
        super().__init__(id, data, world)
        self.kind = 'door'
        self.connections = data.get('connections', {})
        self.locked = data.get('locked', False)
        self.key_id = data.get('key', None)
        self.properties['open'] = data.get('properties', {}).get('open', False) # Default closed
        self.status_descriptions = data.get('status_descriptions', {})

    def get_description(self):
        desc = self.description
        if self.locked:
            desc += " " + self.status_descriptions.get('locked', 'It is locked.')
        elif not self.properties.get('open', False):
            desc += " " + self.status_descriptions.get('closed', 'It is closed.')
        else:
            desc += " It is open."
        return desc

    def to_state(self):
        s = super().to_state()
        s['locked'] = self.locked
        return s

    def load_state(self, state):
        super().load_state(state)
        self.locked = state.get('locked', self.locked)

class World:
    def __init__(self, data):
        self.entities = {}
        self.player_location = data['start_room']
        self.inventory = [] # List of IDs
        self.ai = AIClient(DM_CONFIG_FILE)

        # Parse 'screenplay' format
        if 'scenes' in data:
            self._load_screenplay(data)
        else:
            self._load_legacy(data)

    def _load_screenplay(self, data):
        # 1. Load Rooms (Scenes)
        for scene in data['scenes']:
            r_id = scene['id']
            r = Room(r_id, scene, self)
            self.entities[r_id] = r

            # Load contents (nested items)
            if 'contents' in scene:
                for item_data in scene['contents']:
                    i_id = item_data['id']
                    # Set location implicitly
                    item_data['location'] = r_id
                    i = Entity(i_id, item_data, self)
                    self.entities[i_id] = i
                    self.move_entity(i_id, r_id)

            # Process Exits to build connections later or now
            # We need door entities loaded first usually, so we might need a second pass or load doors first.

        # 2. Load Doors
        if 'doors' in data:
            for d_data in data['doors']:
                d_id = d_data['id']
                d = Door(d_id, d_data, self)
                self.entities[d_id] = d

        # 3. Load Off-stage items
        if 'off_stage' in data:
            for item_data in data['off_stage']:
                i_id = item_data['id']
                item_data['location'] = 'off-stage'
                i = Entity(i_id, item_data, self)
                self.entities[i_id] = i

        # 4. Wire up connections from Scene Exits
        for scene in data['scenes']:
            r_id = scene['id']
            if 'exits' in scene:
                for direction, exit_info in scene['exits'].items():
                    target_room = exit_info.get('target')
                    door_id = exit_info.get('door')

                    if door_id and door_id in self.entities:
                        # Add connection to door
                        door = self.entities[door_id]
                        if not hasattr(door, 'connections'): door.connections = {}
                        door.connections[r_id] = direction
                        # Note: The door needs to know both sides.
                        # The YAML defines exits per room.
                        # So if Cell says North->Corridor via Bars,
                        # and Corridor says South->Cell via Bars,
                        # we populate the door.connections dict with {Cell: North, Corridor: South}
                    elif target_room:
                        # Direct connection (not implemented in this engine yet, requires Door objects for movement)
                        # We can create a dummy door or upgrade Room to have direct exits.
                        # For now, we assume all exits use doors in this specific game.
                        pass

    def _load_legacy(self, data):
        # Load Rooms
        for r_id, r_data in data['rooms'].items():
            r = Room(r_id, r_data, self)
            self.entities[r_id] = r

        # Load Doors
        for d_id, d_data in data.get('doors', {}).items():
            d = Door(d_id, d_data, self)
            self.entities[d_id] = d

        # Load Items
        for i_id, i_data in data.get('items', {}).items():
            i = Entity(i_id, i_data, self)
            self.entities[i_id] = i

        # Build Hierarchy
        for r_id, r_data in data['rooms'].items():
            if 'items' in r_data:
                for i_id in r_data['items']:
                    if i_id in self.entities:
                        self.move_entity(i_id, r_id)

        for i_id, i_data in data.get('items', {}).items():
            loc = i_data.get('location')
            if loc and loc != 'off-stage' and loc in self.entities:
                self.move_entity(i_id, loc)

    def move_entity(self, entity_id, dest_id):
        ent = self.entities[entity_id]
        if ent.location_id and ent.location_id in self.entities:
            parent = self.entities[ent.location_id]
            if entity_id in parent.contents:
                parent.contents.remove(entity_id)

        ent.location_id = dest_id
        if dest_id in self.entities:
            self.entities[dest_id].contents.append(entity_id)

    def get_player_room(self):
        return self.entities[self.player_location]

    def get_visible_entities(self):
        visible = []
        room = self.get_player_room()
        visible.extend(self._get_contents_recursive(room))
        for i_id in self.inventory:
            visible.append(self.entities[i_id])
            visible.extend(self._get_contents_recursive(self.entities[i_id]))
        for d_id, ent in self.entities.items():
            if isinstance(ent, Door) and self.player_location in ent.connections:
                visible.append(ent)
        return visible

    def _get_contents_recursive(self, parent):
        res = []
        for child_id in parent.contents:
            child = self.entities[child_id]
            res.append(child)
            is_open_container = child.kind == 'container' and child.properties.get('open', False)
            is_supporter = child.kind == 'supporter'
            if is_open_container or is_supporter:
                res.extend(self._get_contents_recursive(child))
        return res

    def find_entity(self, name):
        for ent in self.get_visible_entities():
            if ent.match_name(name):
                return ent
        return None

    def get_valid_commands(self):
        cmds = []
        # Standard
        cmds.extend(['n', 's', 'e', 'w', 'north', 'south', 'east', 'west'])
        cmds.extend(['look', 'inventory', 'help', 'save', 'load'])

        visible = self.get_visible_entities()
        for ent in visible:
            name = ent.name.lower()
            # Interactions
            for verb in ent.interactions:
                cmds.append(f"{verb} {name}")

            # Standard verbs per kind
            cmds.append(f"examine {name}")
            if ent.kind != 'room' and not ent.properties.get('fixed', False):
                cmds.append(f"take {name}")
            if ent.kind == 'door' or ent.kind == 'container':
                cmds.append(f"open {name}")
                cmds.append(f"close {name}")
                cmds.append(f"unlock {name} with [key]")

        # Inventory specific
        for i_id in self.inventory:
            name = self.entities[i_id].name.lower()
            cmds.append(f"drop {name}")
            # put X in Y
            for ent in visible:
                if ent.kind == 'container':
                    cmds.append(f"put {name} in {ent.name.lower()}")

        return cmds

    def move_player(self, direction):
        current_room_id = self.player_location
        for ent in self.entities.values():
            if isinstance(ent, Door) and current_room_id in ent.connections:
                if ent.connections[current_room_id] == direction:
                    if ent.locked:
                        print("The door is locked.")
                        return
                    if not ent.properties.get('is_open', True) and not ent.properties.get('open', False):
                        print("The door is closed.")
                        return
                    for r_id, d in ent.connections.items():
                        if r_id != current_room_id:
                            self.player_location = r_id
                            self.look()
                            return
        print("You can't go that way.")

    def look(self):
        room = self.get_player_room()
        print(room.name)
        print(room.description)
        visible_items = [self.entities[i] for i in room.contents if self.entities[i].kind != 'scenery']
        if visible_items:
            names = []
            for item in visible_items:
                name = item.name
                if item.kind == 'container' and item.properties.get('open', False) and item.contents:
                    c_names = [self.entities[c].name for c in item.contents]
                    name += " (containing " + ", ".join(c_names) + ")"
                names.append(name)
            print("You see " + ", ".join(names) + " here.")

    def save_game(self, filename="savegame.json"):
        state = {
            'player_location': self.player_location,
            'inventory': self.inventory,
            'entities': {eid: e.to_state() for eid, e in self.entities.items()}
        }
        try:
            with open(filename, 'w') as f:
                json.dump(state, f)
            print(f"Game saved to {filename}.")
        except Exception as e:
            print(f"Error saving game: {e}")

    def load_game(self, filename="savegame.json"):
        try:
            with open(filename, 'r') as f:
                state = json.load(f)
            self.player_location = state['player_location']
            self.inventory = state['inventory']
            for eid, e_state in state['entities'].items():
                if eid in self.entities:
                    self.entities[eid].load_state(e_state)
            print(f"Game loaded from {filename}.")
            self.look()
        except FileNotFoundError:
            print("No save file found.")
        except Exception as e:
            print(f"Error loading game: {e}")

    def parse_command(self, command):
        parts = command.lower().split()
        if not parts: return
        verb = parts[0]

        if verb == 'save' and len(parts) == 1:
            self.save_game()
            return
        if verb == 'load' and len(parts) == 1:
            self.load_game()
            return

        if verb == 'help' and len(parts) == 1:
            print("Standard Commands:")
            print("  - n, s, e, w: Move")
            print("  - look: Describe area")
            print("  - i / inventory: Check inventory")
            print("  - take [item], drop [item]")
            print("  - examine [item] / x [item]")
            print("  - open [container/door]")
            print("  - put [item] in [container]")
            print("  - unlock [door] with [key]")
            print("  - save, load")

            room = self.get_player_room()
            if hasattr(room, 'help_text') and room.help_text:
                print(f"Scene Hints:\n{room.help_text}")
            return

        if verb in ['n', 'north', 's', 'south', 'e', 'east', 'w', 'west'] and len(parts) == 1:
            d = {'n':'north','s':'south','e':'east','w':'west'}.get(verb, verb)
            self.move_player(d)
            return

        if verb == 'look' and len(parts) == 1:
            self.look()
            return

        if verb in ['i', 'inventory'] and len(parts) == 1:
            if not self.inventory:
                print("You are carrying nothing.")
            else:
                names = [self.entities[i].name for i in self.inventory]
                print("You are carrying: " + ", ".join(names))
            return

        # Parse complex commands

        handled = False

        if len(parts) >= 2:
            noun = " ".join(parts[1:])

            # Drop
            if verb == 'drop':
                obj = self.find_entity(noun)
                if not obj: print("You don't have that."); handled=True
                elif obj.id not in self.inventory: print("You are not carrying that."); handled=True
                else:
                    self.inventory.remove(obj.id)
                    self.move_entity(obj.id, self.player_location)
                    print("Dropped.")
                    handled=True

            # Put
            if not handled and verb == 'put':
                if ' in ' in noun:
                    try:
                        obj_name, container_name = noun.split(' in ', 1)
                        obj = self.find_entity(obj_name)
                        cont = self.find_entity(container_name)
                        if not obj: print("You don't have that."); handled=True
                        elif not cont: print("You can't see that."); handled=True
                        else:
                            if cont.kind != 'container': print("That's not a container."); handled=True
                            elif not cont.properties.get('open', False): print("It's closed."); handled=True
                            else:
                                if obj.id in self.inventory:
                                    self.inventory.remove(obj.id)
                                self.move_entity(obj.id, cont.id)
                                print(f"You put the {obj.name} in the {cont.name}.")
                                handled=True
                    except ValueError:
                        print("I didn't understand that phrasing."); handled=True
                else:
                    print("Put what in what?"); handled=True

            if not handled:
                obj = self.find_entity(noun)

                if obj and verb in obj.interactions:
                     self.run_interaction(obj, verb)
                     handled = True

                elif verb == 'examine' or verb == 'x':
                    if obj:
                        print(obj.get_description())
                    else:
                        print("You see nothing special.")
                    handled = True

                elif verb == 'take':
                    if not obj: print("You can't see that."); handled=True
                    elif obj.kind == 'room': print("You can't take that."); handled=True
                    elif obj.properties.get('fixed', False): print("It's fixed in place."); handled=True

                    elif obj.id in self.inventory: print("You already have that."); handled=True

                    else:
                        if obj.location_id and obj.location_id in self.entities:
                            self.entities[obj.location_id].contents.remove(obj.id)

                        self.inventory.append(obj.id)
                        obj.location_id = 'inventory'
                        print("Taken.")
                        handled = True

                elif verb == 'open':
                    if not obj: print("You can't see that."); handled=True
                    else:
                        if obj.kind == 'door':
                            if obj.locked: print("It's locked.")
                            else:
                                obj.properties['open'] = True
                                print("Opened.")
                        elif obj.kind == 'container':
                            obj.properties['open'] = True
                            print("Opened.")
                        else:
                            print("You can't open that.")
                        handled = True

                elif verb == 'unlock':
                    if ' with ' in noun:
                         target_name, key_name = noun.split(' with ')
                         target = self.find_entity(target_name)
                         key = None
                         for i_id in self.inventory:
                             k = self.entities[i_id]
                             if k.match_name(key_name):
                                 key = k
                                 break

                         if not target: print("You can't see that."); handled=True
                         elif not key: print("You don't have that."); handled=True

                         elif target.kind == 'door':
                             if target.key_id == key.id or target.key_id == key.name:
                                 target.locked = False
                                 print("Unlocked.")
                             else:
                                 print("It doesn't fit.")
                         else:
                             print("That doesn't seem to have a lock.")
                         handled = True
                    else:
                        print("Unlock what with what?"); handled=True

        if not handled:
            # Try AI fallback
            valid_cmds = self.get_valid_commands()
            mapped = self.ai.map_command(command, valid_cmds)
            if mapped:
                print(f"(AI interpreting as: {mapped})")
                self.parse_command(mapped)
            else:
                print("I don't understand that sentence.")

    def run_interaction(self, obj, verb):
        rules = obj.interactions[verb]
        for rule in rules:
            items = self.entities
            try:
                if eval(rule.get('condition', 'True')):
                    print(rule['message'])
                    for act in rule.get('actions', []):
                        self.apply_action(act)
                    return
            except Exception as e:
                print(f"Error in game logic: {e}")

    def apply_action(self, action):
        if action['type'] == 'move':
            t_id = action['target']
            if t_id not in self.entities: return

            dest = action['destination']
            if dest == 'current_location':
                self.move_entity(t_id, self.player_location)
            elif dest == 'inventory':
                 ent = self.entities[t_id]
                 if ent.location_id in self.entities:
                     self.entities[ent.location_id].contents.remove(t_id)
                 self.inventory.append(t_id)
                 ent.location_id = 'inventory'
        elif action['type'] == 'set_property':
             t_id = action['target']
             if t_id in self.entities:
                 self.entities[t_id].properties[action['property']] = action['value']

def main():
    game = World(GAME_DATA)
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
