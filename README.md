# Lore Lock - Prison Break (Inform 7-Style Engine)

This project implements a robust text adventure engine and compiler inspired by Inform 7. It allows you to write interactive fiction in a structured YAML format and compile it into a standalone Python game with complex world modeling, action processing, and AI integration.

## Overview

"Prison Break" is a short text adventure showcasing the engine's capabilities. Escape a damp stone cell by solving puzzles, interacting with NPCs, and manipulating the environment.

## Directory Structure

*   `play.py`: Main entry point for playing stories on the fly.
*   `src/`: Contains the compiler logic (`compiler.py`).
*   `stories/yaml/`: Source YAML story files (naming convention: `story_<name>.yaml`).
*   `stories/games/`: Compiled Python games (Ignored artifacts).
*   `stories/tests/`: Generated test suites (Ignored artifacts).

## Features (Inform 7 Inspired)

The engine closely mimics the core architecture of Inform 7:

*   **Object Model:** Things, Containers, Supporters, Doors, People, Wearables, Edibles.
*   **Action System:** 5-stage rulebook (`Before`, `Check`, `CarryOut`, `After`, `Report`).
*   **Meta-Commands:** `undo`, `save`, `load`.
*   **Parser:** Supports complex sentences (`put the red gem in the steel safe`).
*   **AI Integration:** Fallback AI parser.

## Requirements

*   Python 3.x
*   PyYAML (`pip install pyyaml`)
*   (Optional) `OPENAI_API_KEY` in environment or `.env` for AI features.

## How to Play

To browse and play any story in `stories/yaml/` without generating files:

Run the game:
```bash
python play.py
```

## How to Compile & Test

To compile all stories and run their regression tests:

```bash
python src/compiler.py --all
```

This will generate game and test scripts in `stories/games/` and `stories/tests/` (which are gitignored) and run them.

## Story Format (YAML)

The YAML file defines the world using an entity-component style. See `stories/yaml/` for examples and `AGENTS.md` for detailed documentation.
