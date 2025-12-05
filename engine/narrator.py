import os
import json
from openai import OpenAI

class Narrator:
    def __init__(self, model_name="gpt-5-nano"):
        """
        The Narrator is the CREATIVE ENGINE, optimized for the Nano model.
        It takes the Director's 'Truth' (JSON) and writes the 'Story' (Text).
        """
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model_name

    def generate_narration(self, combined_payload, original_intent="", current_scene_summary=""): 
        
        initial_event = combined_payload.get('initial_event')
        triggered_events = combined_payload.get('triggered_events', [])
        
        if not initial_event:
             return {"narration": "[Narrator Error] No initial event provided.", "updated_scene_summary": current_scene_summary}

        # --- 1. EXTRACT DATA FOR ROLL STRING ---
        roll_data = initial_event.get('mechanics', {})
        
        # Check for stats report explicitly, as it has special handling
        is_stats_report = initial_event.get('event_type') == 'stats_report'
        
        if is_stats_report:
            # Stats report bypasses the standard roll display
            roll_string = ""
            outcome = "INFO"
        else:
            context_data = initial_event.get('context', {})
            roll_total = roll_data.get('roll_total', '??')
            die_face = roll_data.get('die_face', '??')
            target_dc = roll_data.get('target_dc', '??')
            outcome = roll_data.get('outcome', 'INFO')
            stat_name = context_data.get('stat_used', 'STAT')
            
            try:
                modifier = roll_total - die_face
            except TypeError:
                modifier = '??'
            
            roll_string = f"**{stat_name.upper()} Check: d20 ({die_face}) + {modifier} vs DC {target_dc} ({outcome})**"


        # --- 2. COMPILE TRIGGER DESCRIPTIONS ---
        trigger_descriptions = []
        for event in triggered_events:
            if event.get('event_type') == 'triggered_action':
                desc = event.get('context', {}).get('trigger_description')
                if desc:
                    trigger_descriptions.append(desc)
        
        # --- 3. THE SYSTEM PROMPT (Memory & State) ---
        system_prompt = f"""
        ROLE: You are the Dungeon Master.
        TASK: Generate a JSON response with two keys: "narration" and "updated_scene_summary".

        ### INPUT DATA
        1. **CURRENT SCENE SUMMARY (MEMORY):** "{current_scene_summary}"
        2. **PLAYER INTENT:** "{original_intent}"
        3. **ENGINE REPORT (TRUTH):** {json.dumps(combined_payload)}
        
        ### NARRATION RULES (For "narration" output)
        1. **PERSPECTIVE:** ALWAYS use the second-person ("You").
        2. **COHESION:** Weave the check result, damage/status, and trigger descriptions ({json.dumps(trigger_descriptions)}) into one passage.
        3. **CRITICAL RULE (PROSE):** **NEVER** use internal game terms in the final narrative. This includes: 'tag', 'mechanics', 'added', 'removed', 'outcome', 'conceals_item', 'rigid', 'heavy'. Describe physical reality only (e.g., say 'The slab is light now' instead of 'the heavy tag was removed').
        4. **SECRET RULE:** On FAILURE, do not reveal hidden items.
        5. **BREVITY:** 2-3 sentences.
        6. **STATS REPORT:** If event_type is 'stats_report', list the stats, inventory, and status effects clearly. Omit the roll string.
        
        ### MEMORY UPDATE RULES (For "updated_scene_summary" output)
        1. **GOAL:** Rewrite the CURRENT SCENE SUMMARY based ONLY on permanent changes from the ENGINE REPORT.
        2. **SCENE CHANGE:** If event_type is 'scene_change', the new summary is the new room's description, filtered of DM notes.
        3. **CRITICAL OBJECT UPDATE (IMPERATIVE):** Examine the 'applied_effects'. If the target object's tags were removed (e.g., 'rigid', 'conceals_item', 'exit_barrier'), you MUST rewrite the description of that object in the summary to reflect its new state (e.g., 'iron bars' becomes 'broken, bent iron bars' or 'stone slab' becomes 'moved stone slab').
           - *Example 1:* If 'rigid' and 'exit_barrier' were removed from 'bars', update the summary to state the 'north exit is now open/blocked by bent iron'.
           - *Example 2:* If 'conceals_item' was removed, update the summary to state the container is now 'empty' or 'moved aside'.
        4. **SKIP MEMORY UPDATE:** If event_type is 'stats_report', return the existing `current_scene_summary` unchanged.

        ### OUTPUT FORMAT
        --- BEGIN JSON OUTPUT ---
        {{
          "narration": "{roll_string} [immersive prose here, if applicable]",
          "updated_scene_summary": "[rewritten, concise scene memory here]"
        }}
        --- END JSON OUTPUT ---
        """

        # --- 4. API CALL ---
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Generate narration and update scene memory."}
                ],
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            
            # Clean and parse JSON response
            if content.strip().startswith('```json'):
                content = content.strip()[7:].strip()
            if content.strip().endswith('```'):
                content = content.strip()[:-3].strip()
            
            return json.loads(content)

        except Exception as e:
            # Handle potential JSON parsing error if the LLM fails to adhere to the format
            return {"narration": f"[Narrator/JSON Error] {str(e)}", "updated_scene_summary": current_scene_summary}