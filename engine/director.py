import random
import json
# NOTE: rich imports are mocked here as they are instantiated in main.py, 
# but we format the output string here to be rendered later.
# from rich.console import Console 
# from rich.panel import Panel
# from rich.box import SQUARE 
# from rich.padding import Padding

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
    # ... (resolve_check method remains the same)
    # ==========================================================
    def resolve_check(self, params):
        """
        The Dice Tower. Resolves ANY action requiring success/failure.
        Input: {"stat": "str", "target_dc": 15, "target_id": "bars", "consequences": {...}}
        Returns: [Result, TriggerResult, ...]
        """
        stat_name = params.get('stat', 'str')
        target_id = params.get('target_id')
        consequences = params.get('consequences', {})
        
        # --- DC LOOKUP ---
        db_dc = self._get_universal_object_dc(target_id, stat_name)
        target_dc = db_dc if db_dc is not None else params.get('target_dc', 10) 
        
        # A. CALCULATE MODIFIER
        stats = self.session['player'].get('stats', {})
        modifier = stats.get(stat_name, 0)

        # B. ROLL THE DICE (True Randomness)
        die_roll = random.randint(1, 20)
        total = die_roll + modifier

        # C. DETERMINE OUTCOME
        outcome = "FAILURE"
        if total >= target_dc:
            outcome = "SUCCESS"
        elif die_roll == 1:
            outcome = "CRITICAL_FAILURE"
        
        # D. APPLY CONSEQUENCES
        applied_effects = {}
        triggered_results = []
        
        # 1. Apply 'always' effects
        always_effects = consequences.get('always', {})
        triggered_actions = self._apply_effects(always_effects, applied_effects)
        triggered_results.extend(triggered_actions)
        
        # 2. Apply outcome-specific effects
        if outcome == "SUCCESS":
            success_effects = consequences.get('on_success', {})
            triggered_actions = self._apply_effects(success_effects, applied_effects)
            triggered_results.extend(triggered_actions)
        elif outcome == "FAILURE" or outcome == "CRITICAL_FAILURE":
            failure_effects = consequences.get('on_failure', {})
            triggered_actions = self._apply_effects(failure_effects, applied_effects)
            triggered_results.extend(triggered_actions)

        # E. CREATE INITIAL RESULT
        initial_result = {
            "event_type": "check_result",
            "mechanics": {
                "outcome": outcome,
                "roll_total": total,
                "die_face": die_roll,
                "target_dc": target_dc,
                "margin": total - target_dc,
                "applied_effects": applied_effects 
            },
            "context": {
                "stat_used": stat_name,
                "target_name": target_id,
                "target_current_tags": self._get_object_tags(target_id)
            }
        }
        
        # F. RETURN LIST OF RESULTS
        return [initial_result] + triggered_results

    # ==========================================================
    # 2. THE INVENTORY MANAGER (Fixed duplicate add)
    # ... (manage_inventory method remains the same)
    # ==========================================================
    def manage_inventory(self, params):
        """
        Input: {"action": "add", "item_id": "rusty_key"}
        Returns: A single result dictionary for internal use.
        """
        action = params.get('action')
        item_id = params.get('item_id')
        inventory = self.session['player']['inventory']

        if action == "add":
            # FIX: Only add the item if it's not already in the inventory.
            if item_id not in inventory:
                inventory.append(item_id)
                return self._return_inventory_result("inventory_add", {"item_id": item_id, "outcome": "SUCCESS"})
            else:
                # If it's already present, indicate NO_CHANGE.
                return self._return_inventory_result("inventory_add", {"item_id": item_id, "outcome": "NO_CHANGE"})
            
        elif action == "remove":
            if item_id in inventory:
                inventory.remove(item_id)
                return self._return_inventory_result("inventory_remove", {"item_id": item_id, "outcome": "SUCCESS"})
            else:
                return self._return_error("item_not_in_inventory")
        
        return self._return_error("invalid_action")

    # ==========================================================
    # 3. THE SCENE SHIFTER
    # ... (change_scene method remains the same)
    # ==========================================================
    def change_scene(self, params):
        """
        Input: {"direction": "north"}
        """
        direction = params.get('direction')
        current_room_id = self.session.get('current_scene')
        
        # A. LOOKUP EXITS
        room_data = self.db['scenes'].get(current_room_id, {})
        exits = room_data.get('exits', {})

        if direction not in exits:
            return [self._return_error("no_exit_that_way")]

        target_id = exits[direction]['target_id']
        is_locked = exits[direction].get('locked', False)

        # B. CHECK LOCKS
        if is_locked:
            key_needed = exits[direction].get('key_id')
            if key_needed and key_needed not in self.session['player']['inventory']:
                return [self._return_error("door_locked", {"key_needed": key_needed})]
            
        # C. UPDATE STATE
        self.session['current_scene'] = target_id
        
        # D. FETCH NEW CONTEXT 
        new_room_data = self.db['scenes'].get(target_id, {})
        
        # Returns a list containing a single scene_change event
        return [{
            "event_type": "scene_change",
            "data": {
                "outcome": "SUCCESS",
                "new_scene_id": target_id,
                "description": new_room_data.get('description', "A void."),
                "visible_objects": new_room_data.get('objects', [])
            }
        }]

    # ==========================================================
    # 4. THE STATS REPORTER (Direct Console Output)
    # ==========================================================
    def report_stats(self, params):
        """
        Returns a detailed report of the player's stats and inventory, formatted for direct console printing.
        """
        if params.get('target') != 'player':
            return self._return_error("invalid_target")

        player = self.session['player']
        
        # --- Python-side Formatting for Direct Console Output ---
        stats_text = f"[bold white]ATTRIBUTES:[/]\n"
        for stat, value in player.get('stats', {}).items():
            stats_text += f"  [bold cyan]{stat.upper()}:[/] {value}\n"
        
        stats_text += f"\n[bold white]HEALTH & STATUS:[/]\n"
        stats_text += f"  [bold red]HP:[/]{player.get('hp', 0)}/20\n"
        
        status_list = player.get('status_effects', [])
        stats_text += f"  [bold yellow]Status:[/]{', '.join(status_list) if status_list else 'Clear'}\n"
        
        stats_text += f"\n[bold white]INVENTORY:[/]\n"
        inventory_list = player.get('inventory', [])
        if inventory_list:
            inventory_counts = {}
            for item in inventory_list:
                inventory_counts[item] = inventory_counts.get(item, 0) + 1
            for item, count in inventory_counts.items():
                stats_text += f"  - {item.capitalize()} (x{count})\n"
        else:
            stats_text += "  (Empty)\n"
        
        # Return a dictionary containing the skip flag and the pre-formatted string
        return {
            "event_type": "stats_report", 
            "action_type": "report_stats",
            "mechanics": {"outcome": "INFO"},
            "formatted_output": stats_text, # Key for main.py to print directly
            "__skip_narration__": True # Crucial flag
        }


    # ==========================================================
    # 5. INTERNAL HELPERS
    # ==========================================================
    def execute(self, tool_command):
        """
        Master Router: Takes JSON command -> Runs Function
        Returns a LIST of results, handling chained actions.
        """
        tool = tool_command.get('tool')
        params = tool_command.get('parameters', {})

        if tool == 'resolve_check':
            return self.resolve_check(params)
        elif tool == 'manage_inventory':
            # This is an internal call, returns a single result dict, wrap in list for consistency
            result = self.manage_inventory(params)
            return [result] if result.get('event_type') != 'error' else [result]
        elif tool == 'change_scene':
            return self.change_scene(params)
        elif tool == 'report_stats': 
            # This returns the result directly, which includes the __skip_narration__ flag
            result = self.report_stats(params)
            return [result] if result.get('event_type') != 'error' else [result]
        else:
            # For unknown tools, return a list containing a single error result
            return [self._return_error("unknown_tool_call", {"tool": tool_command})] 

    def _apply_effects(self, effects, applied_effects):
        """Routes effects to the correct state update function and returns any triggered action results."""
        
        triggered_results = []

        # Player Effects
        if 'player_damage' in effects:
            damage = effects['player_damage']
            self._apply_player_effects({'damage': damage})
            applied_effects['player_damage'] = damage
        if 'player_heal' in effects:
            heal = effects['player_heal']
            self._apply_player_effects({'heal': heal})
            applied_effects['player_heal'] = heal
        if 'player_status_effect' in effects:
            status = effects['player_status_effect']
            if 'status_effects' not in self.session['player']:
                self.session['player']['status_effects'] = []
            if status not in self.session['player']['status_effects']:
                self.session['player']['status_effects'].append(status)
            applied_effects['player_status_effect'] = status

        # Object Effects (Tag manipulation and Triggers)
        if 'target_id' in effects:
            target_id = effects['target_id']
            add_tags = effects.get('add_tags', [])
            remove_tags = effects.get('remove_tags', [])
            
            # Apply object effects and capture any resulting triggers
            trigger_result = self._apply_object_effects(target_id, add_tags, remove_tags)
            if trigger_result:
                # The result here is the fully formatted narrative payload from the trigger
                triggered_results.append(trigger_result)
            
            # Record the object effects for the Narrator report
            applied_effects['object_tags_added'] = add_tags
            applied_effects['object_tags_removed'] = remove_tags
            
        return triggered_results
    
    def _apply_player_effects(self, effects):
        """Applies damage/healing effects to the player's session state."""
        player_state = self.session['player']
        if 'damage' in effects:
            player_state['hp'] = max(0, player_state.get('hp', 0) - effects['damage'])
        if 'heal' in effects:
            max_hp = 20
            player_state['hp'] = min(max_hp, player_state.get('hp', 0) + effects['heal'])
            
    def _apply_object_effects(self, target_id, add_tags, remove_tags):
        """Applies tag manipulation, checks for exit unlocks, and fires triggers."""
        obj, room_data = self._get_mutable_object_reference(target_id)
        if not obj or not room_data:
            return None

        tags = obj.get('tags', [])
        tags_removed = []
        triggered_action_result = None

        # 1. Apply Tags to Remove & CHECK TRIGGERS
        # Only check and fire if a tag is actually being removed.
        for tag_to_remove in remove_tags:
            if tag_to_remove in tags:
                
                # *** TRIGGER CHECK BEFORE REMOVAL ***
                mechanics = obj.get('mechanics', {})
                triggers = mechanics.get('on_tag_removed', {})
                
                if tag_to_remove in triggers and triggered_action_result is None:
                    
                    trigger_data = triggers[tag_to_remove]
                    action = trigger_data['action']
                    params = trigger_data['params']
                    
                    # Execute the triggered action (e.g., manage_inventory).
                    # self.execute returns a LIST of results, take the single result dict.
                    trigger_execution_results = self.execute({"tool": action, "parameters": params})
                    trigger_execution_result = trigger_execution_results[0]
                    
                    # If the result is a success (or NO_CHANGE if item was already added), we wrap it for narration
                    if trigger_execution_result.get('mechanics', {}).get('outcome') in ['SUCCESS', 'NO_CHANGE']:
                        
                        # --- FIX: Make the trigger one-time use by removing the rule ---
                        # We delete the entire trigger entry from the object's mechanics
                        mechanics['on_tag_removed'].pop(tag_to_remove, None)
                        
                        # Fix: This is where we create the final narratable payload.
                        triggered_action_result = {
                            "event_type": "triggered_action",
                            "action_type": action,
                            "mechanics": trigger_execution_result.get('mechanics', {}),
                            "context": {
                                "target_name": target_id,
                                "trigger_description": trigger_data.get('description', f"Trigger for {action} completed."),
                                "action_params": params
                            }
                        }
                    # We continue removing the tag below regardless of trigger success/failure.
                
                # Now remove the tag from the database
                tags.remove(tag_to_remove)
                tags_removed.append(tag_to_remove)
                
        
        # 2. Apply Tags to Add
        for tag in add_tags:
            if tag not in tags:
                tags.append(tag)
                
        # 3. Universal Exit Unlock Logic (based on 'exit_barrier' tag removal)
        if 'exit_barrier' in tags_removed:
            current_exits = room_data.get('exits', {})
            for _, exit_data in current_exits.items():
                if exit_data.get('locked', False) and exit_data.get('key_id') is None:
                    exit_data['locked'] = False
                    break

        return triggered_action_result

    def _get_mutable_object_reference(self, target_id):
        """Retrieves a mutable reference to the object dictionary in the current scene and the scene data."""
        if not target_id: return None, None
        current_room_id = self.session.get('current_scene')
        room_data = self.db['scenes'].get(current_room_id, {})
        
        room_objs = room_data.get('objects', [])
        for obj in room_objs:
            if obj['id'] == target_id:
                return obj, room_data
        return None, None
    
    def _get_universal_object_dc(self, target_id, stat_name):
        """
        Safely retrieves the DC for a check from object data, keyed by the stat name.
        The Director is universal and strictly expects the DC to be defined under
        obj.mechanics[stat_name].
        """
        obj, _ = self._get_mutable_object_reference(target_id)
        if not obj:
            return None
        
        # Universal lookup: checks the mechanics block directly for the stat name
        dc = obj.get('mechanics', {}).get(stat_name)
        
        return dc

    def _get_object_tags(self, target_id):
        """Safe DB lookup for tags."""
        obj, _ = self._get_mutable_object_reference(target_id)
        return obj.get('tags', []) if obj else []

    def _return_state_update(self, msg):
        return {"event_type": "state_update", "status": "SUCCESS", "message": msg}

    def _return_error(self, reason, details=None):
        return {
            "event_type": "error", 
            "status": "FAILURE", 
            "reason": reason, 
            "details": details or {}
        }
        
    def _return_inventory_result(self, action_type, data):
        """Standardized format for successful internal actions (triggers)."""
        return {
            "event_type": "inventory_result", # Changed to inventory_result for clarity
            "action_type": action_type,
            "mechanics": data,
            "context": {}
        }