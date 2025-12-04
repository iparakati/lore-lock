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

    def generate_narration(self, director_result, original_intent=""): 
        
        # --- 1. EXTRACT DATA FOR ROLL STRING ---
        
        roll_data = director_result.get('mechanics', {})
        context_data = director_result.get('context', {})
        
        roll_total = roll_data.get('roll_total', '??')
        die_face = roll_data.get('die_face', '??')
        target_dc = roll_data.get('target_dc', '??')
        outcome = roll_data.get('outcome', 'INFO')
        stat_name = context_data.get('stat_used', 'STAT')
        
        try:
            # Calculate modifier (Total - Die Face)
            modifier = roll_total - die_face
        except TypeError:
            modifier = '??'

        # Construct the deterministic roll line for the output display
        roll_string = f"**{stat_name.upper()} Check: d20 ({die_face}) + {modifier} vs DC {target_dc} ({outcome})**"

        # 2. THE SYSTEM PROMPT (Strict Constraints)
        system_prompt = f"""
        ROLE: You are the Dungeon Master.
        TASK: Narrate the outcome of the player's action based STRICTLY on the Engine Report.

        ### USER INTENT
        The player originally asked to: "{original_intent}"
        
        ### UNIVERSAL CONSISTENCY RULE (Anti-Hallucination)
        * **DO NOT INVENT:** Use only the elements and tags provided in the report. If a detail is not present (e.g., color, sound, specific NPCs), assume it is absent or minimal.
        * **BREVITY IS LAW:** Your narrative must be **1 to 2 sentences** long. This constraint overrides all temptation to elaborate.
        * **CONTEXT FIX:** Ensure your narrative directly addresses the player's request (e.g., if they asked to 'find the shiv', confirm they found it, or confirm why they failed to find it).
        
        ### OUTPUT FORMAT
        1. Start by including the following Roll String exactly as provided:
           {roll_string}
        2. Immediately follow on the next paragraph with immersive prose.
        
        NARRATION RULES:
        - If target tags are present, integrate them (e.g., 'rigid iron').
        - If outcome is FAILURE, state what the target did NOT do (e.g., "The bars did not yield").
        """

        # 3. API CALL
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
            # Note: The temperature fix is applied by removing the temperature parameter above.
            return f"[Narrator Error] {str(e)}"