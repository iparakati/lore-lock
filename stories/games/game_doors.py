
import sys
import json
import os
import urllib.request
import urllib.error
import re
import random

# Data injected by compiler
GAME_DATA = {'title': 'Door Test', 'purpose': 'Test door functionality: locking, unlocking with keys, opening, closing, and bidirectional travel.', 'scenes': [{'id': 'Hall', 'name': 'Hallway', 'contents': [{'id': 'brass key', 'name': 'brass key'}], 'exits': {'east': {'target': 'Bedroom', 'door': 'oak door'}}}, {'id': 'Bedroom', 'name': 'Master Bedroom'}], 'doors': [{'id': 'oak door', 'name': 'oak door', 'locked': True, 'key': 'brass key'}], 'start_room': 'Hall', 'test_sequence': ['east', 'take brass key', 'unlock oak door with brass key', 'open oak door', 'east', 'look'], 'win_condition': {'type': 'location', 'target': 'Bedroom'}}
STORY_ID = "doors"

DM_CONFIG_FILE = "dm_config.yaml"

# ==========================================
# GAME IO
# ==========================================
class GameIO:
    def __init__(self):
        self.history = []
        self.last_input = None
        self.current_turn_output = []

    def write(self, message):
        print(message)
        self.current_turn_output.append(str(message))

    def log_input(self, text):
        if self.last_input is not None:
             self.history = ["User: " + self.last_input, "System: " + " ".join(self.current_turn_output)]

        self.last_input = text
        self.current_turn_output = []

    def get_history_str(self):
        return "\n".join(self.history)

# ==========================================
# AI CLIENT
# ==========================================
class AIClient:
    def __init__(self, config_file):
        self.enabled = False
        self.config = {}
        self._load_env()
        self.api_key = os.environ.get("OPENAI_API_KEY")

        config_path = self._find_file(config_file)
        if self.api_key and config_path:
            try:
                import yaml
                with open(config_path, 'r') as f:
                    self.config = yaml.safe_load(f)
                self.enabled = True
            except ImportError:
                print("Warning: PyYAML not installed, AI features disabled.")
            except Exception as e:
                print(f"Warning: Could not load DM config: {e}")
        elif not self.api_key:
            pass

    def _find_file(self, filename):
        if os.path.exists(filename): return filename
        path = filename
        for _ in range(3):
            path = os.path.join("..", path)
            if os.path.exists(path): return path
        return None

    def _load_env(self):
        env_path = self._find_file(".env")
        if env_path:
            try:
                with open(env_path, "r") as f:
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

    def map_command(self, user_input, valid_commands, history, context):
        if not self.enabled: return None

        system_prompt = self.config.get('system_prompt', "You are a helpful AI.")
        model = self.config.get('model', 'gpt-5-nano')
        temperature = self.config.get('temperature', 1)

        valid_cmds_str = "\n".join([f"- {cmd}" for cmd in valid_commands])

        prompt = f"Translate the user's natural language into one of these standard formats:\n{valid_cmds_str}\n\n"
        prompt += f"Current Location Context:\n{context}\n\n"
        prompt += f"Recent History:\n{history}\n"

        user_msg = f"User Input: {user_input}\n\n{prompt}"

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
        self.contents = []
        self.kind = data.get('kind', 'thing')
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
        defaults = {
            'portable': True, 'scenery': False, 'lit': False,
            'wearable': False, 'edible': False, 'pushable': False
        }
        for k, v in defaults.items():
            if k not in self.properties: self.properties[k] = v

class Room(Entity):
    def __init__(self, id, data, world):
        super().__init__(id, data, world)
        self.kind = 'room'
        self.properties['lit'] = True
        self.exits = {}

