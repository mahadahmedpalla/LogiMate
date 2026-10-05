"""
FastAPI Server for AI Logisim Controller.
Serves REST API, handles Gemini settings, connects to Logisim Driver and Agent.
"""

import sys
import os
import json
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from logisim_engine.driver import LogisimDriver
from agent.gemini_client import GeminiClient, AVAILABLE_MODELS as AVAILABLE_GEMINI_MODELS
from agent.groq_client import GroqClient, AVAILABLE_GROQ_MODELS
from agent.controller_agent import ControllerAgent


def get_bundle_dir() -> str:
    """Returns directory where static assets (like ui/) are located."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def get_data_dir() -> str:
    """Returns directory where user data (config.json, output/) should persist."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


DATA_DIR = get_data_dir()
BUNDLE_DIR = get_bundle_dir()

CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
OUTPUT_DIR = os.path.join(DATA_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_config() -> Dict[str, Any]:
    default_config = {
        "ai_provider": "gemini",  # "gemini" or "groq"
        "gemini_api_key": "",
        "gemini_model": "gemini-3.6-flash",
        "groq_api_key": "",
        "groq_model": "qwen/qwen3.8-27b",
        "custom_model": "",
        "logisim_path": "",
        "thinking_budget": 1024,
        "canvas_offset_x": 200,
        "canvas_offset_y": 70,
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                default_config.update(loaded)
        except Exception:
            pass

    # Auto-migrate legacy 2.x/1.x models
    if default_config.get("gemini_model") in ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"):
        default_config["gemini_model"] = "gemini-3.6-flash"

    # Auto-migrate openrouter -> groq if previously selected
    if default_config.get("ai_provider") == "openrouter":
        default_config["ai_provider"] = "groq"

    return default_config


def save_config(cfg: Dict[str, Any]):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


config = load_config()

# Initialize Driver, Gemini, Groq, and Agent
active_gemini_model = config.get("custom_model") if config.get("gemini_model") == "custom" and config.get("custom_model") else config.get("gemini_model", "gemini-3.6-flash")
active_groq_model = config.get("custom_model") if config.get("groq_model") == "custom" and config.get("custom_model") else config.get("groq_model", "qwen/qwen3.8-27b")

driver = LogisimDriver(
    canvas_offset_x=config.get("canvas_offset_x", 200),
    canvas_offset_y=config.get("canvas_offset_y", 70),
    custom_logisim_path=config.get("logisim_path"),
)

gemini = GeminiClient(
    api_key=config.get("gemini_api_key", ""),
    model_id=active_gemini_model,
    thinking_budget=int(config.get("thinking_budget", 1024)),
)

groq = GroqClient(
    api_key=config.get("groq_api_key", ""),
    model_id=active_groq_model,
)

current_provider = config.get("ai_provider", "gemini").lower()
active_client = groq if current_provider == "groq" else gemini

agent = ControllerAgent(
    gemini_client=active_client,
    driver=driver,
    workspace_dir=OUTPUT_DIR,
)

app = FastAPI(title="AI Logisim Controller")


# Request Models
class SettingsPayload(BaseModel):
    ai_provider: Optional[str] = None
    provider: Optional[str] = None
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    groq_model: Optional[str] = None
    model: Optional[str] = None
    custom_model: Optional[str] = None
    logisim_path: Optional[str] = None
    thinking_budget: Optional[int] = None
    canvas_offset_x: Optional[int] = None
    canvas_offset_y: Optional[int] = None


class ChatPayload(BaseModel):
    prompt: str
    deep_mode: Optional[bool] = False


class PokePayload(BaseModel):
    pin_name: Optional[str] = None
    canvas_x: Optional[int] = None
    canvas_y: Optional[int] = None


class OpenUrlPayload(BaseModel):
    url: Optional[str] = None


CURRENT_VERSION = "1.6.0"


@app.get("/api/ping")
def ping():
    """Zero-cost readiness probe used by the desktop launcher (no window/file scans)."""
    return {"ok": True, "version": CURRENT_VERSION}


def _circuit_version() -> int:
    """Modification stamp of the active circuit file; changes only when a new circuit is written."""
    try:
        return os.stat(agent.current_circ_path).st_mtime_ns
    except OSError:
        return 0


@app.get("/api/status")
def get_status():
    win_info = driver.get_window_info()
    provider = config.get("ai_provider", "gemini").lower()
    active_client = groq if provider == "groq" else gemini
    exe_path = driver.find_logisim_exe()
    return {
        "logisim": win_info,
        "logisim_path": exe_path,
        "has_logisim": bool(exe_path),
        "bundled_logisim": driver.is_bundled(),
        "ai_provider": provider,
        "has_api_key": bool(active_client.api_key),
        "model_id": active_client.model_id,
        "available_models": AVAILABLE_GROQ_MODELS if provider == "groq" else AVAILABLE_GEMINI_MODELS,
        "available_gemini_models": AVAILABLE_GEMINI_MODELS,
        "available_groq_models": AVAILABLE_GROQ_MODELS,
        "active_circuit": os.path.exists(agent.current_circ_path),
        "circuit_version": _circuit_version(),
        "active_pins": agent.active_pin_map,
    }


@app.get("/api/settings")
def get_settings():
    masked_gemini_key = ""
    if config.get("gemini_api_key"):
        k = config["gemini_api_key"]
        masked_gemini_key = k[:4] + "..." + k[-4:] if len(k) > 8 else "***"

    masked_groq_key = ""
    if config.get("groq_api_key"):
        k = config["groq_api_key"]
        masked_groq_key = k[:4] + "..." + k[-4:] if len(k) > 8 else "***"

    return {
        "ai_provider": config.get("ai_provider", "gemini"),
        "gemini_api_key": masked_gemini_key,
        "gemini_model": config.get("gemini_model", "gemini-3.6-flash"),
        "groq_api_key": masked_groq_key,
        "groq_model": config.get("groq_model", "qwen/qwen3.8-27b"),
        "custom_model": config.get("custom_model", ""),
        "logisim_path": config.get("logisim_path", ""),
        "detected_logisim_path": driver.find_logisim_exe(),
        "bundled_logisim": driver.is_bundled(),
        "thinking_budget": config.get("thinking_budget", 1024),
        "canvas_offset_x": driver.canvas_offset_x,
        "canvas_offset_y": driver.canvas_offset_y,
        "available_models": AVAILABLE_GEMINI_MODELS,
        "available_gemini_models": AVAILABLE_GEMINI_MODELS,
        "available_groq_models": AVAILABLE_GROQ_MODELS,
    }


@app.post("/api/settings")
def update_settings(payload: SettingsPayload):
    global config
    if payload.ai_provider is not None and payload.ai_provider.strip():
        config["ai_provider"] = payload.ai_provider.strip().lower()
    if payload.gemini_api_key is not None and payload.gemini_api_key.strip():
        config["gemini_api_key"] = payload.gemini_api_key.strip()
    if payload.gemini_model is not None:
        config["gemini_model"] = payload.gemini_model.strip()
    if payload.groq_api_key is not None and payload.groq_api_key.strip():
        config["groq_api_key"] = payload.groq_api_key.strip()
    if payload.groq_model is not None:
        config["groq_model"] = payload.groq_model.strip()
    if payload.custom_model is not None:
        config["custom_model"] = payload.custom_model.strip()
    if payload.logisim_path is not None:
        config["logisim_path"] = payload.logisim_path.strip()
        driver.custom_logisim_path = config["logisim_path"] if config["logisim_path"] else None
    if payload.thinking_budget is not None:
        config["thinking_budget"] = payload.thinking_budget
    if payload.canvas_offset_x is not None:
        config["canvas_offset_x"] = payload.canvas_offset_x
        driver.canvas_offset_x = payload.canvas_offset_x
    if payload.canvas_offset_y is not None:
        config["canvas_offset_y"] = payload.canvas_offset_y
        driver.canvas_offset_y = payload.canvas_offset_y

    save_config(config)

    # Update runtime objects
    model_to_use_gemini = config.get("custom_model") if config.get("gemini_model") == "custom" and config.get("custom_model") else config.get("gemini_model", "gemini-3.6-flash")
    gemini.set_credentials(
        api_key=config.get("gemini_api_key", ""),
        model_id=model_to_use_gemini,
        thinking_budget=int(config.get("thinking_budget", 1024)),
    )

    model_to_use_groq = config.get("custom_model") if config.get("groq_model") == "custom" and config.get("custom_model") else config.get("groq_model", "qwen/qwen3.8-27b")
    groq.set_credentials(
        api_key=config.get("groq_api_key", ""),
        model_id=model_to_use_groq,
    )

    # Route agent to active provider
    current_provider = config.get("ai_provider", "gemini").lower()
    agent.client = groq if current_provider == "groq" else gemini

    return {"success": True, "message": "Settings saved successfully."}


@app.post("/api/test-key")
@app.post("/api/test-connection")
def test_key(payload: SettingsPayload):
    provider = (payload.ai_provider or payload.provider or config.get("ai_provider", "gemini")).lower()
    if provider == "groq":
        raw_key = payload.groq_api_key if payload.groq_api_key and payload.groq_api_key.strip() else payload.api_key
        key = raw_key.strip() if raw_key and raw_key.strip() else config.get("groq_api_key", "")
        raw_model = payload.groq_model if payload.groq_model and payload.groq_model.strip() else payload.model
        model = raw_model.strip() if raw_model and raw_model.strip() else config.get("groq_model", "qwen/qwen3.8-27b")
        if model == "custom" and payload.custom_model:
            model = payload.custom_model.strip()
        test_client = GroqClient(api_key=key, model_id=model)
        return test_client.test_connection()
    else:
        raw_key = payload.gemini_api_key if payload.gemini_api_key and payload.gemini_api_key.strip() else payload.api_key
        key = raw_key.strip() if raw_key and raw_key.strip() else config.get("gemini_api_key", "")
        raw_model = payload.gemini_model if payload.gemini_model and payload.gemini_model.strip() else payload.model
        model = raw_model.strip() if raw_model and raw_model.strip() else config.get("gemini_model", "gemini-3.6-flash")
        if model == "custom" and payload.custom_model:
            model = payload.custom_model.strip()
        test_client = GeminiClient(api_key=key, model_id=model)
        return test_client.test_connection()


@app.post("/api/chat")
def chat(payload: ChatPayload):
    if not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    result = agent.execute_prompt(payload.prompt, deep_mode=payload.deep_mode)
    return result


@app.post("/api/control/launch-logisim")
def launch_logisim_app():
    ok = driver.launch_logisim()
    if ok:
        return {"success": True, "message": "Logisim 2.7.1 launched successfully!"}
    exe = driver.find_logisim_exe()
    if not exe:
        return {"success": False, "message": "Logisim executable not found. Please install Java and check Settings."}
    return {"success": False, "message": "Failed to start Logisim process. Please ensure Java (JRE/JDK) is installed."}


@app.post("/api/control/tick")
def manual_tick():
    ok = driver.tick_once()
    return {"success": ok, "message": "Clock ticked" if ok else "Logisim window not detected."}


@app.post("/api/control/toggle-clock")
def manual_toggle_clock():
    ok = driver.toggle_ticks()
    return {"success": ok, "message": "Toggled continuous ticks" if ok else "Logisim window not detected."}


@app.post("/api/control/reset")
def manual_reset():
    ok = driver.reset_simulation()
    return {"success": ok, "message": "Simulation reset" if ok else "Logisim window not detected."}


@app.post("/api/control/poke")
def manual_poke(payload: PokePayload):
    if payload.pin_name and payload.pin_name in agent.active_pin_map:
        coords = agent.active_pin_map[payload.pin_name]
        ok = driver.poke_canvas_coord(coords[0], coords[1])
        return {"success": ok, "message": f"Poked {payload.pin_name} at {coords}"}
    elif payload.canvas_x is not None and payload.canvas_y is not None:
        ok = driver.poke_canvas_coord(payload.canvas_x, payload.canvas_y)
        return {"success": ok, "message": f"Poked canvas ({payload.canvas_x}, {payload.canvas_y})"}
    return {"success": False, "message": "Pin name or coordinates not found."}


@app.post("/api/control/load-circuit")
def reload_circuit():
    if os.path.exists(agent.current_circ_path):
        ok = driver.open_circuit_direct(agent.current_circ_path)
        return {"success": ok, "message": "Loaded circuit into Logisim!" if ok else "Could not launch Logisim or load circuit."}
    return {"success": False, "message": "No generated circuit exists yet."}
    return {"success": False, "message": "No generated circuit exists yet."}


@app.get("/api/circuit/diagram")
def get_circuit_diagram():
    """Returns component and wire data for live in-app SVG visualizer."""
    if agent.current_builder:
        b = agent.current_builder
        components = []
        for c in b.components:
            components.append({
                "lib": c.lib,
                "name": c.name,
                "x": c.x,
                "y": c.y,
                "attrs": c.attrs,
                "label": c.label,
            })
        wires = [{"from": w.from_pos, "to": w.to_pos} for w in b.wires]
        return {
            "exists": True,
            "components": components,
            "wires": wires,
            "pins": b.pin_map,
        }
    return {"exists": False, "components": [], "wires": [], "pins": {}}


@app.get("/api/circuit/content")
def get_circuit_content():
    if os.path.exists(agent.current_circ_path):
        with open(agent.current_circ_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"exists": True, "xml": content}
    return {"exists": False, "xml": ""}


@app.get("/api/circuit/download")
def download_circuit():
    if os.path.exists(agent.current_circ_path):
        return FileResponse(
            agent.current_circ_path,
            filename="circuit.circ",
            media_type="application/xml",
        )
    raise HTTPException(status_code=404, detail="No circuit found.")


@app.get("/api/check-update")
def check_for_updates():
    """Checks GitHub Releases for a newer version of LogiMate."""
    import urllib.request

    github_url = "https://api.github.com/repos/mahadahmedpalla/LogiMate/releases/latest"
    try:
        req = urllib.request.Request(
            github_url,
            headers={"User-Agent": f"LogiMate-App/{CURRENT_VERSION}"}
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                tag_name = data.get("tag_name", "").lstrip("v").strip()
                html_url = data.get("html_url", "https://github.com/mahadahmedpalla/LogiMate/releases/latest")
                body = data.get("body", "")

                def parse_version(v_str):
                    parts = []
                    for part in v_str.split("."):
                        digits = "".join(filter(str.isdigit, part))
                        parts.append(int(digits) if digits else 0)
                    return parts

                cur_parts = parse_version(CURRENT_VERSION)
                latest_parts = parse_version(tag_name)

                is_newer = latest_parts > cur_parts
                return {
                    "update_available": is_newer,
                    "current_version": CURRENT_VERSION,
                    "latest_version": tag_name,
                    "html_url": html_url,
                    "release_notes": body,
                }
    except Exception:
        pass

    return {
        "update_available": False,
        "current_version": CURRENT_VERSION,
        "latest_version": CURRENT_VERSION,
        "html_url": "https://github.com/mahadahmedpalla/LogiMate/releases/latest",
    }


@app.post("/api/open-external")
def open_external(payload: OpenUrlPayload):
    import webbrowser
    url = payload.url or "https://github.com/mahadahmedpalla/LogiMate/releases/latest"
    webbrowser.open(url)
    return {"success": True}


# Mount UI static files
UI_DIR = os.path.join(BUNDLE_DIR, "ui")
if os.path.exists(UI_DIR):
    app.mount("/static", StaticFiles(directory=UI_DIR), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(UI_DIR, "index.html"))
