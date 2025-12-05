# Lore Lock - Prison Break (Inform 7-Style Engine)

This project implements a robust text adventure engine and compiler inspired by Inform 7. It allows you to write interactive fiction in a structured YAML format and compile it into a standalone Python game with complex world modeling, action processing, and AI integration.

## Overview

"Prison Break" is a short text adventure showcasing the engine's capabilities. Escape a damp stone cell by solving puzzles, interacting with NPCs, and manipulating the environment.

## Features (Inform 7 Inspired)

The engine closely mimics the core architecture of Inform 7:

*   **Object Model:**
    *   **Things:** Portable objects (`take`, `drop`).
    *   **Containers:** Can be opened, closed, locked, opaque, or transparent.
    *   **Supporters:** Tables/desks where items sit on top.
    *   **Doors:** Lockable, openable connections between rooms.
    *   **People:** NPCs that can be talked to (`ask`/`tell`).
    *   **Wearables & Edibles:** Clothing and Food.
*   **Action System:** Uses a 5-stage rulebook (`Before`, `Check`, `CarryOut`, `After`, `Report`) for flexible game logic.
*   **Parser:** Supports complex sentences (`put the red gem in the steel safe`, `unlock oak door with brass key`).
*   **AI Integration:** Fallback AI parser (OpenAI) translates unstructured natural language into valid game commands if strict parsing fails.

## Requirements

*   Python 3.x
*   PyYAML (`pip install pyyaml`)
*   (Optional) `OPENAI_API_KEY` in environment or `.env` for AI features.

## How to Compile

To generate the game and test suite from the story file:

```bash
python compiler.py prison_break.yaml
```

This will create:
*   `prison_break_game.py`: The playable game script.
*   `test_prison_break.py`: An automated test suite.

## How to Play

Run the generated game script:

```bash
python prison_break_game.py
```

### Commands
*   **Navigation**: `n`, `s`, `e`, `w`
*   **Interaction**: `take`, `drop`, `put X in Y`, `put X on Y`
*   **Doors**: `open`, `close`, `lock`, `unlock`
*   **Conversation**: `ask [person] about [topic]`, `tell [person] about [topic]`
*   **Meta**: `save`, `load`, `look`, `inventory`

## Testing

The project includes a comprehensive test suite defined in YAML stories:

```bash
python compiler.py test_containers.yaml && python test_test_containers.py
python compiler.py test_doors.yaml && python test_test_doors.py
python compiler.py test_conversation.yaml && python test_test_conversation.py
```

## Story Format (YAML)

The YAML file defines the world using an entity-component style:

```yaml
scenes:
  - id: "Lab"
    contents:
      - id: "glass box"
        kind: "container"
        properties: { transparent: true, closed: true }
        contents:
          - id: "gem"
```
