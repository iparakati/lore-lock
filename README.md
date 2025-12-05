# Lore Lock - Prison Break (Inform 7-Style Engine)

This project implements a robust text adventure engine and compiler inspired by Inform 7. It allows you to write interactive fiction in a structured YAML format and compile it into a standalone Python game with complex world modeling, action processing, and AI integration.

## Overview

"Prison Break" is a short text adventure showcasing the engine's capabilities. Escape a damp stone cell by solving puzzles, interacting with NPCs, and manipulating the environment.

## Directory Structure

*   `src/`: Contains the compiler logic (`compiler.py`).
*   `stories/yaml/`: Source YAML story files (naming convention: `story_<name>.yaml`).
*   `stories/games/`: Compiled Python games (naming convention: `game_<name>.py`).
*   `stories/tests/`: Generated test suites (naming convention: `test_<name>.py`).

## Features (Inform 7 Inspired)

The engine closely mimics the core architecture of Inform 7:

*   **Object Model:** Things, Containers, Supporters, Doors, People, Wearables, Edibles.
*   **Action System:** 5-stage rulebook (`Before`, `Check`, `CarryOut`, `After`, `Report`).
*   **Parser:** Supports complex sentences (`put the red gem in the steel safe`).
*   **AI Integration:** Fallback AI parser.

## Requirements

*   Python 3.x
*   PyYAML (`pip install pyyaml`)
*   (Optional) `OPENAI_API_KEY` in environment or `.env` for AI features.

## How to Compile & Run

### Single Story

To generate a game and test suite from a specific story file:

```bash
python src/compiler.py stories/yaml/story_prison_break.yaml
```

This will create:
*   `stories/games/game_prison_break.py`
*   `stories/tests/test_prison_break.py`

Run the game:
```bash
python stories/games/game_prison_break.py
```

Run the test:
```bash
python stories/tests/test_prison_break.py
```

### Bulk Compile & Test

To compile ALL stories and run ALL tests (regression testing):

```bash
python src/compiler.py --all
```

## Story Format (YAML)

The YAML file defines the world using an entity-component style. See `stories/yaml/` for examples.
