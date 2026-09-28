"""
Official Groq LPU Client for AI Logisim Controller.
Provides ultra-fast inference via console.groq.com using the official groq SDK
with HTTP REST fallback for standalone environments.
"""

import json
import re
from typing import Dict, Any, List, Optional
import requests

try:
    from groq import Groq
    HAS_GROQ_SDK = True
except ImportError:
    HAS_GROQ_SDK = False


AVAILABLE_GROQ_MODELS = [
    {"id": "qwen/qwen3.8-27b", "name": "Qwen 3.8 27B (Groq)"},
    {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B Versatile"},
    {"id": "deepseek-r1-distill-llama-70b", "name": "DeepSeek R1 Distill 70B"},
    {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B Instant (Ultra Fast)"},
    {"id": "custom", "name": "Custom Model..."},
]

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def _extract_json_response(raw_text: str) -> Dict[str, Any]:
    """
    Extracts and parses JSON from model output, handling:
    - Raw JSON
    - Markdown code blocks (```json ... ```)
    - Chain-of-thought tags (<think>...</think>)
    - Leading/trailing conversational text
    """
    thought = ""
    m_think = re.search(r"<think>(.*?)</think>", raw_text, re.DOTALL | re.IGNORECASE)
    if m_think:
        thought = m_think.group(1).strip()
        cleaned_text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL | re.IGNORECASE)
    else:
        cleaned_text = raw_text

    text = cleaned_text.strip()

    # Strip markdown block if present
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()

    # Attempt 1: Direct JSON parse
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            if thought and not data.get("thought"):
                data["thought"] = thought
            return data
    except Exception:
        pass

    # Attempt 2: Find outermost { and }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace : last_brace + 1]
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                if thought and not data.get("thought"):
                    data["thought"] = thought
                return data
        except Exception:
            pass

    # Fallback: Plain text response wrapper
    return {
        "thought": thought,
        "response": cleaned_text.strip() or raw_text.strip(),
        "actions": [],
    }


class GroqClient:
    """Client for Groq LPU API integrating with ControllerAgent."""

    def __init__(self, api_key: str = "", model_id: str = "qwen/qwen3.8-27b"):
        self.api_key = api_key.strip()
        self.model_id = model_id.strip() or "qwen/qwen3.8-27b"
        self._client: Optional[Any] = None
        self._init_sdk()

    def _init_sdk(self):
        if HAS_GROQ_SDK and self.api_key:
            try:
                self._client = Groq(api_key=self.api_key)
            except Exception:
                self._client = None
        else:
            self._client = None

    def set_credentials(self, api_key: str, model_id: Optional[str] = None):
        self.api_key = api_key.strip()
        if model_id:
            self.model_id = model_id.strip() or "qwen/qwen3.8-27b"
        self._init_sdk()

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def test_connection(self) -> Dict[str, Any]:
        """Validates Groq API key and model connectivity."""
        if not self.api_key:
            return {"success": False, "error": "API key is empty. Please enter your Groq API key (gsk_...)."}

        # Attempt 1: Official Groq SDK
        if self._client:
            try:
                resp = self._client.chat.completions.create(
                    model=self.model_id,
                    messages=[{"role": "user", "content": "Reply with 'OK' only."}],
                    max_tokens=10,
                    temperature=0.1,
                )
                if resp.choices and resp.choices[0].message.content:
                    return {
                        "success": True,
                        "message": f"Connected to {self.model_id} via Groq LPU!",
                    }
            except Exception as e:
                err_msg = str(e)
                if "401" in err_msg or "invalid_api_key" in err_msg.lower():
                    return {"success": False, "error": "Invalid Groq API Key. Please verify your key on console.groq.com."}
                elif "model_not_found" in err_msg.lower() or "not found" in err_msg.lower():
                    return {"success": False, "error": f"Model '{self.model_id}' was not found on Groq. Try 'llama-3.3-70b-versatile' or verify model ID."}
                return {"success": False, "error": f"Groq Error: {err_msg}"}

        # Attempt 2: Direct HTTP REST fallback
        payload = {
            "model": self.model_id,
            "messages": [{"role": "user", "content": "Reply with 'OK' only."}],
            "max_tokens": 10,
            "temperature": 0.1,
        }

        try:
            resp = requests.post(
                GROQ_API_URL,
                headers=self._get_headers(),
                json=payload,
                timeout=12.0,
            )

            if resp.status_code == 200:
                return {
                    "success": True,
                    "message": f"Connected to {self.model_id} via Groq LPU!",
                }

            try:
                err_data = resp.json()
                err_msg = err_data.get("error", {}).get("message") or resp.text
            except Exception:
                err_msg = resp.text

            if resp.status_code == 401:
                return {"success": False, "error": "Invalid Groq API Key. Please verify your key on console.groq.com."}
            return {"success": False, "error": f"Groq Error ({resp.status_code}): {err_msg}"}

        except requests.exceptions.Timeout:
            return {"success": False, "error": "Connection timed out connecting to Groq. Please try again."}
        except Exception as e:
            return {"success": False, "error": f"Groq Connection Error: {str(e)}"}

    def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        system_instruction: str = "",
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """
        Generates structured JSON circuit commands via Groq.
        Matches GeminiClient interface exactly for drop-in interoperability.
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "No Groq API key configured. Please enter your Groq key (gsk_...) in Settings.",
            }

        # Build OpenAI/Groq standard messages
        formatted_messages: List[Dict[str, str]] = []
        if system_instruction:
            formatted_messages.append({"role": "system", "content": system_instruction})

        recent_messages = messages[-6:] if len(messages) > 6 else messages
        for m in recent_messages:
            role = m.get("role", "user")
            if role in ("model", "assistant"):
                role = "assistant"
            elif role in ("user", "system"):
                role = "user"
            formatted_messages.append({"role": role, "content": m.get("content", "")})

        # Try official SDK first
        if self._client:
            try:
                try:
                    resp = self._client.chat.completions.create(
                        model=self.model_id,
                        messages=formatted_messages,
                        temperature=temperature,
                        response_format={"type": "json_object"},
                    )
                except Exception as sdk_err:
                    if "response_format" in str(sdk_err).lower():
                        resp = self._client.chat.completions.create(
                            model=self.model_id,
                            messages=formatted_messages,
                            temperature=temperature,
                        )
                    else:
                        raise

                if resp.choices:
                    msg = resp.choices[0].message
                    raw_content = msg.content or ""
                    parsed = _extract_json_response(raw_content)
                    return {
                        "success": True,
                        "data": parsed,
                        "raw_text": raw_content,
                    }
            except Exception as e:
                err_str = str(e)
                if "401" in err_str or "invalid_api_key" in err_str.lower():
                    return {"success": False, "error": "Invalid Groq API Key. Please verify your key on console.groq.com."}
                return {"success": False, "error": f"Groq SDK Error: {err_str}"}

        # Direct REST fallback
        payload = {
            "model": self.model_id,
            "messages": formatted_messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        try:
            resp = requests.post(
                GROQ_API_URL,
                headers=self._get_headers(),
                json=payload,
                timeout=45.0,
            )

            if resp.status_code == 400 and "response_format" in resp.text:
                payload.pop("response_format", None)
                resp = requests.post(
                    GROQ_API_URL,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=45.0,
                )

            if resp.status_code != 200:
                try:
                    err_json = resp.json()
                    err_msg = err_json.get("error", {}).get("message") or resp.text
                except Exception:
                    err_msg = resp.text
                return {"success": False, "error": f"Groq Error ({resp.status_code}): {err_msg}"}

            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                return {"success": False, "error": "Groq returned empty choices list."}

            choice = choices[0]
            raw_content = choice.get("message", {}).get("content", "")
            parsed = _extract_json_response(raw_content)

            return {
                "success": True,
                "data": parsed,
                "raw_text": raw_content,
            }

        except requests.exceptions.Timeout:
            return {"success": False, "error": f"Groq request timed out for model {self.model_id}."}
        except Exception as e:
            return {"success": False, "error": f"Groq Request Error: {str(e)}"}
