
import sys
import json
import os
import urllib.request
import urllib.error
import re
import random

# Data injected by compiler
GAME_DATA = {'title': 'Undo Test', 'purpose': 'Test the undo functionality to ensure game state can be reverted.', 'scenes': [{'id': 'Room A', 'name': 'Room A', 'contents': [{'id': 'ball', 'name': 'ball'}]}], 'start_room': 'Room A', 'test_sequence': ['look', 'take ball', 'i', 'undo', 'i', 'look'], 'win_condition': {'type': 'location', 'target': 'Room A'}}
STORY_ID = "undo"

DM_CONFIG_FILE = "dm_config.yaml"

# ==========================================
# AI CLIENT
# ==========================================
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
                            key = key.strip()
                            if key not in os.environ:
                                os.environ[key] = val.strip()
            except Exception as e:
                print(f"Warning: Failed to load .env: {e}")

    def map_command(self, user_input, valid_commands):
        if not self.enabled: return None

        system_prompt = self.config.get('system_prompt', "You are a helpful AI.")
        model = self.config.get('model', 'gpt-5-nano')
        temperature = self.config.get('temperature', 1)

        context_str = "Translate the user's natural language into one of these standard formats:\n"
        context_str += "- look\n- n, s, e, w\n- take [object]\n- drop [object]\n- put [object] in [container]\n"
        context_str += "- put [object] on [supporter]\n- open [object]\n- close [object]\n"
        context_str += "- lock [object] with [key]\n- unlock [object] with [key]\n- ask [person] about [topic]\n- tell [person] about [topic]\n"
        context_str += "- wear [object]\n- eat [object]\n- enter [object]"

        user_msg = f"User Input: {user_input}\n\n{context_str}"

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
            return None

# ==========================================
# CORE OBJECT MODEL
# ==========================================

class Entity:
    def __init__(self, id, data, world):
        self.id = id
        self.name = data.get('name', 'unnamed')
        self.aliases = data.get('aliases', [])
        self.description = data.get('description', "")
        self.location_id = data.get('location', None)
        self.properties = data.get('properties', {})
        self.world = world
        self.contents = [] # IDs of children
        self.kind = data.get('kind', 'thing')

        # Interactions / Custom Rules
        # Stored as list of dicts: {verb, type, condition, message, actions}
        self.interactions = data.get('interactions', [])

    def match_name(self, name):
        name = name.lower()
        if self.name.lower() == name: return True
        for alias in self.aliases:
            if alias.lower() == name: return True
        return False

    def has_prop(self, prop):
        return self.properties.get(prop, False)

    def set_prop(self, prop, val):
        self.properties[prop] = val

    def get_description(self):
        return self.description

    def to_state(self):
        return {
            'location_id': self.location_id,
            'properties': self.properties.copy(),
            'contents': self.contents[:]
        }

    def load_state(self, state):
        self.location_id = state.get('location_id')
        self.properties = state.get('properties', {}).copy()
        self.contents = state.get('contents', [])[:]


class Thing(Entity):
    def __init__(self, id, data, world):
        super().__init__(id, data, world)
        # Default properties for Things
        defaults = {
            'portable': True,
            'scenery': False,
            'lit': False,
            'wearable': False,
            'edible': False,
            'pushable': False
        }
        for k, v in defaults.items():
            if k not in self.properties:
                self.properties[k] = v

class Room(Entity):
    def __init__(self, id, data, world):
        super().__init__(id, data, world)
        self.kind = 'room'
        self.properties['lit'] = True # Rooms usually lit by default unless dark
        self.exits = {} # direction -> entity_id (Door) or room_id

class Container(Thing):
    def __init__(self, id, data, world):
        super().__init__(id, data, world)
        # Container defaults
        defaults = {
            'openable': True,
            'open': False,
            'locked': False,
            'lockable': False,
            'transparent': False,
            'enterable': False
        }
        for k, v in defaults.items():
            if k not in self.properties:
                self.properties[k] = v

    def get_description(self):
        desc = self.description
        if self.has_prop('open'):
            desc += " It is open."
            if self.contents:
                names = [self.world.entities[i].name for i in self.contents]
                desc += " Inside is: " + ", ".join(names)
            else:
                desc += " It is empty."
        else:
             desc += " It is closed."
             if self.has_prop('transparent'):
                 if self.contents:
                    names = [self.world.entities[i].name for i in self.contents]
                    desc += " Inside you can see: " + ", ".join(names)
        return desc

