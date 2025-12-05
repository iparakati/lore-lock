import json
import os
from openai import OpenAI

class Listener:
    def __init__(self, model_name="gpt-5-nano"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model_name 

    def parse(self, user_input, allowed_tools, scene_summary, raw_object_context):
        """
        Maps user intent to a tool call using the full scene context.
        """
        system_prompt = f"""
        ROLE: You are the Game Engine Interface, responsible for parsing intent into executable logic.
        TASK: Map the user's intent to one of the Allowed Tools, using the provided context to determine stat checks, DCs, and consequences.
        
        ### CURRENT GAME CONTEXT
        1. **Scene Narrative Summary (State Memory):** "{scene_summary}"
        2. **Raw Mechanical Object Data (Truth):** {raw_object_context}
        
        ### ALLOWED TOOLS
        {json.dumps(allowed_tools, indent=2)}
        
        ### RULES
        1. Output **VALID JSON ONLY**.
        2. **STRICT JSON FORMAT (CRITICAL):** The root object MUST contain exactly two keys: "tool" (which holds the tool name string) and "parameters" (which holds the parameter object).
        3. **ACTION LOGIC:** Use the **Raw Mechanical Object Data** to determine the correct 'target_id', 'stat', and 'target_dc'. Use the **Scene Narrative Summary** to verify if an action makes sense (e.g., if the summary says 'The slab is gone', don't propose moving it).
        4. **TAG CHANGE LOGIC:** When proposing a permanent state change (in 'on_success'), you MUST check the 'Raw Mechanical Object Data' for the current tags and only propose removing tags that are currently present.
        5. **DM NOTES**: The scene description may include sensitive DM notes. **NEVER** expose the text of the DM notes in the output JSON.
        
        
        EXAMPLE OUTPUT (Use tool 'report_stats' for user input like 'stats' or 'inventory'):
        {{
          "tool": "report_stats",
          "parameters": {{ "target": "player", "report_type": "full" }}
        }}
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                response_format={"type": "json_object"}, 
                temperature=1
            )
            
            content = response.choices[0].message.content
            return json.loads(content)

        except Exception as e:
            if "Invalid API key" in str(e):
                error_msg = "OpenAI API Key is invalid or missing."
            else:
                error_msg = str(e)
            
            print(f"[Listener Error] {error_msg}")
            
            return {"tool": "error", "reason": "Listener AI Failure", "details": error_msg}