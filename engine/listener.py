import json
import os
from openai import OpenAI

class Listener:
    def __init__(self, model_name="gpt-5-nano"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model_name 

    def parse(self, user_input, allowed_tools):
        system_prompt = f"""
        ROLE: You are the Game Engine Interface.
        TASK: Map the user's intent to one of the Allowed Tools.
        
        ALLOWED TOOLS:
        {json.dumps(allowed_tools, indent=2)}
        
        RULES:
        1. Output valid JSON only.
        2. The root key MUST be "tool", followed by "parameters".
        3. For 'resolve_check' or 'combat_action', you MUST identify the object or entity being acted upon and pass it as the 'target_id' parameter. If the user input mentions an object, extract it.
        
        EXAMPLE OUTPUT (Context Extraction):
        {{
          "tool": "resolve_check",
          "parameters": {{ "stat": "strength", "target_dc": 15, "target_id": "bars" }}
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
            print(f"[Listener Error] {e}")
            return {"tool": "error", "reason": str(e)}