class Supporter(Thing):
    def __init__(self, id, data, world):
        super().__init__(id, data, world)
        self.properties['enterable'] = False # Unless a chair/bed
        self.properties['scenery'] = True # Often furniture is fixed
        self.properties['portable'] = False

    def get_description(self):
        desc = self.description
        if self.contents:
            names = [self.world.entities[i].name for i in self.contents]
            desc += " On it you see: " + ", ".join(names)
        return desc

class Door(Thing):
    def __init__(self, id, data, world):
        super().__init__(id, data, world)
        self.kind = 'door'
        self.connections = data.get('connections', {}) # {room_id: direction}
        self.key_id = data.get('key', None)
        self.properties['portable'] = False

        # Pull top-level fields into properties if present
        if 'locked' in data: self.properties['locked'] = data['locked']
        if 'open' in data: self.properties['open'] = data['open']

        defaults = {'open': False, 'locked': False, 'openable': True}
        for k, v in defaults.items():
            if k not in self.properties:
                self.properties[k] = v

        # Auto-set lockable if locked
        if self.properties['locked']:
            self.properties['lockable'] = True

    def get_description(self):
        desc = self.description
        if self.has_prop('locked'):
            desc += " It is locked."
        elif self.has_prop('open'):
            desc += " It is open."
        else:
            desc += " It is closed."
        return desc

class Person(Thing):
    def __init__(self, id, data, world):
        super().__init__(id, data, world)
        self.kind = 'person'
        self.properties['alive'] = True
        self.properties['portable'] = False
        self.topics = data.get('topics', {}) # 'topic': 'response'