class Container(Thing):
    def __init__(self, id, data, world):
        super().__init__(id, data, world)
        defaults = {
            'openable': True, 'open': False, 'locked': False,
            'lockable': False, 'transparent': False, 'enterable': False
        }
        for k, v in defaults.items():
            if k not in self.properties: self.properties[k] = v

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
        self.properties['enterable'] = False
        self.properties['scenery'] = True
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
        self.connections = data.get('connections', {})
        self.key_id = data.get('key', None)
        self.properties['portable'] = False

        if 'locked' in data: self.properties['locked'] = data['locked']
        if 'open' in data: self.properties['open'] = data['open']

        defaults = {'open': False, 'locked': False, 'openable': True}
        for k, v in defaults.items():
            if k not in self.properties: self.properties[k] = v

        if self.properties['locked']: self.properties['lockable'] = True

    def get_description(self):
        desc = self.description
        if self.has_prop('locked'): desc += " It is locked."
        elif self.has_prop('open'): desc += " It is open."
        else: desc += " It is closed."
        return desc

class Person(Thing):
    def __init__(self, id, data, world):
        super().__init__(id, data, world)
        self.kind = 'person'
        self.properties['alive'] = True
        self.properties['portable'] = False
        self.topics = data.get('topics', {})

class Rulebook:
    def __init__(self, world):
        self.world = world

    def process(self, action):
        verb = action.verb

        # 1. Before/Instead
        if self.run_custom_rules(action, 'before'): return True
        if self.run_custom_rules(action, 'instead'): return True

        # 2. Check / Carry Out / Report Dispatch
        check_f = getattr(self, f"check_{verb}", None)
        carry_f = getattr(self, f"carry_out_{verb}", None)
        report_f = getattr(self, f"report_{verb}", None)

        if not check_f and not carry_f and not report_f:
            # Verb not handled by standard rules
            return False

        if check_f:
            res = check_f(action)
            if res == "FALLBACK": return False
            if not res: return True # Handled failure

        if carry_f:
            carry_f(action)

        if self.run_custom_rules(action, 'after'): return True

        if report_f:
            report_f(action)

        return True

    def run_custom_rules(self, action, hook_type):
        targets = []
        if action.noun: targets.append(action.noun)
        if action.second: targets.append(action.second)
        targets.append(self.world.get_player_room())

        for obj in targets:
            for rule in obj.interactions:
                if rule.get('verb') == action.verb and rule.get('type') == hook_type:
                    ctx = {
                        'world': self.world, 'action': action,
                        'player': self.world.get_player(),
                        'item': obj, 'items': self.world.entities
                    }
                    cond = rule.get('condition', 'True')
                    try:
                        if eval(cond, {}, ctx):
                            if 'message' in rule: self.world.io.write(rule['message'])
                            for eff in rule.get('actions', []):
                                self.world.apply_effect(eff)
                            return True
                    except Exception as e:
                        self.world.io.write(f"Rule Error: {e}")
        return False

    # --- TAKE ---
    def check_take(self, action):
        p = self.world.get_player()
        if not action.noun: self.world.io.write("Take what?"); return False
        if action.noun.id == p.id: self.world.io.write("You can't take yourself."); return False
        if not action.noun.has_prop('portable'): self.world.io.write("That's fixed in place."); return False
        if action.noun.location_id == p.id: self.world.io.write("You already have that."); return False
        if not self.world.is_accessible(action.noun): self.world.io.write("You can't reach it."); return False
        return True

    def carry_out_take(self, action):
        self.world.move_entity(action.noun.id, self.world.get_player().id)
        if action.noun.has_prop('worn'): action.noun.set_prop('worn', False)

    def report_take(self, action):
        self.world.io.write("Taken.")

    # --- DROP ---
    def check_drop(self, action):
        p = self.world.get_player()
        if not action.noun: self.world.io.write("Drop what?"); return False
        if action.noun.location_id != p.id: self.world.io.write("You aren't carrying that."); return False
        return True

    def carry_out_drop(self, action):
        self.world.move_entity(action.noun.id, self.world.player_location)
        if action.noun.has_prop('worn'): action.noun.set_prop('worn', False)

    def report_drop(self, action):
        self.world.io.write("Dropped.")

    # --- PUT ---
    def check_put(self, action):
        p = self.world.get_player()
        if not action.noun: self.world.io.write("Put what?"); return False
        if not action.second: self.world.io.write("Put it where?"); return False
        if action.noun.location_id != p.id: self.world.io.write("You aren't carrying that."); return False
        if action.noun.id == action.second.id: self.world.io.write("You can't put something inside itself."); return False
        if not action.second.has_prop('open') and not action.second.has_prop('enterable') and action.second.kind == 'container':
            self.world.io.write(f"The {action.second.name} is closed."); return False
        return True

    def carry_out_put(self, action):
         self.world.move_entity(action.noun.id, action.second.id)
         if action.noun.has_prop('worn'): action.noun.set_prop('worn', False)

    def report_put(self, action):
         self.world.io.write(f"You put the {action.noun.name} on/in the {action.second.name}.")

    # --- ENTER ---
    def check_enter(self, action):
         if not action.noun: self.world.io.write("Enter what?"); return False
         if not action.noun.has_prop('enterable'): self.world.io.write("That's not something you can enter."); return False
         return True

    def carry_out_enter(self, action):
        self.world.move_entity(self.world.get_player().id, action.noun.id)

    def report_enter(self, action):
        self.world.io.write(f"You get into the {action.noun.name}.")

    # --- INVENTORY ---
    def check_inventory(self, action): return True
    def report_inventory(self, action): self.world.show_inventory()

    # --- LOOK ---
    def check_look(self, action): return True
    def report_look(self, action): self.world.look()

    # --- EXAMINE ---
    def check_examine(self, action):
        if not action.noun: self.world.io.write("Examine what?"); return False
        return True
    def report_examine(self, action):
        self.world.io.write(action.noun.get_description())

    # --- OPEN ---
    def check_open(self, action):
        if not action.noun: self.world.io.write("Open what?"); return False
        if not action.noun.has_prop('openable'): self.world.io.write("That's not something you can open."); return False
        if action.noun.has_prop('locked'): self.world.io.write("It is locked."); return False
        if action.noun.has_prop('open'): self.world.io.write("It is already open."); return False
        return True

    def carry_out_open(self, action):
        action.noun.set_prop('open', True)

    def report_open(self, action):
        self.world.io.write("Opened.")
        self.world.io.write(action.noun.get_description())

    # --- CLOSE ---
    def check_close(self, action):
        if not action.noun: self.world.io.write("Close what?"); return False
        if not action.noun.has_prop('openable'): self.world.io.write("That's not something you can close."); return False
        if not action.noun.has_prop('open'): self.world.io.write("It is already closed."); return False
        return True

    def carry_out_close(self, action):
        action.noun.set_prop('open', False)

    def report_close(self, action):
        self.world.io.write("Closed.")

    # --- LOCK ---
    def check_lock(self, action):
        if not action.noun: self.world.io.write("Lock what?"); return False
        if not action.noun.has_prop('lockable'): self.world.io.write("That doesn't have a lock."); return False
        if action.noun.has_prop('locked'): self.world.io.write("It's already locked."); return False
        if action.noun.has_prop('open'): self.world.io.write("Close it first."); return False
        if not action.second: self.world.io.write("Lock it with what?"); return False
        if action.noun.key_id != action.second.id and action.noun.key_id != action.second.name:
            self.world.io.write("That key doesn't fit."); return False
        return True

    def carry_out_lock(self, action):
        action.noun.set_prop('locked', True)

    def report_lock(self, action):
        self.world.io.write("Locked.")

    # --- UNLOCK ---
    def check_unlock(self, action):
        if not action.noun: self.world.io.write("Unlock what?"); return False
        if not action.noun.has_prop('lockable'): self.world.io.write("That doesn't have a lock."); return False
        if not action.noun.has_prop('locked'): self.world.io.write("It's already unlocked."); return False
        if not action.second: self.world.io.write("Unlock it with what?"); return False
        if action.noun.key_id != action.second.id and action.noun.key_id != action.second.name:
            self.world.io.write("That key doesn't fit."); return False
        return True

    def carry_out_unlock(self, action):
        action.noun.set_prop('locked', False)

    def report_unlock(self, action):
        self.world.io.write("Unlocked.")

    # --- WEAR ---
    def check_wear(self, action):
        p = self.world.get_player()
        if not action.noun: self.world.io.write("Wear what?"); return False
        if not action.noun.has_prop('wearable'): self.world.io.write("You can't wear that."); return False
        if action.noun.location_id != p.id: self.world.io.write("You aren't holding it."); return False
        if action.noun.has_prop('worn'): self.world.io.write("You are already wearing it."); return False
        return True

    def carry_out_wear(self, action):
        action.noun.set_prop('worn', True)

    def report_wear(self, action):
        self.world.io.write("You put it on.")

    # --- EAT ---
    def check_eat(self, action):
        p = self.world.get_player()
        if not action.noun: self.world.io.write("Eat what?"); return False
        if not action.noun.has_prop('edible'): self.world.io.write("That's not edible."); return False
        if action.noun.location_id != p.id: self.world.io.write("You aren't holding it."); return False
        return True

    def carry_out_eat(self, action):
        self.world.remove_entity(action.noun.id)

    def report_eat(self, action):
        self.world.io.write("You eat it. Delicious.")

    # --- ASK ---
    def check_ask(self, action):
         if not action.noun: self.world.io.write("Ask who?"); return False
         if action.noun.kind != 'person': self.world.io.write("You can't talk to that."); return False
         if action.topic not in action.noun.topics:
             self.world.io.write("They have nothing to say about that.")
             return False
         return True

    def report_ask(self, action):
         resp = action.noun.topics.get(action.topic, "")
         self.world.io.write(f'"{resp}"')

    # --- TELL ---
    def check_tell(self, action):
         if not action.noun: self.world.io.write("Tell who?"); return False
         if action.noun.kind != 'person': self.world.io.write("You can't talk to that."); return False
         return True

    def report_tell(self, action):
         self.world.io.write(f"You tell {action.noun.name} about {action.topic}. They listen politely.")

    # --- TALK ---
    def check_talk(self, action):
         target = action.noun or action.second
         if not target: self.world.io.write("Talk to who?"); return False
         if target.kind != 'person': self.world.io.write("You can't talk to that."); return False
         return True

    def report_talk(self, action):
         target = action.noun or action.second
         self.world.io.write(f"To converse, try 'ask {target.name} about [topic]' or 'tell {target.name} about [topic]'.")

    # --- PUSH ---
    def check_push(self, action):
        if not action.noun: self.world.io.write("Push what?"); return False
        return True

    def report_push(self, action):
        self.world.io.write("Nothing happens.")

    # --- PULL ---
    def check_pull(self, action):
        if not action.noun: self.world.io.write("Pull what?"); return False
        return True

    def report_pull(self, action):
        self.world.io.write("Nothing happens.")

    # --- GO ---
    def check_go(self, action): pass

