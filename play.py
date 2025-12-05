import os
import sys
import yaml
from src.compiler import generate_game_code

def main():
    stories_dir = "stories/yaml"
    if not os.path.exists(stories_dir):
        print(f"Error: {stories_dir} not found.")
        return

    while True:
        stories = [f for f in os.listdir(stories_dir) if f.endswith(".yaml")]
        if not stories:
            print("No stories found.")
            return

        print("\n=== Main Menu ===")
        print("Available Stories:")
        for i, story in enumerate(stories):
            print(f"{i + 1}. {story}")
        print("\nCommands:")
        print("- Type a number to play")
        print("- Type a name (partial match) to play")
        print("- Type 'quit' to exit")

        try:
            choice = input("\nSelect a story: ").strip().lower()
            if not choice: continue

            if choice == 'quit':
                print("Goodbye.")
                break

            selected_story = None

            # Numeric selection
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(stories):
                    selected_story = stories[idx]
            else:
                # Partial match
                matches = [s for s in stories if choice in s.lower()]
                if len(matches) == 1:
                    selected_story = matches[0]
                elif len(matches) > 1:
                    print(f"Ambiguous: {', '.join(matches)}")
                    continue
                else:
                    print("No match found.")
                    continue

            if selected_story:
                filepath = os.path.join(stories_dir, selected_story)
                print(f"\nLoading {selected_story}...")

                with open(filepath, 'r') as f:
                    data = yaml.safe_load(f)

                # Use filename without extension as story_id
                story_id = os.path.splitext(selected_story)[0]
                code = generate_game_code(data, story_id)

                # Execute the game code in a new namespace
                namespace = {}
                try:
                    exec(code, namespace)
                    if 'main' in namespace:
                        namespace['main']()
                    else:
                        print("Error: Could not find main() in generated code.")
                except Exception as e:
                    print(f"Runtime Error: {e}")
            else:
                print("Invalid selection.")

        except KeyboardInterrupt:
            print("\nExiting.")
            break

if __name__ == "__main__":
    main()
