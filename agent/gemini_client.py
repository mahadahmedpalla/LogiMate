"""
Production-grade Gemini Client using the official google-genai SDK.
Handles high-capacity API keys (AQ.... and AIza....), token pooling, and structured JSON output.
"""

import json
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types
from google.genai.errors import APIError


AVAILABLE_MODELS = [
    {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash (Fast & Stable — Recommended)"},
    {"id": "gemini-3.6-flash", "name": "Gemini 3.6 Flash (Latest Flagship)"},
    {"id": "gemini-3.5-flash", "name": "Gemini 3.5 Flash"},
    {"id": "gemini-3.8-flash", "name": "Gemini 3.8 Flash"},
    {"id": "gemini-3.7-flash", "name": "Gemini 3.7 Flash"},
    {"id": "custom", "name": "Custom Model..."},
]


class GeminiClient:
    """Official Google GenAI SDK wrapper for AI Logisim Controller."""

    def __init__(self, api_key: str = "", model_id: str = "gemini-2.5-flash"):
        self.api_key = api_key.strip()
        self.model_id = model_id.strip() or "gemini-2.5-flash"
        self._client: Optional[genai.Client] = None
        self._init_client()

    def _init_client(self):
        if self.api_key:
            try:
                self._client = genai.Client(api_key=self.api_key)
            except Exception:
                self._client = None
        else:
            self._client = None

    def set_credentials(self, api_key: str, model_id: Optional[str] = None):
        self.api_key = api_key.strip()
        if model_id:
            self.model_id = model_id.strip()
        self._init_client()

    def test_connection(self) -> Dict[str, Any]:
        """Validates credentials using the official SDK."""
        if not self.api_key:
            return {"success": False, "error": "API key is empty. Please enter your Gemini API key."}

        if not self._client:
            self._init_client()

        try:
            resp = self._client.models.generate_content(
                model=self.model_id,
                contents="Reply with 'OK' only.",
            )
            if resp.text:
                return {"success": True, "message": f"Connected to {self.model_id} via official GenAI SDK!"}
            return {"success": False, "error": "No response returned from model."}
        except APIError as e:
            err_msg = str(e)
            if "503" in err_msg or "high demand" in err_msg.lower():
                return {
                    "success": False,
                    "error": f"{self.model_id} is temporarily experiencing high traffic on Google's servers. Select 'Gemini 2.5 Flash' to connect immediately."
                }
            return {"success": False, "error": f"Google API Error: {err_msg}"}
        except Exception as e:
            return {"success": False, "error": f"Connection error: {str(e)}"}

    def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        system_instruction: str = "",
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """
        Generates structured JSON circuit commands using official GenAI SDK.
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "No API key configured. Please enter your Gemini API key in Settings.",
            }

        if not self._client:
            self._init_client()

        # Build message history (keep last 6 for fast TPM efficiency)
        recent_messages = messages[-6:] if len(messages) > 6 else messages
        prompt_parts = []
        for m in recent_messages:
            role_prefix = "User: " if m.get("role") in ["user", "system"] else "Assistant: "
            prompt_parts.append(f"{role_prefix}{m.get('content', '')}")

        full_prompt = "\n\n".join(prompt_parts)

        # Configure SDK call
        config = types.GenerateContentConfig(
            system_instruction=system_instruction if system_instruction else None,
            response_mime_type="application/json",
            temperature=temperature,
        )

        # Models to try with automatic fallback
        models_to_try = [self.model_id]
        if self.model_id != "gemini-2.5-flash":
            models_to_try.append("gemini-2.5-flash")

        last_error = ""
        for model in models_to_try:
            try:
                resp = self._client.models.generate_content(
                    model=model,
                    contents=full_prompt,
                    config=config,
                )

                if resp.text:
                    try:
                        parsed_json = json.loads(resp.text)
                        return {"success": True, "data": parsed_json, "raw_text": resp.text}
                    except json.JSONDecodeError:
                        return {"success": True, "raw_text": resp.text, "data": {"response": resp.text, "actions": []}}

            except APIError as e:
                err_str = str(e)
                last_error = err_str
                if "503" in err_str or "high demand" in err_str.lower() or "not found" in err_str.lower():
                    # Fallback to secondary model
                    continue
                return {"success": False, "error": f"GenAI API Error: {err_str}"}
            except Exception as e:
                last_error = str(e)

        return {"success": False, "error": f"Gemini Error: {last_error}"}
