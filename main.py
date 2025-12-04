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

# 1. SETUP THEME
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
        ("1", "Start New Campaign"),
        ("2", "Load Saved Session"),
        ("3", "Campaign Creator"),
        ("4", "Quit")
    ]

    for key, label in menu_options:
        console.print(f" [[info]{key}[/info]] {label}")

    print()
    choice = Prompt.ask(" >", choices=["1", "2", "3", "4"], default="1")
    return choice

# ============================================
# GAME LOOP
# ============================================
def start_game(config):
    clear_screen()
    console.print(Panel("[info]INITIALIZING SESSION...[/info]", border_style="info"))
    
    # 1. MOCK DATA (The "Campaign File" in memory)
    campaign = {
        "scenes": {
            "cell": {
                "description": "A damp stone cell. Iron bars block the north exit.", 
                "exits": {
                    "north": {"target_id": "hallway", "locked": True, "key_id": "shiv"}
                },
                "objects": [
                    {"id": "bars", "tags": ["rigid", "iron"], "mechanics": {"break_dc": 20}}
                ]
            },
            "hallway": {
                "description": "Freedom! A long stone corridor.",
                "objects": []
            }
        }
    }
    
    # 2. MOCK STATE (The "Save File" in memory)
    session = {
        "current_scene": "cell",
        "player": {
            "inventory": [], 
            "stats": {"str": 10, "dex": 12, "int": 10} 
        },
        "world_state": {}
    }

    # 3. INITIALIZE ENGINE
    with console.status("[dim]Booting Director & Listener...[/dim]"):
        director = Director(campaign, session)
        
        # Initialize models based on config
        # NOTE: Ensure your Listener/Narrator classes accept 'model_name' in __init__
        listener = Listener(model_name=config.get('listener_model', 'gpt-5-nano'))
        narrator = Narrator(model_name=config.get('narrator_model', 'gpt-5-nano'))
        time.sleep(1) 

    # 4. DEFINE TOOLS (The API for the Listener)
    allowed_tools = [
        {"name": "resolve_check", "description": "Roll dice", "parameters": {"stat": "str/dex/int", "target_dc": "int"}},
        {"name": "manage_inventory", "description": "Add/Remove items", "parameters": {"action": "add/remove", "item_id": "str"}},
        {"name": "change_scene", "description": "Move area", "parameters": {"direction": "north/south/east/west"}}
    ]

    console.print(f"\n[bold]SCENE: {campaign['scenes']['cell']['description']}[/bold]")
    console.print("[dim]Type 'quit' to return to menu.[/dim]\n")

    # 5. THE LOOP
    while True:
        user_input = Prompt.ask("[info]>[/info]")
        
        if user_input.lower() in ["quit", "exit", "menu"]:
            break

        # A. LISTENER PHASE (AI)
        with console.status("[dim]Parsing intent...[/dim]"):
            command = listener.parse(user_input, allowed_tools)
        
        # Debug: Show command if debug_mode is True
        if config.get('debug_mode'):
            console.print(f"[dim]Command: {json.dumps(command)}[/dim]")

        # B. DIRECTOR PHASE (Logic)
        result = director.execute(command)
        
        # C. NARRATOR PHASE (Creative)
        with console.status("[dim]Narrating result...[/dim]"):
            story_text = narrator.generate_narration(result)
        
        # D. RENDER OUTPUT
        outcome = result.get('mechanics', {}).get('outcome', 'INFO')
        
        if outcome == "SUCCESS":
            border_color = "success"
        elif outcome == "FAILURE" or outcome == "CRITICAL_FAILURE":
            border_color = "warning"
        else:
            border_color = "info"

        console.print(Panel(
            Markdown(story_text), 
            title=f"The Narrator ({outcome})", 
            border_style=border_color
        ))

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

    while True:
        choice = show_welcome_screen()
        
        if choice == "1":
            start_game(config) 
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