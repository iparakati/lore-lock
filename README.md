# Lore-Lock

**A Neuro-Symbolic RPG Engine**

Lore-Lock is an experimental RPG engine that separates **Game Logic (Symbolic AI)** from **Narrative Generation (Neural AI)**. This architecture ensures that the rules of the game are enforced deterministically by code, while the storytelling is handled by creative Large Language Models (LLMs). This prevents "hallucinations" where an AI might invent rules or ignore game state.

> *Logic is Python. Creativity is AI.*

---

## 🧠 Philosophy

In traditional AI dungeon masters, the LLM often handles everything: the story, the dice rolls, and the inventory management. This leads to inconsistency—an AI might say you rolled a 20 when you actually rolled a 5, or let you use an item you don't have.

**Lore-Lock solves this by splitting the brain:**

1.  **The Director (Python):** The strict rulekeeper. It manages the database, calculates stats, rolls dice using `random`, and updates the JSON save file. It has *zero* creative writing ability.
2.  **The Narrator (LLM):** The storyteller. It receives a rigid data payload from the Director (e.g., `outcome: SUCCESS`, `margin: 5`) and turns it into prose. It *cannot* change the outcome, only describe it.

---

## 🔄 The Core Loop

The engine operates on a strict cyclical communication loop:

1.  **User**: Enters a natural language command (e.g., *"I want to smash the lock with my hammer"*).
2.  **Listener (LLM)**: Analyzes the user's intent and translates it into a strict JSON command for the engine.
    *   *Input:* "I want to smash the lock..."
    *   *Output:* `{"tool": "resolve_check", "parameters": {"stat": "str", "target_dc": 15}}`
3.  **Director (Python)**: Executes the command. It rolls the dice, checks the player's stats, and updates the game state.
    *   *Action:* `random.randint(1, 20) + 10`
    *   *Result:* `{"outcome": "SUCCESS", "roll": 22, "dc": 15}`
4.  **Narrator (LLM)**: Receives the data result and generates a description. It uses the numeric "margin of success" to determine the tone of the narration.
    *   *Input:* `SUCCESS`, `margin: 7`
    *   *Output:* "With a deafening clang, your hammer shatters the mechanism..."
5.  **User**: Reads the output and plans their next move.

---

## 📂 Project Structure

```
.
├── main.py                # The entry point and game loop controller
├── config.yaml            # Configuration for models (Listener/Narrator)
├── engine/
│   ├── director.py        # The State Machine (Logic & Physics)
│   ├── listener.py        # The Translator (NL -> JSON)
│   └── narrator.py        # The Storyteller (JSON -> Prose)
└── ...
```

### Key Components

*   **`main.py`**: Orchestrates the loop. It holds the "Mock Data" (Campaign) and "Mock State" (Session) in memory.
*   **`engine/director.py`**: Contains the `Director` class. It implements tools like `resolve_check`, `manage_inventory`, and `change_scene`. It returns raw data dictionaries.
*   **`engine/listener.py`**: Uses an LLM to map user text to one of the `allowed_tools` defined in `main.py`.
*   **`engine/narrator.py`**: Uses an LLM to turn the `Director`'s output into a story. It enforces constraints (e.g., "Do not repeat numbers").

---

## 🚀 Getting Started

### Prerequisites

*   Python 3.8+
*   An OpenAI API Key (or compatible)

### Installation

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Set up your environment variables:
    *   Copy `.env.example` to `.env`
    *   Add your `OPENAI_API_KEY` to `.env`

### Usage

Run the game:

```bash
python main.py
```

Select "Start New Campaign" to enter the demo cell. Type natural language commands to interact with the environment.

**Examples:**
*   "Look around."
*   "Try to break the bars."
*   "Go north."
