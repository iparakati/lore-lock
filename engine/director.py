import random

class Director:
    def __init__(self, campaign_db, session_state):
        """
        The Director is the STATE MACHINE.
        It does not generate text. It calculates numbers and updates JSON.
        """
        self.db = campaign_db
        self.session = session_state

    # ==========================================================
    # 1. THE UNIVERSAL RESOLVER (Physics & Skills)
    # ==========================================================
    def resolve_check(self, params):
        """
        The Dice Tower. Resolves ANY action requiring success/failure.
        Input: {"stat": "str", "target_dc": 15, "target_id": "iron_bars"}
        """
        stat_name = params.get('stat', 'str')
        target_dc = params.get('target_dc', 10)
        target_id = params.get('target_id')

        # A. CALCULATE MODIFIER
        # Fetch stats from session. Default to 0 if missing.
        stats = self.session['player'].get('stats', {})
        modifier = stats.get(stat_name, 0)

        # B. ROLL THE DICE (True Randomness)
        die_roll = random.randint(1, 20)
        total = die_roll + modifier

        # C. DETERMINE OUTCOME
        if total >= target_dc:
            outcome = "SUCCESS"
        elif die_roll == 1:
            outcome = "CRITICAL_FAILURE"
        else:
            outcome = "FAILURE"

        # D. FETCH CONTEXT (Why did I fail?)
        target_tags = self._get_object_tags(target_id)
        
        # E. RETURN PAYLOAD (No Prose, just Data)
        return {
            "event_type": "check_result",
            "mechanics": {
                "outcome": outcome,
                "roll_total": total,
                "die_face": die_roll,
                "target_dc": target_dc,
                "margin": total - target_dc
            },
            "context": {
                "stat_used": stat_name,
                "target_name": target_id,
                "target_tags": target_tags
            }
        }

    # ==========================================================
    # 2. THE INVENTORY MANAGER
    # ==========================================================
    def manage_inventory(self, params):
        """
        Input: {"action": "add", "item_id": "rusty_key"}
        """
        action = params.get('action')
        item_id = params.get('item_id')
        inventory = self.session['player']['inventory']

        if action == "add":
            inventory.append(item_id)
            return self._return_state_update(f"Item added: {item_id}")
            
        elif action == "remove":
            if item_id in inventory:
                inventory.remove(item_id)
                return self._return_state_update(f"Item removed: {item_id}")
            else:
                return self._return_error("item_not_in_inventory")
        
        return self._return_error("invalid_action")

    # ==========================================================
    # 3. THE SCENE SHIFTER (Turning the Page)
    # ==========================================================
    def change_scene(self, params):
        """
        Input: {"direction": "north"}
        """
        direction = params.get('direction')
        current_room_id = self.session.get('current_scene')
        
        # A. LOOKUP EXITS
        # We look into the static campaign database
        room_data = self.db['scenes'].get(current_room_id, {})
        exits = room_data.get('exits', {})

        if direction not in exits:
            return self._return_error("no_exit_that_way")

        target_id = exits[direction]['target_id']
        is_locked = exits[direction].get('locked', False)

        # B. CHECK LOCKS
        if is_locked:
            key_needed = exits[direction].get('key_id')
            if key_needed not in self.session['player']['inventory']:
                return self._return_error("door_locked", {"key_needed": key_needed})

        # C. UPDATE STATE
        self.session['current_scene'] = target_id
        
        # D. FETCH NEW CONTEXT (The Page Turn)
        new_room_data = self.db['scenes'].get(target_id, {})
        
        return {
            "event_type": "scene_change",
            "data": {
                "outcome": "SUCCESS",
                "new_scene_id": target_id,
                "description": new_room_data.get('description', "A void."),
                "visible_objects": new_room_data.get('objects', [])
            }
        }

    # ==========================================================
    # 4. INTERNAL HELPERS
    # ==========================================================
    def execute(self, tool_command):
        """
        Master Router: Takes JSON command -> Runs Function
        """
        tool = tool_command.get('tool')
        params = tool_command.get('parameters', {})

        if tool == 'resolve_check':
            return self.resolve_check(params)
        elif tool == 'manage_inventory':
            return self.manage_inventory(params)
        elif tool == 'change_scene':
            return self.change_scene(params)
        else:
            return self._return_error("unknown_tool_call", {"tool": tool})

    def _get_object_tags(self, target_id):
        """Safe DB lookup for tags."""
        if not target_id: return []
        
        current_room = self.session.get('current_scene')
        # Check static campaign data
        room_objs = self.db['scenes'].get(current_room, {}).get('objects', [])
        for obj in room_objs:
            if obj['id'] == target_id:
                return obj.get('tags', [])
        return []

    def _return_state_update(self, msg):
        return {"event_type": "state_update", "status": "SUCCESS", "message": msg}

    def _return_error(self, reason, details=None):
        return {
            "event_type": "error", 
            "status": "FAILURE", 
            "reason": reason, 
            "details": details or {}
        }