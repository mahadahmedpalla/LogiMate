"""
FastAPI Server for AI Logisim Controller.
Serves REST API, handles Gemini settings, connects to Logisim Driver and Agent.
"""

import sys
import os
import json
from typing import Dict, Any, Optional
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from logisim_engine.driver import LogisimDriver
from agent.gemini_client import GeminiClient, AVAILABLE_MODELS
from agent.controller_agent import ControllerAgent
from agent.planner_agent import PlannerAgent


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
        "gemini_api_key": "",
        "gemini_model": "gemini-2.5-flash",
        "custom_model": "",
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
    return default_config


def save_config(cfg: Dict[str, Any]):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


config = load_config()

# Initialize Driver, Gemini, and Agent
active_model = config.get("custom_model") if config.get("gemini_model") == "custom" and config.get("custom_model") else config.get("gemini_model", "gemini-2.5-flash")

driver = LogisimDriver(
    canvas_offset_x=config.get("canvas_offset_x", 200),
    canvas_offset_y=config.get("canvas_offset_y", 70),
)

gemini = GeminiClient(
    api_key=config.get("gemini_api_key", ""),
    model_id=active_model,
    thinking_budget=int(config.get("thinking_budget", 1024)),
)

agent = ControllerAgent(
    gemini_client=gemini,
    driver=driver,
    workspace_dir=OUTPUT_DIR,
)

planner_agent = PlannerAgent(
    gemini_client=gemini,
    driver=driver,
    workspace_dir=OUTPUT_DIR,
)

app = FastAPI(title="AI Logisim Controller")


# Request Models
class SettingsPayload(BaseModel):
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    custom_model: Optional[str] = None
    thinking_budget: Optional[int] = None
    canvas_offset_x: Optional[int] = None
    canvas_offset_y: Optional[int] = None


class ChatPayload(BaseModel):
    prompt: str
    mode: Optional[str] = "normal"


class PokePayload(BaseModel):
    pin_name: Optional[str] = None
    canvas_x: Optional[int] = None
    canvas_y: Optional[int] = None


class OpenUrlPayload(BaseModel):
    url: Optional[str] = None


CURRENT_VERSION = "1.0.0"


@app.get("/api/status")
def get_status():
    win_info = driver.get_window_info()
    return {
        "logisim": win_info,
        "has_api_key": bool(gemini.api_key),
        "model_id": gemini.model_id,
        "available_models": AVAILABLE_MODELS,
        "active_circuit": os.path.exists(agent.current_circ_path),
        "active_pins": agent.active_pin_map,
    }


@app.get("/api/settings")
def get_settings():
    masked_key = ""
    if config.get("gemini_api_key"):
        k = config["gemini_api_key"]
        masked_key = k[:4] + "..." + k[-4:] if len(k) > 8 else "***"
    return {
        "gemini_api_key": masked_key,
        "gemini_model": config.get("gemini_model", "gemini-2.5-flash"),
        "custom_model": config.get("custom_model", ""),
        "thinking_budget": config.get("thinking_budget", 1024),
        "canvas_offset_x": driver.canvas_offset_x,
        "canvas_offset_y": driver.canvas_offset_y,
        "available_models": AVAILABLE_MODELS,
    }


@app.post("/api/settings")
def update_settings(payload: SettingsPayload):
    global config
    if payload.gemini_api_key is not None and payload.gemini_api_key.strip():
        config["gemini_api_key"] = payload.gemini_api_key.strip()
    if payload.gemini_model is not None:
        config["gemini_model"] = payload.gemini_model.strip()
    if payload.custom_model is not None:
        config["custom_model"] = payload.custom_model.strip()
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
    model_to_use = config.get("custom_model") if config.get("gemini_model") == "custom" and config.get("custom_model") else config.get("gemini_model", "gemini-2.5-flash")
    gemini.set_credentials(
        api_key=config.get("gemini_api_key", ""),
        model_id=model_to_use,
        thinking_budget=int(config.get("thinking_budget", 1024)),
    )

    return {"success": True, "message": "Settings saved successfully."}


@app.post("/api/test-key")
def test_key(payload: SettingsPayload):
    key = payload.gemini_api_key.strip() if payload.gemini_api_key else config.get("gemini_api_key", "")
    model = payload.gemini_model.strip() if payload.gemini_model else config.get("gemini_model", "gemini-2.5-flash")
    if model == "custom" and payload.custom_model:
        model = payload.custom_model.strip()

    test_client = GeminiClient(api_key=key, model_id=model)
    return test_client.test_connection()


@app.post("/api/chat")
def chat(payload: ChatPayload):
    if not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    if payload.mode == "agent":
        result = planner_agent.execute_hierarchical_plan(payload.prompt)
        if planner_agent.current_builder:
            agent.current_builder = planner_agent.current_builder
            agent.active_pin_map = planner_agent.active_pin_map.copy()
        return result
    result = agent.execute_prompt(payload.prompt)
    return result


@app.post("/api/chat-agent-stream")
async def chat_agent_stream(payload: ChatPayload):
    if not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def progress_callback(event: Dict[str, Any]):
        loop.call_soon_threadsafe(queue.put_nowait, {"type": "progress", **event})

    async def run_worker():
        try:
            result = await asyncio.to_thread(
                planner_agent.execute_hierarchical_plan,
                payload.prompt,
                progress_callback,
            )
            if planner_agent.current_builder:
                agent.current_builder = planner_agent.current_builder
                agent.active_pin_map = planner_agent.active_pin_map.copy()
            await queue.put({"type": "complete", "result": result})
        except Exception as e:
            await queue.put({"type": "error", "error": str(e)})

    asyncio.create_task(run_worker())

    async def event_generator():
        while True:
            item = await queue.get()
            yield f"data: {json.dumps(item)}\n\n"
            if item.get("type") in ("complete", "error"):
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/control/launch-logisim")
def launch_logisim_app():
    ok = driver.launch_logisim()
    return {"success": ok, "message": "Logisim 2.7.1 launched!" if ok else "Logisim file not found in Downloads."}


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
        return {"success": ok, "message": "Loaded circuit into Logisim!" if ok else "Could not launch Logisim."}
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
