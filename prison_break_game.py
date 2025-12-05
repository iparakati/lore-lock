
import sys
import json

# Data injected by compiler
GAME_DATA = {'title': 'Prison Break', 'start_room': 'Damp Stone Cell', 'rooms': {'Damp Stone Cell': {'name': 'Damp Stone Cell', 'description': 'You wake up on a hard slab in a damp stone cell. The air is cold and smells strongly of brine and mold.', 'items': ['stone slab', 'moldy box']}, 'Corridor': {'name': 'The Corridor', 'description': 'A dimly lit corridor, silent except for the drip of water. Torches flicker weakly on the walls.', 'items': []}}, 'doors': {'iron bars': {'name': 'iron bars', 'aliases': ['bars'], 'description': 'Thick iron bars blocking the way.', 'locked': True, 'key': 'rusty shiv', 'connections': {'Damp Stone Cell': 'north', 'Corridor': 'south'}, 'status_descriptions': {'locked': 'They appear to be locked.', 'closed': 'Iron bars block the north exit.'}}}, 'items': {'rusty shiv': {'name': 'rusty shiv', 'aliases': ['shiv'], 'description': 'A jagged piece of metal, sharp enough to cut but not meant for heavy fighting.', 'location': 'off-stage'}, 'stone slab': {'name': 'Stone Slab', 'aliases': ['slab'], 'description': 'It seems loose. You might be able to move it.', 'location': 'Damp Stone Cell', 'properties': {'fixed': False}, 'interactions': {'push': [{'condition': "items['rusty shiv'].location_id == 'off-stage'", 'message': 'You shift the heavy stone slab. Underneath, you discover a rusty shiv!', 'actions': [{'type': 'move', 'target': 'rusty shiv', 'destination': 'current_location'}, {'type': 'set_property', 'target': 'stone slab', 'property': 'fixed', 'value': True}]}], 'attack': [{'message': "It's stone. You'll only hurt your hands."}]}}, 'moldy box': {'kind': 'container', 'name': 'moldy box', 'aliases': ['box'], 'description': 'A rotting wooden box.', 'location': 'Damp Stone Cell', 'properties': {'open': False}}}, 'test_sequence': ['examine slab', 'push slab', 'take shiv', 'open box', 'put shiv in box', 'look', 'examine box', 'take shiv', 'unlock bars with shiv', 'open bars', 'north'], 'win_condition': {'type': 'location', 'target': 'Corridor'}}

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

class Room(Entity):
    def __init__(self, id, data, world):
        super().__init__(id, data, world)
        self.kind = 'room'
        # connections map direction -> room_id
        # In this schema, connections are often on doors, or implicit?
        # The schema puts items in rooms via 'location' property on items usually,
        # or 'items' list in room. We need to sync this.
        self.connections = {}

class Door(Entity):
    def __init__(self, id, data, world):
        super().__init__(id, data, world)
        self.kind = 'door'
        self.connections = data.get('connections', {}) # room_id -> direction
        self.locked = data.get('locked', False)
        self.key_id = data.get('key', None)
        self.closed = True # Doors start closed usually
        self.status_descriptions = data.get('status_descriptions', {})

