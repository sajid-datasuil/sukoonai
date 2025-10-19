import os
from typing import Dict, Any, Tuple, List
from openai import OpenAI

class LLMClient:
    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("SUKOON_LLM_MODEL", "gpt-4o-mini")
        self.temp = float(os.getenv("SUKOON_LLM_TEMP", "0.4"))
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def chat(self, system_prompt: str, user_text: str, lang_hint: str = "ur") -> Tuple[str, Dict[str, Any]]:
        """Return (text, usage)."""
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ]
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temp,
            max_tokens=400,
            messages=messages,
        )
        out = resp.choices[0].message.content
        usage = {
            "prompt_tokens": getattr(resp.usage, "prompt_tokens", None),
            "completion_tokens": getattr(resp.usage, "completion_tokens", None),
            "total_tokens": getattr(resp.usage, "total_tokens", None),
        }
        return out, usage
