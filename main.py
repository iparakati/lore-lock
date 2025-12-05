import sys
import os
import time
import json
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.theme import Theme

# Import Engine Components
from engine.director import Director
from engine.listener import Listener
from engine.narrator import Narrator

# --- CONFIGURATION ---
CAMPAIGN_BASE_PATH = "data/campaigns"
DEFAULT_CAMPAIGN_ID = "prison_break"
DM_NOTE_PREFIX = "[DM NOTE:" # Define the prefix for filtering

# 1. SETUP THEME
# --- FIX: Defining custom_theme here ---
custom_theme = Theme({
    "info": "bold #b0d8e3",       # Pale Cyan
    "text": "default",            # Adaptive
    "dim": "dim",                 # Grey
    "warning": "bold #ffafaf",    # Soft red
    "success": "bold #a3be8c",    # Soft green
})

load_dotenv()
console = Console(theme=custom_theme)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def load_config():
    """
    Loads config.yaml or creates default if missing.
    """
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        default_yaml = """
# LORE-LOCK CONFIGURATION
# -----------------------
# We use gpt-5-nano for everything to keep it fast and cheap.
# You can change this to 'gpt-4o' if you want higher quality narration.

narrator_model: gpt-5-nano 
listener_model: gpt-5-nano
debug_mode: false
"""
        with open(config_path, "w") as f:
            f.write(default_yaml.strip())
            
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def load_campaign(campaign_id):
    """
    Loads and merges all YAML files for a given campaign ID.
    """
    campaign_path = os.path.join(CAMPAIGN_BASE_PATH, campaign_id)
    
    # Initialize the main campaign database structure
    campaign_db = {
        'manifest': {},
        'scenes': {},
        'assets': {}
    }
    
    # Load Manifest (Title, Starting Scene ID)
    with open(os.path.join(campaign_path, "manifest.yaml"), "r") as f:
        campaign_db['manifest'] = yaml.safe_load(f)
        
    # Load Scenes (Room definitions)
    with open(os.path.join(campaign_path, "scenes.yaml"), "r") as f:
        campaign_db['scenes'] = yaml.safe_load(f)
        
    # Load Assets (Items, NPCs, etc.)
    with open(os.path.join(campaign_path, "assets.yaml"), "r") as f:
        campaign_db['assets'] = yaml.safe_load(f)
        
    return campaign_db

# --- MOVED HELPER FUNCTION TO BE DEFINED BEFORE START_GAME ---
def get_listener_context(scene_data):
    """
    Extracts the minimalist object data (tags/mechanics) for the Listener's reasoning.
    """
    objects = scene_data.get('objects', [])
    raw_context = {}
    
    if objects:
        for obj in objects:
            # Provide ID, Tags, and Mechanics for full Listener context
            obj_context = {
                "tags": obj.get('tags', []),
                "mechanics": obj.get('mechanics', {})
            }
            # Use json.dumps for strict LLM consumption
            raw_context[obj.get('id')] = obj_context
            
    return json.dumps(raw_context, indent=2)

def show_welcome_screen():
    clear_screen()
    
    welcome_md = Markdown("""
    # ❖ LORE-LOCK
    
    The Neuro-Symbolic RPG Engine.
    
    > *Logic is Python. Creativity is AI.*
    """)

    console.print(Panel(
        welcome_md, 
        border_style="info",
        padding=(1, 2),
        width=60
    ))

    console.print("\n[dim]Select an option:[/dim]\n")

    menu_options = [
        ("1", f"Start New Campaign: {DEFAULT_CAMPAIGN_ID}"),
        ("D", "Toggle Debug Mode (current: Off)"), # Changed label based on config below
        ("2", "Load Saved Session"),
        ("3", "Campaign Creator"),
        ("4", "Quit")
    ]
    
    # Check current debug mode state for display
    current_config = load_config()
    debug_state = "On" if current_config.get('debug_mode', False) else "Off"
    
    menu_options[1] = ("D", f"Toggle Debug Mode (current: {debug_state})")


    for key, label in menu_options:
        console.print(f" [[info]{key}[/info]] {label}")

    print()
    # Add 'D' to choices
    choice = Prompt.ask(" >", choices=["1", "2", "3", "4", "D"], default="1")
    return choice

