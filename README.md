# Lore Lock - Prison Break

This project implements a custom text adventure engine and compiler inspired by Inform 7. It allows you to write interactive fiction in a structured YAML format and compile it into a standalone Python game.

## Overview

"Prison Break" is a short text adventure where you must escape a damp stone cell. The story is defined in `prison_break.yaml` and compiled into `prison_break_game.py`.

## Requirements

*   Python 3.x
*   PyYAML (`pip install pyyaml`)

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
*   **Navigation**: `n`, `s`, `e`, `w` (or `north`, `south`, etc.)
*   **Interaction**: `take [item]`, `drop [item]`, `put [item] in [container]`
*   **Observation**: `look`, `examine [item]` (or `x [item]`)
*   **Doors**: `open [door]`, `unlock [door] with [key]`
*   **Inventory**: `i` or `inventory`

## Testing

The story file includes a "test sequence" that verifies the game can be completed. To run this verification:

```bash
python test_prison_break.py
```

## Story Format (YAML)

The `prison_break.yaml` file defines the game world. It supports:
*   **Rooms**: Descriptions and connections.
*   **Items**: Descriptions, locations, and aliases (partial matching is disabled).
*   **Containers**: Items that can hold other items (supports `open`/`close` logic).
*   **Doors**: Lockable connections between rooms.
*   **Interactions**: Custom scripts (e.g., pushing a slab to reveal an item).