class Rulebook:
    def __init__(self, world):
        self.world = world

    def process(self, action):
        # 1. Before Rules (Custom interactions)
        if self.run_custom_rules(action, 'before'): return True # Stopped
        if self.run_custom_rules(action, 'instead'): return True # Stopped

        # 2. Check Rules (Standard logic)
        if not self.check(action): return True # Failed check

        # 3. Carry Out (State change)
        self.carry_out(action)

        # 4. After Rules
        if self.run_custom_rules(action, 'after'): return True # Custom outcome handles report

        # 5. Report
        self.report(action)
        return True

    def run_custom_rules(self, action, hook_type):
        # Check specific object interactions (noun or second_noun)
        targets = []
        if action.noun: targets.append(action.noun)
        if action.second: targets.append(action.second)
        # Also check room
        targets.append(self.world.get_player_room())

        for obj in targets:
            for rule in obj.interactions:
                # Rule format: {verb: 'take', type: 'before', condition: '...', message: '...', actions: []}
                if rule.get('verb') == action.verb and rule.get('type') == hook_type:
                    # Check condition
                    ctx = {
                        'world': self.world,
                        'action': action,
                        'player': self.world.get_player(),
                        'item': obj,
                        'items': self.world.entities
                    }
                    cond = rule.get('condition', 'True')
                    try:
                        # Allow simplified Python expressions
                        if eval(cond, {}, ctx):
                            if 'message' in rule:
                                print(rule['message'])
                            # Execute side effects
                            for eff in rule.get('actions', []):
                                self.world.apply_effect(eff)
                            return True # Rule matched and handled/stopped
                    except Exception as e:
                        print(f"Rule Error: {e}")
        return False

    def check(self, action):
        # Implement Standard Rules per verb
        verb = action.verb
        p = self.world.get_player()

        if verb == 'take':
            if not action.noun: print("Take what?"); return False
            if action.noun.id == p.id: print("You can't take yourself."); return False
            if not action.noun.has_prop('portable'): print("That's fixed in place."); return False
            if action.noun.location_id == p.id: print("You already have that."); return False
            # Check containment accessibility
            if not self.world.is_accessible(action.noun): print("You can't reach it."); return False
            return True

        if verb == 'drop':
            if not action.noun: print("Drop what?"); return False
            if action.noun.location_id != p.id: print("You aren't carrying that."); return False
            return True

        if verb == 'put':
            if not action.noun: print("Put what?"); return False
            if not action.second: print("Put it where?"); return False
            if action.noun.location_id != p.id: print("You aren't carrying that."); return False
            if action.noun.id == action.second.id: print("You can't put something inside itself."); return False
            if not action.second.has_prop('open') and not action.second.has_prop('enterable') and action.second.kind == 'container':
                print(f"The {action.second.name} is closed."); return False
            return True

        if verb == 'enter':
             if not action.noun: print("Enter what?"); return False
             if not action.noun.has_prop('enterable'): print("That's not something you can enter."); return False
             return True

        if verb == 'inventory':
            return True

        if verb == 'look':
            return True

        if verb == 'examine':
            if not action.noun: print("Examine what?"); return False
            return True

        if verb == 'open':
            if not action.noun: print("Open what?"); return False
            if not action.noun.has_prop('openable'): print("That's not something you can open."); return False
            if action.noun.has_prop('locked'): print("It is locked."); return False
            if action.noun.has_prop('open'): print("It is already open."); return False
            return True

        if verb == 'close':
            if not action.noun: print("Close what?"); return False
            if not action.noun.has_prop('openable'): print("That's not something you can close."); return False
            if not action.noun.has_prop('open'): print("It is already closed."); return False
            return True

        if verb == 'lock':
            if not action.noun: print("Lock what?"); return False
            if not action.noun.has_prop('lockable'): print("That doesn't have a lock."); return False
            if action.noun.has_prop('locked'): print("It's already locked."); return False
            if action.noun.has_prop('open'): print("Close it first."); return False
            if not action.second: print("Lock it with what?"); return False # Key
            if action.noun.key_id != action.second.id and action.noun.key_id != action.second.name:
                print("That key doesn't fit."); return False
            return True

        if verb == 'unlock':
            if not action.noun: print("Unlock what?"); return False
            if not action.noun.has_prop('lockable'): print("That doesn't have a lock."); return False
            if not action.noun.has_prop('locked'): print("It's already unlocked."); return False
            if not action.second: print("Unlock it with what?"); return False
            if action.noun.key_id != action.second.id and action.noun.key_id != action.second.name:
                print("That key doesn't fit."); return False
            return True

        if verb == 'wear':
            if not action.noun: print("Wear what?"); return False
            if not action.noun.has_prop('wearable'): print("You can't wear that."); return False
            if action.noun.location_id != p.id: print("You aren't holding it."); return False
            if action.noun.has_prop('worn'): print("You are already wearing it."); return False
            return True

        if verb == 'eat':
            if not action.noun: print("Eat what?"); return False
            if not action.noun.has_prop('edible'): print("That's not edible."); return False
            if action.noun.location_id != p.id: print("You aren't holding it."); return False
            return True

        if verb == 'ask':
             if not action.noun: print("Ask who?"); return False
             if action.noun.kind != 'person': print("You can't talk to that."); return False
             return True

        if verb == 'tell':
             if not action.noun: print("Tell who?"); return False
             if action.noun.kind != 'person': print("You can't talk to that."); return False
             return True

        if verb == 'go':
             # Handled in parser usually, but if we map 'go north' -> verb='go', noun='north'
             # Or verb='north'. Let's stick to verb='north' for simplicity in parser, or check standard map.
             pass

        return True

    def carry_out(self, action):
        verb = action.verb
        p = self.world.get_player()

        if verb == 'take':
            self.world.move_entity(action.noun.id, p.id)
            # If it was worn, unset worn
            if action.noun.has_prop('worn'): action.noun.set_prop('worn', False)

        if verb == 'drop':
            self.world.move_entity(action.noun.id, self.world.player_location)
            if action.noun.has_prop('worn'): action.noun.set_prop('worn', False)

        if verb == 'put':
            self.world.move_entity(action.noun.id, action.second.id)

        if verb == 'enter':
            self.world.move_entity(p.id, action.noun.id)

        if verb == 'open':
            action.noun.set_prop('open', True)

        if verb == 'close':
            action.noun.set_prop('open', False)

        if verb == 'lock':
            action.noun.set_prop('locked', True)

        if verb == 'unlock':
            action.noun.set_prop('locked', False)

        if verb == 'wear':
            action.noun.set_prop('worn', True)

        if verb == 'eat':
            # Destroy item
            self.world.remove_entity(action.noun.id)

    def report(self, action):
        verb = action.verb
        if verb == 'take': print("Taken.")
        if verb == 'drop': print("Dropped.")
        if verb == 'put': print(f"You put the {action.noun.name} on/in the {action.second.name}.")
        if verb == 'open': print("Opened.")
        if verb == 'close': print("Closed.")
        if verb == 'lock': print("Locked.")
        if verb == 'unlock': print("Unlocked.")
        if verb == 'wear': print("You put it on.")
        if verb == 'eat': print("You eat it. Delicious.")
        if verb == 'enter': print(f"You get into the {action.noun.name}.")

        if verb == 'ask':
             topic = action.topic
             resp = action.noun.topics.get(topic, "They have nothing to say about that.")
             print(f"\"{resp}\"")

        if verb == 'tell':
             # Simple echo for now
             print(f"You tell {action.noun.name} about {action.topic}. They listen politely.")

        if verb == 'look':
            self.world.look()

        if verb == 'inventory':
            self.world.show_inventory()

        if verb == 'examine':
            print(action.noun.get_description())