# ============================================
# GAME LOOP
# ============================================
def start_game(config):
    clear_screen()
    console.print(Panel("[info]LOADING CAMPAIGN...[/info]", border_style="info"))
    
    # 1. LOAD CAMPAIGN DATA (The "Campaign File" in memory)
    try:
        campaign = load_campaign(DEFAULT_CAMPAIGN_ID)
    except FileNotFoundError as e:
        console.print(Panel(f"[warning]ERROR: Campaign data not found.[/] Missing file: {e}", border_style="warning"))
        time.sleep(3)
        return
    except yaml.YAMLError as e:
        # Catch specific YAML errors if a file is malformed
        console.print(Panel(f"[warning]YAML STRUCTURE ERROR:[/]\nCheck your campaign files for indentation or syntax errors.\nDetails: {e}", border_style="warning"))
        time.sleep(5)
        return
    except Exception as e:
        console.print(Panel(f"[warning]CRITICAL LOAD ERROR:[/]\nFailed to load campaign data.\nDetails: {e}", border_style="warning"))
        time.sleep(5)
        return

    manifest = campaign['manifest']
    scenes = campaign['scenes']
    
    # 2. INITIALIZE SESSION STATE (The "Save File" in memory)
    starting_scene_id = manifest.get('starting_scene_id', list(scenes.keys())[0])
    
    session = {
        "current_scene": starting_scene_id,
        "player": {
            "inventory": [], 
            "stats": {"str": 10, "dex": 12, "int": 10},
            "hp": 20 # Starting HP
        },
        "world_state": {}
    }

    # 3. INITIALIZE ENGINE
    with console.status("[dim]Booting Director & Listener...[/dim]"):
        try:
            director = Director(campaign, session)
            
            # Initialize models based on config
            listener = Listener(model_name=config.get('listener_model', 'gpt-5-nano'))
            narrator = Narrator(model_name=config.get('narrator_model', 'gpt-5-nano'))
            time.sleep(1) 
        except Exception as e:
            console.print(Panel(f"[warning]ENGINE BOOT ERROR:[/]\nDirector or Listener initialization failed.\nDetails: {e}", border_style="warning"))
            time.sleep(5)
            return

    # 4. DEFINE TOOLS (The API for the Listener)
    allowed_tools = [
        {"name": "resolve_check", "description": "Roll dice for a skill check. Consequences are applied based on the outcome.", "parameters": {
            "stat": "str/dex/int", 
            "target_dc": "int", 
            "target_id": "str", 
            "consequences": {
                "type": "object", 
                "description": "A map defining effects for different outcomes.",
                "properties": {
                    "on_success": {"type": "object", "description": "Effects applied only on success. Can include object tag changes."},
                    "on_failure": {"type": "object", "description": "Effects applied only on failure. Can include player damage/status."},
                    "always": {"type": "object", "description": "Effects applied regardless of outcome (e.g., guaranteed player damage from a risky action)."}
                }
            }
        }},
        {"name": "manage_inventory", "description": "Add/Remove items", "parameters": {"action": "add/remove", "item_id": "str"}},
        {"name": "change_scene", "description": "Move area", "parameters": {"direction": "north/south/east/west"}},
        # NEW TOOL: Report Stats
        {"name": "report_stats", "description": "Report current player stats and inventory.", "parameters": {"target": "player", "report_type": "full"}}
    ]
    
    # 5. INITIAL SCENE SETUP
    current_scene_data = scenes.get(starting_scene_id, {"description": "Error: Scene not found."})
    
    # --- Context Filtering and Setup ---
    # 5a. Filter DM notes for player display (the public description)
    scene_desc_lines = current_scene_data.get('description', "Error: Scene not found.").split('\n')
    filtered_desc = '\n'.join([line for line in scene_desc_lines if not line.strip().startswith(DM_NOTE_PREFIX)])
    
    # Initialize Scene Summary Memory
    if 'scene_summary' not in session:
        session['scene_summary'] = filtered_desc # Initialize with filtered description
        
    console.print(Panel(
        f"[bold blue]{manifest.get('title', 'Unknown Campaign')}[/bold blue]",
        title="CAMPAIGN STARTED",
        border_style="info"
    ))
    console.print(f"\n[bold]SCENE: {current_scene_data.get('name', 'Starting Location')}[/bold]")
    console.print(f"\n{filtered_desc}") # Use filtered description here
    console.print("[dim]Type 'quit' to return to menu.[/dim]\n")

    # 6. THE LOOP
    is_debug = config.get('debug_mode', False)
    while True:
        user_input = Prompt.ask("[info]>[/info]")
        
        if user_input.lower() in ["quit", "exit", "menu"]:
            break
        
        # A. RETRIEVE CURRENT, REAL-TIME SCENE STATE FOR LISTENER
        current_scene_id = director.session.get('current_scene')
        current_scene_data = director.db['scenes'].get(current_scene_id, {})
        
        # 1. RAW MECHANICAL CONTEXT (for DCs, Tags, Mechanics lookup)
        raw_object_context = get_listener_context(current_scene_data)
        
        # 2. NARRATIVE SCENE SUMMARY (for general scene understanding)
        scene_summary = session.get('scene_summary', filtered_desc)


        # B. LISTENER PHASE (AI)
        with console.status("[dim]Parsing intent...[/dim]"):
            if is_debug:
                 # Show the memory and the mechanical truth being sent to the LLM
                 console.print(Panel(
                     f"[dim]Narrative Memory:[/]\n{scene_summary}\n\n[dim]Raw Object Data:[/]\n{raw_object_context}", 
                     title="[DEBUG: Listener Context Input]", 
                     border_style="dim"
                 ))
            
            # PASS BOTH CONTEXTS TO THE LISTENER
            command = listener.parse(user_input, allowed_tools, scene_summary, raw_object_context)
        
        if is_debug:
            console.print(Panel(f"[dim]Intent ({user_input}):[/]\n{json.dumps(command, indent=2)}", title="[DEBUG: Listener Tool Output]", border_style="dim"))

        # C. DIRECTOR PHASE (Logic)
        results = director.execute(command)
        
        if is_debug:
            console.print(Panel(f"[dim]Results (List):[/]\n{json.dumps(results, indent=2)}", title="[DEBUG: Director Output]", border_style="dim"))

        # D. NARRATE and RENDER (Combined API Call)
        
        # Check for immediate errors or bypass
        if results and results[0].get('event_type') == 'error':
             first_error = results[0]
             console.print(Panel(Markdown(f"[[SYSTEM ERROR]] {first_error.get('reason')}: {first_error.get('details')}"), title="Director Error", border_style="warning"))
             continue
        
        # --- NARRATOR BYPASS LOGIC (New) ---
        if results and results[0].get('__skip_narration__') is True:
            # Stats report: print the pre-formatted text directly and skip LLM call
            console.print(Panel(
                results[0].get('formatted_output', "[Director Error: Missing formatted output]"), 
                title="[Character Sheet]", 
                border_style="info"
            ))
            # Skip the rest of the narration section
            continue 
        # --- END BYPASS LOGIC ---


        combined_payload = {
            "initial_event": results[0],
            "triggered_events": results[1:] if len(results) > 1 else [],
            "combined_outcome": results[0].get('mechanics', {}).get('outcome', 'INFO'),
            "player_session_state": director.session['player']
        }
        
        # Check if scene changed (reset summary)
        if results[0].get('event_type') == 'scene_change':
            # Reset summary to the new raw description
            new_desc = results[0].get('data', {}).get('description', '')
            # Filter DM notes from the raw scene description before setting the summary
            new_desc_lines = new_desc.split('\n')
            filtered_new_desc = '\n'.join([line for line in new_desc_lines if not line.strip().startswith(DM_NOTE_PREFIX)])
            session['scene_summary'] = filtered_new_desc
        
        outcome = combined_payload["combined_outcome"]
        border_color = "success" if outcome == "SUCCESS" else ("warning" if outcome in ["FAILURE", "CRITICAL_FAILURE"] else "info")

        with console.status("[dim]Narrating chained results (1 API call)...[/dim]"):
            # Pass the CURRENT summary to the Narrator
            response = narrator.generate_narration(
                combined_payload, 
                original_intent=user_input, 
                current_scene_summary=session.get('scene_summary', filtered_desc)
            )
            
            # Handle the new JSON response format
            updated_summary_debug = None
            if isinstance(response, dict):
                story_text = response.get('narration', '[Narrator Error: Missing narration]')
                
                # Check if this was a stats report; if so, skip memory update and special styling
                if combined_payload['initial_event']['event_type'] == 'stats_report':
                    # This case should now be handled by the bypass logic above, but left as a safety.
                    pass 
                else:
                    # UPDATE THE SESSION SUMMARY for non-stats events
                    session['scene_summary'] = response.get('updated_scene_summary', session['scene_summary'])
                    
                    # --- Prepare Debug Output ---
                    if is_debug:
                        updated_summary_debug = Panel(f"[dim]New Scene Summary:[/]\n{session['scene_summary']}", title="[DEBUG: Updated Memory]", border_style="dim")
            else:
                story_text = str(response) # Fallback if text is returned on error

        
        console.print(Panel(Markdown(story_text), title=f"The Narrator ({outcome})", border_style=border_color))
        
        # --- PRINT DEBUG MEMORY AFTER NARRATION ---
        if updated_summary_debug:
            console.print(updated_summary_debug)

        # Skip the standard HP line if we just reported stats (which includes HP)
        if combined_payload['initial_event']['event_type'] != 'stats_report':
            current_hp = director.session['player']['hp']
            current_status = director.session['player'].get('status_effects', [])
            status_line = f"Status: {', '.join(current_status)}" if current_status else "Status: Clear"
            console.print(f"[dim]Player HP: {current_hp}/20 | {status_line}[/dim]")