class Action:
    def __init__(self, verb, noun=None, second=None, topic=None):
        self.verb = verb
        self.noun = noun
        self.second = second
        self.topic = topic

class World:
    def __init__(self, data):
        self.io = GameIO()
        self.entities = {}
        self.player_location = data['start_room']
        self.ai = AIClient(DM_CONFIG_FILE)
        self.rulebook = Rulebook(self)
        self.history = []

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
        for scene in data.get('scenes', []):
            r = Room(scene['id'], scene, self)
            self.entities[r.id] = r
            for item in scene.get('contents', []):
                self._load_item(item, r.id)

        for d_data in data.get('doors', []):
            d = Door(d_data['id'], d_data, self)
            self.entities[d.id] = d

        for item in data.get('off_stage', []):
            self._load_item(item, 'off-stage')

        for scene in data.get('scenes', []):
            r = self.entities[scene['id']]
            if 'exits' in scene:
                for dir, info in scene['exits'].items():
                    if isinstance(info, str):
                        target = info
                        door_id = None
                    else:
                        target = info.get('target')
                        door_id = info.get('door')

                    if door_id:
                        r.exits[dir] = door_id
                        d = self.entities[door_id]
                        d.connections[r.id] = dir
                        if target and target not in d.connections:
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

        data['location'] = loc_id
        obj = cls(data['id'], data, self)
        self.entities[obj.id] = obj

        if 'contents' in data:
            for child in data['contents']:
                self._load_item(child, obj.id)

        self.move_entity(obj.id, loc_id)

    def get_player(self):
        return self.entities['player']

    def get_player_room(self):
        p = self.get_player()
        loc = p.location_id
        while loc in self.entities and self.entities[loc].kind != 'room':
             loc = self.entities[loc].location_id
        return self.entities.get(loc)

    def move_entity(self, obj_id, dest_id):
        if obj_id not in self.entities: return
        obj = self.entities[obj_id]
        if obj.location_id and obj.location_id in self.entities:
             try: self.entities[obj.location_id].contents.remove(obj_id)
             except: pass
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

    def get_scope(self):
        scope = []
        p = self.get_player()
        scope.extend(self._get_contents_recursive(p))
        room = self.get_player_room()
        if room:
            scope.append(room)
            scope.extend(self._get_contents_recursive(room))
            for dir, target_id in room.exits.items():
                if target_id in self.entities:
                    scope.append(self.entities[target_id])
        return scope

    def _get_contents_recursive(self, parent):
        res = []
        for c_id in parent.contents:
            child = self.entities[c_id]
            res.append(child)
            see_inside = False
            if child.kind == 'supporter': see_inside = True
            elif child.kind == 'container':
                 if child.has_prop('open') or child.has_prop('transparent'): see_inside = True

            if see_inside:
                res.extend(self._get_contents_recursive(child))
        return res

    def is_accessible(self, obj):
        if obj.location_id == self.player_id: return True
        parent_id = obj.location_id
        while parent_id and parent_id != self.player_id and parent_id != self.get_player_room().id:
            parent = self.entities[parent_id]
            if parent.kind == 'container' and not parent.has_prop('open'):
                return False
            parent_id = parent.location_id
        return True

    def find_in_scope(self, name):
        if not name: return None
        scope = self.get_scope()
        for ent in scope:
            if ent.match_name(name): return ent
        for ent in scope:
            if name in ent.name.lower(): return ent
        return None

    def get_current_context(self):
        room = self.get_player_room()
        scope = self.get_scope()

        context_lines = []
        context_lines.append(f"Location: {room.name}")

        visible_names = []
        for e in scope:
            if e.id == 'player': continue
            name = e.name
            if e.has_prop('locked'): name += " (locked)"
            elif e.has_prop('closed'): name += " (closed)"
            elif e.has_prop('open'): name += " (open)"
            visible_names.append(name)
        context_lines.append(f"Visible: {', '.join(visible_names)}")

        for e in scope:
            if e.kind == 'person' and e.topics:
                topics = ", ".join(e.topics.keys())
                context_lines.append(f"Person '{e.name}' Topics: {topics}")

        return "\n".join(context_lines)

    def look(self):
        room = self.get_player_room()
        self.io.write(f"**{room.name}**")
        self.io.write(room.description)

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
            self.io.write("You see: " + ", ".join(desc_list))

        exits_str = []
        for d, t in room.exits.items():
            if t in self.entities:
                door = self.entities[t]
                exits_str.append(f"{d} ({door.name})")
            else:
                exits_str.append(d)
        if exits_str:
            self.io.write("Exits: " + ", ".join(exits_str))

    def show_inventory(self):
        p = self.get_player()
        if not p.contents:
            self.io.write("You are carrying nothing.")
        else:
            names = []
            for i in p.contents:
                item = self.entities[i]
                name = item.name
                if item.has_prop('worn'): name += " (being worn)"
                names.append(name)
            self.io.write("You are carrying: " + ", ".join(names))

    def move_player(self, direction):
        room = self.get_player_room()
        if direction in room.exits:
            target = room.exits[direction]
            if target in self.entities and self.entities[target].kind == 'door':
                door = self.entities[target]
                if not door.has_prop('open'):
                    if not door.has_prop('locked'):
                         self.io.write(f"(First opening the {door.name})")
                         door.set_prop('open', True)
                    else:
                         self.io.write(f"The {door.name} is closed.")
                         return
                for r_id in door.connections:
                    if r_id != room.id:
                        self.move_entity(self.player_id, r_id)
                        self.look()
                        return
                self.io.write("The door leads nowhere?")
            else:
                self.move_entity(self.player_id, target)
                self.look()
        else:
            self.io.write("You can't go that way.")

    def parse(self, text):
        text = text.lower().strip()
        if not text: return

        for w in ['the ', 'a ', 'an ']:
            text = text.replace(f" {w}", " ")
            if text.startswith(w): text = text[len(w):]

        text = text.replace('talk to ', 'talk ')

        self.io.log_input(text)

        meta_commands = ['save', 'load', 'undo', 'look', 'l', 'inventory', 'i', 'help']
        is_meta = text in meta_commands or text.split()[0] in meta_commands

        if not is_meta:
            self.history.append(self.save_state_to_memory())
            if len(self.history) > 10: self.history.pop(0)

        dirs = {'n':'north','s':'south','e':'east','w':'west','u':'up','d':'down'}
        if text in dirs: text = dirs[text]
        if text in ['north','south','east','west','up','down']:
            self.move_player(text)
            return

        if text.startswith("go ") or text.startswith("walk "):
            parts = text.split(" ", 1)
            if len(parts) > 1:
                direction = parts[1]
                if direction in dirs: direction = dirs[direction]
                if direction in ['north','south','east','west','up','down']:
                    self.move_player(direction)
                    return

        tokens = text.split()
        verb = tokens[0]

        if verb == 'insert' or verb == 'place': verb = 'put'
        if verb == 'read': verb = 'examine'
        if verb == 'shift' or verb == 'shove': verb = 'push'

        if verb == 'look' and len(tokens) > 1:
            if ' around' in text:
                verb = 'look'
                tokens = ['look']
            elif ' at ' in text:
                verb = 'examine'
                text = text.replace('look at ', 'examine ')
            elif ' inside ' in text:
                verb = 'examine'
                text = text.replace('look inside ', 'examine ')
            elif ' in ' in text:
                verb = 'examine'
                text = text.replace('look in ', 'examine ')
            elif ' under ' in text:
                verb = 'examine'
                text = text.replace('look under ', 'examine ')
            if verb == 'examine':
                tokens = text.split()

        if verb == 'undo':
            if not self.history: self.io.write("Nothing to undo.")
            else:
                state = self.history.pop()
                self.load_state_from_memory(state)
                self.io.write("Undone.")
                self.look()
            return

        if (verb == 'look' or text == 'l') and len(tokens) == 1: self.rulebook.process(Action('look')); return
        if verb == 'inventory' or text == 'i': self.rulebook.process(Action('inventory')); return
        if verb == 'wait' or text == 'z': self.io.write("Time passes."); return
        if verb == 'save': self.save_game(); return
        if verb == 'load': self.load_game(); return
        if verb == 'menu': self.io.write("Exiting to menu..."); return "menu"

        if verb == 'ask' or verb == 'tell':
            if ' about ' in text:
                try:
                    target_name, topic = text[len(verb)+1:].split(' about ', 1)
                    target = self.find_in_scope(target_name)
                    if self.rulebook.process(Action(verb, noun=target, topic=topic)):
                        return
                except: pass

        preps = [' in ', ' on ', ' with ', ' to ']
        prep_found = None
        for p in preps:
             if p in text:
                 prep_found = p.strip()
                 break

        if prep_found:
            try:
                parts = text.split(f" {prep_found} ", 1)
                verb_phrase = parts[0].split(' ', 1)
                verb = verb_phrase[0]
                noun_str = verb_phrase[1] if len(verb_phrase) > 1 else ""
                second_str = parts[1]
                noun = self.find_in_scope(noun_str)
                second = self.find_in_scope(second_str)
                if self.rulebook.process(Action(verb, noun=noun, second=second)):
                    return
            except: pass

        if len(tokens) >= 1:
            noun_str = " ".join(tokens[1:])
            noun = self.find_in_scope(noun_str)
            if noun or len(tokens) == 1:
                if self.rulebook.process(Action(verb, noun=noun)):
                    return

        # AI Fallback - Dynamic
        std_verbs = set()
        for m in dir(self.rulebook):
            if m.startswith("check_"):
                std_verbs.add(m[6:])

        for e in self.entities.values():
            for rule in e.interactions:
                if 'verb' in rule: std_verbs.add(rule['verb'])

        valid_cmds = []
        for v in std_verbs:
             valid_cmds.append(f"{v} [noun]")

        valid_cmds.append("put [item] in [container]")
        valid_cmds.append("put [item] on [supporter]")
        valid_cmds.append("lock [item] with [key]")
        valid_cmds.append("unlock [item] with [key]")
        valid_cmds.append("ask [person] about [topic]")
        valid_cmds.append("tell [person] about [topic]")
        valid_cmds.append("go [direction]")

        context = self.get_current_context()
        history = self.io.get_history_str()

        mapped = self.ai.map_command(text, valid_cmds, history, context)
        if mapped:
            if mapped.lower().strip() == text:
                self.io.write("I understand, but I can't do that right now.")
            else:
                self.io.write(f"[AI Interpreted: {mapped}]")
                self.parse(mapped)
        else:
            self.io.write("I didn't understand that.")

    def check_win(self):
        win = GAME_DATA.get('win_condition')
        if win and win.get('type') == 'location':
            if self.get_player_room().id == win['target']:
                self.io.write("\n*** YOU HAVE WON ***")
                self.io.write("*** The End ***")
                return True
        return False

    def save_game(self):
        filename = f"{STORY_ID}.save"
        state = {
            'player_loc': self.entities['player'].location_id,
            'entities': {eid: e.to_state() for eid, e in self.entities.items()}
        }
        with open(filename, 'w') as f: json.dump(state, f)
        self.io.write(f"Saved to {filename}.")

    def load_game(self):
        filename = f"{STORY_ID}.save"
        try:
            with open(filename, 'r') as f: state = json.load(f)
            self.move_entity('player', state['player_loc'])
            for eid, s in state['entities'].items():
                if eid in self.entities: self.entities[eid].load_state(s)
            self.io.write(f"Loaded from {filename}.")
            self.look()
        except: self.io.write("No save file found.")

def main():
    game = World(GAME_DATA)

    title = GAME_DATA.get('title', 'Untitled')
    author = GAME_DATA.get('author', 'Anonymous')

    game.io.write(f"\n\"{title}\"")
    game.io.write(f"An Interactive Fiction by {author}")
    game.io.write("Release 1 / Lore Lock Engine\n")

    game.look()
    while True:
        try:
            cmd = input("> ")
            if cmd == "quit": break
            res = game.parse(cmd)
            if res == "menu": break
            if game.check_win(): break
        except EOFError: break

if __name__ == "__main__":
    main()
