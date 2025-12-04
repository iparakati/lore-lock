import os
import json
from openai import OpenAI

class Narrator:
    def __init__(self, model_name="gpt-5-nano"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model_name

    def generate_narration(self, director_result):
        
        # --- 1. EXTRACT DATA FOR ROLL STRING ---
        # We need to extract the stat name from the context block
        roll_data = director_result.get('mechanics', {})
        context_data = director_result.get('context', {})
        
        roll_total = roll_data.get('roll_total', '??')
        die_face = roll_data.get('die_face', '??')
        target_dc = roll_data.get('target_dc', '??')
        outcome = roll_data.get('outcome', 'INFO')
        
        # Get modifier by subtraction, since Director didn't send it directly
        try:
            modifier = roll_total - die_face
        except TypeError:
            modifier = '??'

        # Get the stat name
        stat_name = context_data.get('stat_used', 'STAT')

        # 2. CONSTRUCT THE ROLL STRING (Deterministic Formatting)
        # We add the STAT NAME and the MODIFIER to the string
        roll_string = f"**{stat_name.upper()} Check: d20 ({die_face}) + {modifier} vs DC {target_dc} ({outcome})**"

        # 3. THE NEW SYSTEM PROMPT (The Instruction)
        system_prompt = f"""
        ROLE: You are the Dungeon Master.
        TASK: Narrate the outcome of the player's action based STRICTLY on the Engine Report.
        
        OUTPUT FORMAT:
        1. **Start** by including the following Roll String exactly as provided:
           {roll_string}
        2. Immediately follow with immersive prose.
        3. Integrate target tags (like 'rigid' or 'iron') to explain the action.
        
        ### NARRATION CONSTRAINT (The Fix)
        * **Do NOT** repeat the total roll value, the DC, or the margin in the body of the narrative (e.g., avoid saying 'The roll total was 25' or 'beating the DC by 10').
        * Instead, use the margin to determine the *tone* (e.g., High Margin = effortless and clean, Low Margin = struggled and ungraceful).

        INPUT DATA RULES: ... (Continue with existing rules on tags, etc.)
        """

        # ... rest of the function remains the same ...
        user_message = f"ENGINE_REPORT: {json.dumps(director_result)}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            )
            
            return response.choices[0].message.content

        except Exception as e:
            return f"[Narrator Error] {str(e)}"