# ============================================
# MAIN
# ============================================
def main():
    # Load Config
    config = load_config()

    if not os.getenv("OPENAI_API_KEY"):
        console.print("\n[warning]WARNING:[/] No API Key found in .env file.")
        console.print("[dim]The Director will not be able to summon the Narrator.[/dim]")
        Prompt.ask("Press Enter to continue anyway...")
        
    def toggle_debug(current_config):
        """Toggles the debug_mode flag in config.yaml."""
        config_path = "config.yaml"
        current_config['debug_mode'] = not current_config.get('debug_mode', False)
        with open(config_path, "w") as f:
            yaml.dump(current_config, f, default_flow_style=False)
        clear_screen()
        console.print(Panel(
            f"[info]DEBUG MODE:[/][bold]{' ON' if current_config['debug_mode'] else ' OFF'}[/bold]", 
            border_style="info"
        ))
        time.sleep(1)

    while True:
        # Re-load config to get the latest debug state for the menu label
        config = load_config()
        choice = show_welcome_screen()
        
        if choice == "1":
            start_game(config) 
        elif choice.upper() == "D":
            toggle_debug(config)
        elif choice == "2":
            console.print("\n[dim]No saved sessions found.[/dim]")
            time.sleep(1)
        elif choice == "3":
            console.print("\n[dim]Creator module is offline.[/dim]")
            time.sleep(1)
        elif choice == "4":
            console.print("\nGoodbye.")
            sys.exit()

if __name__ == "__main__":
    main()