class World:
    def __init__(self, data):
        self.entities = {}
        self.player_location = data['start_room']
        self.inventory = [] # List of IDs

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
            # Check kind
            kind = i_data.get('kind', 'thing')
            i = Entity(i_id, i_data, self)
            self.entities[i_id] = i

        # Build Hierarchy
        # 1. Put items in rooms/containers based on 'location'
        # 2. Also check 'items' list in room data if present (legacy support)

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
        # Remove from old parent
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
        # Recursive visibility check starting from room and inventory
        visible = []
        room = self.get_player_room()

        # Room contents
        visible.extend(self._get_contents_recursive(room))

        # Inventory contents
        for i_id in self.inventory:
            visible.append(self.entities[i_id])
            visible.extend(self._get_contents_recursive(self.entities[i_id]))

        # Doors connected to this room
        for d_id, ent in self.entities.items():
            if isinstance(ent, Door) and self.player_location in ent.connections:
                visible.append(ent)

        return visible

    def _get_contents_recursive(self, parent):
        res = []
        for child_id in parent.contents:
            child = self.entities[child_id]
            res.append(child)
            # If open container or supporter, recurse
            is_open_container = child.kind == 'container' and child.properties.get('open', False)
            is_supporter = child.kind == 'supporter'
            if is_open_container or is_supporter:
                res.extend(self._get_contents_recursive(child))
        return res

    def find_entity(self, name):
        # Search visible
        for ent in self.get_visible_entities():
            if ent.match_name(name):
                return ent
        return None

    def move_player(self, direction):
        # Check doors
        current_room_id = self.player_location
        for ent in self.entities.values():
            if isinstance(ent, Door) and current_room_id in ent.connections:
                if ent.connections[current_room_id] == direction:
                    if ent.locked:
                        print("The door is locked.")
                        return
                    if not ent.properties.get('is_open', True) and not ent.properties.get('open', False):
                        # Support both 'is_open' and standard 'open' prop
                        print("The door is closed.")
                        return

                    # Find dest
                    for r_id, d in ent.connections.items():
                        if r_id != current_room_id:
                            self.player_location = r_id
                            self.look()
                            return

        # Check direct connections (if any, not in this schema but good to have)
        print("You can't go that way.")

    def look(self):
        room = self.get_player_room()
        print(room.name)
        print(room.description)

        # List items
        # We only list top-level items in the room, or on supporters?
        # Standard IF: "You see X, Y and Z here."
        visible_items = [self.entities[i] for i in room.contents if self.entities[i].kind != 'scenery']
        if visible_items:
            names = []
            for item in visible_items:
                name = item.name
                if item.kind == 'container' and item.properties.get('open', False) and item.contents:
                    # simplistic content listing
                    c_names = [self.entities[c].name for c in item.contents]
                    name += " (containing " + ", ".join(c_names) + ")"
                names.append(name)
            print("You see " + ", ".join(names) + " here.")

    def parse_command(self, command):
        parts = command.lower().split()
        if not parts: return
        verb = parts[0]

        if verb in ['n', 'north', 's', 'south', 'e', 'east', 'w', 'west']:
            # normalize
            d = {'n':'north','s':'south','e':'east','w':'west'}.get(verb, verb)
            self.move_player(d)
            return

        if verb == 'look':
            self.look()
            return

        if verb in ['i', 'inventory']:
            if not self.inventory:
                print("You are carrying nothing.")
            else:
                names = [self.entities[i].name for i in self.inventory]
                print("You are carrying: " + ", ".join(names))
            return

        if len(parts) < 2:
            print("I don't understand that.")
            return

        noun = " ".join(parts[1:])

        # Handle "put X in Y"
        if verb == 'put':
            if ' in ' in noun:
                obj_name, container_name = noun.split(' in ')
                obj = self.find_entity(obj_name)
                cont = self.find_entity(container_name)
                if not obj: print("You don't have that."); return
                if not cont: print("You can't see that."); return

                if cont.kind != 'container': print("That's not a container."); return
                if not cont.properties.get('open', False): print("It's closed."); return

                # Move
                if obj.id in self.inventory:
                    self.inventory.remove(obj.id)
                self.move_entity(obj.id, cont.id)
                print(f"You put the {obj.name} in the {cont.name}.")
                return
            else:
                print("Put what in what?")
                return

        # Handle other verbs
        obj = self.find_entity(noun)

        # Try custom interactions first
        if obj and verb in obj.interactions:
             self.run_interaction(obj, verb)
             return

        if verb == 'examine' or verb == 'x':
            if obj:
                print(obj.get_description())
            else:
                print("You see nothing special.")
            return

        if verb == 'take':
            if not obj: print("You can't see that."); return
            if obj.kind == 'room': print("You can't take that."); return
            if obj.properties.get('fixed', False): print("It's fixed in place."); return

            # Remove from old loc
            if obj.id in self.inventory: print("You already have that."); return

            # Remove from world
            if obj.location_id and obj.location_id in self.entities:
                self.entities[obj.location_id].contents.remove(obj.id)

            self.inventory.append(obj.id)
            obj.location_id = 'inventory'
            print("Taken.")
            return

        if verb == 'open':
            if not obj: print("You can't see that."); return
            if obj.kind == 'door':
                if obj.locked: print("It's locked."); return
                obj.properties['open'] = True # generic prop
                print("Opened.")
            elif obj.kind == 'container':
                obj.properties['open'] = True
                print("Opened.")
            else:
                print("You can't open that.")
            return

        if verb == 'unlock':
            # Simplified parser: "unlock bars with shiv"
            # We need to split
            if ' with ' in noun:
                 target_name, key_name = noun.split(' with ')
                 target = self.find_entity(target_name)
                 key = None
                 # Find key in inventory
                 for i_id in self.inventory:
                     k = self.entities[i_id]
                     if k.match_name(key_name):
                         key = k
                         break

                 if not target: print("You can't see that."); return
                 if not key: print("You don't have that."); return

                 if target.kind == 'door':
                     # check key match (by ID or name)
                     if target.key_id == key.id or target.key_id == key.name:
                         target.locked = False
                         print("Unlocked.")
                     else:
                         print("It doesn't fit.")
                 else:
                     print("That doesn't seem to have a lock.")
            else:
                print("Unlock what with what?")
            return

        print("I don't understand that command.")

    def run_interaction(self, obj, verb):
        rules = obj.interactions[verb]
        for rule in rules:
            # Eval condition
            # We expose 'world', 'obj'
            items = self.entities # Alias for condition eval
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
            # target, destination
            # Resolve target
            t_id = action['target'] # Assumed ID
            # In simple schema, we might not have ID, so we search?
            # But the schema uses IDs in keys.
            if t_id not in self.entities: return

            dest = action['destination']
            if dest == 'current_location':
                self.move_entity(t_id, self.player_location)
            elif dest == 'inventory':
                 # remove from world
                 ent = self.entities[t_id]
                 if ent.location_id in self.entities:
                     self.entities[ent.location_id].contents.remove(t_id)
                 self.inventory.append(t_id)
                 ent.location_id = 'inventory'
            # support moving to container?
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
