"""
Production-grade Gemini Client using the official google-genai SDK.
Handles high-capacity API keys (AQ.... and AIza....), token pooling, and structured JSON output.
"""

import json
import time
import logging
from typing import Dict, Any, List, Optional, Callable
from google import genai  # type: ignore
from google.genai import types  # type: ignore
from google.genai.errors import APIError  # type: ignore

logger = logging.getLogger("AI_Logisim_Controller.gemini_client")

AVAILABLE_MODELS = [
    {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash (Fast & Stable — Recommended)"},
    {"id": "gemini-3.6-flash", "name": "Gemini 3.6 Flash (Latest Flagship)"},
    {"id": "gemini-3.5-flash", "name": "Gemini 3.5 Flash"},
    {"id": "gemini-3.8-flash", "name": "Gemini 3.8 Flash"},
    {"id": "gemini-3.7-flash", "name": "Gemini 3.7 Flash"},
    {"id": "custom", "name": "Custom Model..."},
]


def _clean_json_str(raw: str) -> str:
    s = raw.strip()
    if s.startswith("```json"):
        s = s[7:]
    elif s.startswith("```"):
        s = s[3:]
    if s.endswith("```"):
        s = s[:-3]
    return s.strip()


class GeminiClient:
    """Official Google GenAI SDK wrapper for AI Logisim Controller."""

    def __init__(self, api_key: str = "", model_id: str = "gemini-2.5-flash", thinking_budget: int = 1024):
        self.api_key = api_key.strip()
        self.model_id = model_id.strip() or "gemini-2.5-flash"
        self.thinking_budget = thinking_budget
        self._client: Optional[genai.Client] = None
        self._init_client()

    def _init_client(self):
        if self.api_key:
            try:
                # 45 second request timeout in milliseconds to prevent infinite socket hangs
                http_opts = types.HttpOptions(timeout=45000)
                self._client = genai.Client(api_key=self.api_key, http_options=http_opts)
            except Exception as e:
                logger.warning(f"Error initializing GenAI Client: {e}")
                self._client = None
        else:
            self._client = None

    def set_credentials(self, api_key: str, model_id: Optional[str] = None, thinking_budget: Optional[int] = None):
        self.api_key = api_key.strip()
        if model_id:
            self.model_id = model_id.strip()
        if thinking_budget is not None:
            self.thinking_budget = thinking_budget
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
            if "429" in err_msg or "resource_exhausted" in err_msg.lower():
                return {
                    "success": False,
                    "error": f"Rate limit reached on {self.model_id}. Please wait a moment or select 'Gemini 2.5 Flash'."
                }
            return {"success": False, "error": f"Google API Error: {err_msg}"}
        except Exception as e:
            return {"success": False, "error": f"Connection error: {str(e)}"}

    def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        system_instruction: str = "",
        temperature: float = 0.2,
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Generates structured JSON circuit commands using official GenAI SDK.
        Includes automatic 429 backoff retry, socket timeout handling, and model fallback.
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

        # Configure SDK call with thinking/reasoning budget
        thinking_cfg = None
        if self.thinking_budget is not None and self.thinking_budget >= 0:
            thinking_cfg = types.ThinkingConfig(thinking_budget=self.thinking_budget)

        config = types.GenerateContentConfig(
            system_instruction=system_instruction if system_instruction else None,
            response_mime_type="application/json",
            temperature=temperature,
            thinking_config=thinking_cfg,
        )

        # Models to try with automatic fallback
        models_to_try = [self.model_id]
        if self.model_id != "gemini-2.5-flash":
            models_to_try.append("gemini-2.5-flash")

        last_error = ""
        for model in models_to_try:
            for attempt in range(2):
                try:
                    resp = self._client.models.generate_content(
                        model=model,
                        contents=full_prompt,
                        config=config,
                    )

                    if resp.text:
                        cleaned = _clean_json_str(resp.text)
                        try:
                            parsed_json = json.loads(cleaned)
                            return {"success": True, "data": parsed_json, "raw_text": resp.text}
                        except json.JSONDecodeError:
                            return {"success": True, "raw_text": resp.text, "data": {"response": resp.text, "actions": []}}

                except Exception as e:
                    err_str = str(e)
                    last_error = err_str

                    # Check for rate limiting / quota
                    is_rate_limit = (
                        "429" in err_str
                        or "resource_exhausted" in err_str.lower()
                        or "quota" in err_str.lower()
                        or "rate limit" in err_str.lower()
                    )
                    # Check for overload / unavailable
                    is_overload = (
                        "503" in err_str
                        or "high demand" in err_str.lower()
                        or "not found" in err_str.lower()
                        or "unavailable" in err_str.lower()
                    )
                    # Check for timeout
                    is_timeout = (
                        "timed out" in err_str.lower()
                        or "timeout" in err_str.lower()
                    )

                    # Handle unsupported thinking config
                    if "thinking" in err_str.lower() and config.thinking_config is not None:
                        config.thinking_config = None
                        continue

                    # If retryable error and on first attempt for this model, wait and retry
                    if (is_rate_limit or is_overload or is_timeout) and attempt == 0:
                        delay = 3.0 if is_rate_limit else 1.5
                        reason = "rate limit reached" if is_rate_limit else ("timed out" if is_timeout else "server busy")
                        if status_callback:
                            status_callback(f"{model} {reason}. Retrying in {int(delay)}s...")
                        time.sleep(delay)
                        continue

                    # Otherwise, break attempt loop to switch to next model (e.g. gemini-2.5-flash fallback)
                    if status_callback and model != models_to_try[-1]:
                        status_callback(f"Switching from {model} to fallback {models_to_try[-1]}...")
                    break

        return {"success": False, "error": f"Gemini Error: {last_error}"}

    def generate_json(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.2,
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Generates structured JSON from a single prompt using official GenAI SDK."""
        return self.generate_chat_response(
            messages=[{"role": "user", "content": prompt}],
            system_instruction=system_instruction,
            temperature=temperature,
            status_callback=status_callback,
        )