class Action:
    def __init__(self, verb, noun=None, second=None, topic=None):
        self.verb = verb
        self.noun = noun
        self.second = second
        self.topic = topic

class World:
    def __init__(self, data):
        self.entities = {}
        self.player_location = data['start_room']
        self.ai = AIClient(DM_CONFIG_FILE)
        self.rulebook = Rulebook(self)
        self.history = []

        # Create Player
        self.player_id = 'player'
        self.entities['player'] = Person('player', {'name': 'yourself', 'location': self.player_location}, self)

        self._load_data(data)

    def save_state_to_memory(self):
        return {
            'player_loc': self.entities['player'].location_id,
            'entities': {eid: e.to_state() for eid, e in self.entities.items()}
        }

    def load_state_from_memory(self, state):
        self.move_entity('player', state['player_loc'])
        for eid, s in state['entities'].items():
            if eid in self.entities: self.entities[eid].load_state(s)

    def _load_data(self, data):
        # 1. Load Rooms
        for scene in data.get('scenes', []):
            r = Room(scene['id'], scene, self)
            self.entities[r.id] = r

            # Contents
            for item in scene.get('contents', []):
                self._load_item(item, r.id)

        # 2. Doors
        for d_data in data.get('doors', []):
            d = Door(d_data['id'], d_data, self)
            self.entities[d.id] = d
            # Doors are technically "in" the rooms they connect, but visually distinct.
            # We handle them by reference in Room.exits usually.

        # 3. Off-stage
        for item in data.get('off_stage', []):
            self._load_item(item, 'off-stage')

        # 4. Wire Connections
        for scene in data.get('scenes', []):
            r = self.entities[scene['id']]
            if 'exits' in scene:
                for dir, info in scene['exits'].items():
                    target = info.get('target')
                    door_id = info.get('door')
                    if door_id:
                        r.exits[dir] = door_id
                        # Update door connections if not fully set
                        d = self.entities[door_id]
                        d.connections[r.id] = dir
                        if target:
                            # Also register the target side so we can cross
                            if target not in d.connections:
                                d.connections[target] = 'unknown'
                    elif target:
                        r.exits[dir] = target

    def _load_item(self, data, loc_id):
        kind = data.get('kind', 'thing')
        if kind == 'container': cls = Container
        elif kind == 'supporter': cls = Supporter
        elif kind == 'person': cls = Person
        elif kind == 'door': cls = Door
        elif kind == 'wearable': cls = Thing; data['properties'] = data.get('properties', {}); data['properties']['wearable'] = True
        elif kind == 'edible': cls = Thing; data['properties'] = data.get('properties', {}); data['properties']['edible'] = True
        else: cls = Thing

        # Initial location
        data['location'] = loc_id
        obj = cls(data['id'], data, self)
        self.entities[obj.id] = obj

        # Recursive contents
        if 'contents' in data:
            for child in data['contents']:
                self._load_item(child, obj.id)

        # Register in parent
        self.move_entity(obj.id, loc_id)

    def get_player(self):
        return self.entities['player']

    def get_player_room(self):
        # The player is in a room. Or in a container in a room.
        p = self.get_player()
        loc = p.location_id
        while loc in self.entities and self.entities[loc].kind != 'room':
             loc = self.entities[loc].location_id
        return self.entities.get(loc)

    def move_entity(self, obj_id, dest_id):
        if obj_id not in self.entities: return
        obj = self.entities[obj_id]

        # Remove from old
        if obj.location_id and obj.location_id in self.entities:
             try: self.entities[obj.location_id].contents.remove(obj_id)
             except: pass

        # Add to new
        obj.location_id = dest_id
        if dest_id in self.entities:
            self.entities[dest_id].contents.append(obj_id)

    def remove_entity(self, obj_id):
        if obj_id not in self.entities: return
        obj = self.entities[obj_id]
        if obj.location_id and obj.location_id in self.entities:
             try: self.entities[obj.location_id].contents.remove(obj_id)
             except: pass
        del self.entities[obj_id]

    def apply_effect(self, effect):
        t = effect.get('type')
        if t == 'move':
            self.move_entity(effect['target'], effect['destination'] if effect['destination'] != 'current_location' else self.get_player_room().id)
        elif t == 'set_property':
            if effect['target'] in self.entities:
                self.entities[effect['target']].set_prop(effect['property'], effect['value'])

    # --- Visibility & Accessibility ---

    def get_scope(self):
        # Everything visible to player
        # 1. Player inventory
        # 2. Room contents
        # 3. Recursive transparency
        scope = []
        p = self.get_player()

        # Inventory
        scope.extend(self._get_contents_recursive(p))

        # Room
        room = self.get_player_room()
        if room:
            scope.append(room)
            scope.extend(self._get_contents_recursive(room))

            # Doors
            for dir, target_id in room.exits.items():
                if target_id in self.entities:
                    scope.append(self.entities[target_id])

        return scope

    def _get_contents_recursive(self, parent):
        res = []
        for c_id in parent.contents:
            child = self.entities[c_id]
            res.append(child)
            # Recursion logic:
            # If open container, or supporter, or transparent container
            see_inside = False
            if child.kind == 'supporter': see_inside = True
            elif child.kind == 'container':
                 if child.has_prop('open') or child.has_prop('transparent'): see_inside = True

            if see_inside:
                res.extend(self._get_contents_recursive(child))
        return res

    def is_accessible(self, obj):
        # Can the player touch it?
        # Simplified: If it's in scope and not inside a closed transparent container (unless that container is in inventory?)
        # For now, assume Scope == Touch for most things, except strict closed containers.
        if obj.location_id == self.player_id: return True
        parent_id = obj.location_id
        while parent_id and parent_id != self.player_id and parent_id != self.get_player_room().id:
            parent = self.entities[parent_id]
            if parent.kind == 'container' and not parent.has_prop('open'):
                return False
            parent_id = parent.location_id
        return True

    def find_in_scope(self, name):
        scope = self.get_scope()
        # 1. Exact match
        for ent in scope:
            if ent.match_name(name): return ent
        # 2. Partial match (simple)
        for ent in scope:
            if name in ent.name.lower(): return ent
        return None

    # --- UI ---

    def look(self):
        room = self.get_player_room()
        print(f"**{room.name}**")
        print(room.description)

        # List contents
        # Don't list scenery or player
        visible = [self.entities[i] for i in room.contents if i != self.player_id and not self.entities[i].has_prop('scenery')]

        if visible:
            desc_list = []
            for item in visible:
                desc = item.name
                if item.kind == 'container':
                     if item.has_prop('open') and item.contents:
                         names = [self.entities[c].name for c in item.contents]
                         desc += " (containing " + ", ".join(names) + ")"
                     elif item.has_prop('open'):
                         desc += " (empty)"
                     elif item.has_prop('closed'):
                         desc += " (closed)"
                desc_list.append(desc)
            print("You see: " + ", ".join(desc_list))

        # Exits
        exits_str = []
        for d, t in room.exits.items():
            if t in self.entities: # It's a door
                door = self.entities[t]
                exits_str.append(f"{d} ({door.name})")
            else:
                exits_str.append(d)
        if exits_str:
            print("Exits: " + ", ".join(exits_str))

    def show_inventory(self):
        p = self.get_player()
        if not p.contents:
            print("You are carrying nothing.")
        else:
            names = []
            for i in p.contents:
                item = self.entities[i]
                name = item.name
                if item.has_prop('worn'): name += " (being worn)"
                names.append(name)
            print("You are carrying: " + ", ".join(names))

    def move_player(self, direction):
        room = self.get_player_room()
        if direction in room.exits:
            target = room.exits[direction]

            # If target is a door, check if open
            if target in self.entities and self.entities[target].kind == 'door':
                door = self.entities[target]
                if not door.has_prop('open'):
                    print(f"The {door.name} is closed.")
                    return
                # Find destination from door connections
                # door.connections = {roomA: dirA, roomB: dirB}
                # We want the 'other' room
                for r_id in door.connections:
                    if r_id != room.id:
                        self.move_entity(self.player_id, r_id)
                        self.look()
                        return
                print("The door leads nowhere?")
            else:
                # Direct connection
                self.move_entity(self.player_id, target)
                self.look()
        else:
            print("You can't go that way.")

    def parse(self, text):
        text = text.lower().strip()
        if not text: return

        # Save state for UNDO before any state-changing command
        # (For now, we save before EVERY command that isn't meta/undo to be safe,
        # or we rely on the command handling to know if it changes state.
        # A simple approach: save before everything, but that's heavy.
        # Better: Save before processing, unless it's a meta command.)

        meta_commands = ['save', 'load', 'undo', 'look', 'l', 'inventory', 'i', 'help']
        is_meta = text in meta_commands or text.split()[0] in meta_commands

        if not is_meta:
            self.history.append(self.save_state_to_memory())
            if len(self.history) > 10: self.history.pop(0)

        # 1. Directions
        dirs = {'n':'north','s':'south','e':'east','w':'west','u':'up','d':'down'}
        if text in dirs: text = dirs[text]
        if text in ['north','south','east','west','up','down']:
            self.move_player(text)
            return

        # 2. Tokenize
        tokens = text.split()
        verb = tokens[0]

        # Simple verbs
        if verb == 'undo':
            if not self.history:
                print("Nothing to undo.")
            else:
                state = self.history.pop()
                self.load_state_from_memory(state)
                print("Undone.")
                self.look()
            return

        if verb == 'look' or text == 'l': self.rulebook.process(Action('look')); return
        if verb == 'inventory' or text == 'i': self.rulebook.process(Action('inventory')); return
        if verb == 'wait' or text == 'z': print("Time passes."); return
        if verb == 'save': self.save_game(); return
        if verb == 'load': self.load_game(); return
        if verb == 'menu': print("Exiting to menu..."); return "menu"

        # Complex verbs
        # Patterns:
        # VERB NOUN (take sword)
        # VERB NOUN PREP NOUN (put sword in sack)
        # ASK NOUN ABOUT TOPIC

        if verb == 'ask' or verb == 'tell':
            if ' about ' in text:
                try:
                    target_name, topic = text[len(verb)+1:].split(' about ', 1)
                    target = self.find_in_scope(target_name)
                    self.rulebook.process(Action(verb, noun=target, topic=topic))
                    return
                except: pass

        # Prepositions for PUT / UNLOCK
        preps = [' in ', ' on ', ' with ']
        prep_found = None
        for p in preps:
             if p in text:
                 prep_found = p.strip()
                 break

        if prep_found:
            # SVOPO
            try:
                parts = text.split(f" {prep_found} ", 1)
                verb_phrase = parts[0].split(' ', 1)
                verb = verb_phrase[0]
                noun_str = verb_phrase[1] if len(verb_phrase) > 1 else ""
                second_str = parts[1]

                noun = self.find_in_scope(noun_str)
                second = self.find_in_scope(second_str)

                self.rulebook.process(Action(verb, noun=noun, second=second))
                return
            except: pass

        # SVO
        if len(tokens) > 1:
            noun_str = " ".join(tokens[1:])
            noun = self.find_in_scope(noun_str)
            self.rulebook.process(Action(verb, noun=noun))
            return

        # AI Fallback
        valid_cmds = ["look", "inventory", "take [item]", "drop [item]", "open [item]", "put [item] in [item]"]
        mapped = self.ai.map_command(text, valid_cmds)
        if mapped:
            print(f"[AI Interpreted: {mapped}]")
            self.parse(mapped)
        else:
            print("I didn't understand that.")

    def save_game(self):
        filename = f"{STORY_ID}.save"
        state = {
            'player_loc': self.entities['player'].location_id,
            'entities': {eid: e.to_state() for eid, e in self.entities.items()}
        }
        with open(filename, 'w') as f: json.dump(state, f)
        print(f"Saved to {filename}.")

    def load_game(self):
        filename = f"{STORY_ID}.save"
        try:
            with open(filename, 'r') as f: state = json.load(f)
            self.move_entity('player', state['player_loc'])
            for eid, s in state['entities'].items():
                if eid in self.entities: self.entities[eid].load_state(s)
            print(f"Loaded from {filename}.")
            self.look()
        except: print("No save file found.")

def main():
    game = World(GAME_DATA)

    title = GAME_DATA.get('title', 'Untitled')
    author = GAME_DATA.get('author', 'Anonymous')

    print(f"\n\"{title}\"")
    print(f"An Interactive Fiction by {author}")
    print("Release 1 / Lore Lock Engine\n")

    game.look()
    while True:
        try:
            cmd = input("> ")
            if cmd == "quit": break
            res = game.parse(cmd)
            if res == "menu": break
        except EOFError: break

if __name__ == "__main__":
    main()
