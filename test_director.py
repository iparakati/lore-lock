from engine.director import Director

# 1. MOCK DATA (The "Book")
campaign = {
    "scenes": {
        "cell": {
            "description": "A damp cell.", 
            "exits": {"north": {"target_id": "hallway", "locked": True, "key_id": "shiv"}},
            "objects": [{"id": "bars", "tags": ["rigid", "iron"]}]
        },
        "hallway": {"description": "Freedom!"}
    }
}

# 2. MOCK STATE (The "Save File")
session = {
    "current_scene": "cell",
    "player": {"inventory": [], "stats": {"str": 2}}
}

# 3. INITIALIZE
d = Director(campaign, session)
print("--- TEST 1: Breaking Bars (Should Fail) ---")
result = d.execute({
    "tool": "resolve_check", 
    "parameters": {"stat": "str", "target_dc": 20, "target_id": "bars"}
})
print(f"Roll: {result['mechanics']['roll_total']} | Outcome: {result['mechanics']['outcome']}")

print("\n--- TEST 2: Moving North (Should Fail - Locked) ---")
result = d.execute({
    "tool": "change_scene", 
    "parameters": {"direction": "north"}
})
print(f"Status: {result['status']} | Reason: {result.get('reason')}")

print("\n--- TEST 3: Cheat & Move (Add Key) ---")
d.execute({"tool": "manage_inventory", "parameters": {"action": "add", "item_id": "shiv"}})
result = d.execute({
    "tool": "change_scene", 
    "parameters": {"direction": "north"}
})
print(f"Status: {result.get('data', {}).get('outcome')} | Location: {result.get('data', {}).get('new_scene_id')}")