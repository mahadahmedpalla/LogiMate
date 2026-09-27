"""
Controller Agent coordinating LLM reasoning, XML synthesis, and Logisim driver actions.
Supports the full suite of Logisim 2.7.1 digital components:
Multi-bit pins, Splitters, Bitwise & Standard Gates, Arithmetic units, Plexers, Memory/Registers, and Probes.
"""

import os
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from logisim_engine.circ_builder import CircuitBuilder
from logisim_engine.driver import LogisimDriver
from .gemini_client import GeminiClient
from .circuit_prompts import SYSTEM_PROMPT
from .circuit_templates import (
    build_half_adder,
    build_full_adder,
    build_mux_2to1,
    build_sr_latch,
)


def _to_coords(val: Any, default_x: int = 100, default_y: int = 100) -> Tuple[int, int]:
    if isinstance(val, (list, tuple)) and len(val) >= 2:
        return int(val[0]), int(val[1])
    if isinstance(val, str):
        nums = [int(n.strip()) for n in val.replace("(", "").replace(")", "").split(",") if n.strip().lstrip("-").isdigit()]
        if len(nums) >= 2:
            return nums[0], nums[1]
    return default_x, default_y


def _parse_pin(p: Any) -> Tuple[str, int, int, bool, int, str]:
    """Extracts (name, x, y, is_output, width, facing) from dict or list/tuple."""
    if isinstance(p, dict):
        name = p.get("name") or p.get("label") or p.get("id") or "Pin"
        if "loc" in p:
            x, y = _to_coords(p["loc"], 100, 100)
        elif "pos" in p:
            x, y = _to_coords(p["pos"], 100, 100)
        else:
            x = int(p.get("x", 100))
            y = int(p.get("y", 100))
        is_out = p.get("is_output") or p.get("output") or (p.get("type") == "output") or False
        w = p.get("width", 1)
        facing = p.get("facing", "west" if is_out else "east")
        return str(name), x, y, bool(is_out), int(w), str(facing)
    elif isinstance(p, (list, tuple)):
        name = str(p[0])
        x = int(p[1])
        y = int(p[2])
        is_out = bool(p[3]) if len(p) > 3 else False
        w = int(p[4]) if len(p) > 4 else 1
        facing = str(p[5]) if len(p) > 5 else ("west" if is_out else "east")
        return name, x, y, is_out, w, facing
    raise ValueError(f"Cannot parse pin format: {p}")


def _parse_wire(w: Any) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """Extracts ((x1, y1), (x2, y2)) from dict or list/tuple."""
    def to_point(p):
        if isinstance(p, (list, tuple)):
            return int(p[0]), int(p[1])
        if isinstance(p, str):
            nums = [int(n) for n in p.replace("(", "").replace(")", "").split(",") if n.strip()]
            if len(nums) >= 2:
                return nums[0], nums[1]
        return 0, 0

    if isinstance(w, dict):
        p1 = w.get("from") or w.get("start") or w.get("src")
        p2 = w.get("to") or w.get("end") or w.get("dst")
        return to_point(p1), to_point(p2)
    elif isinstance(w, (list, tuple)):
        if len(w) == 2 and isinstance(w[0], (list, tuple)):
            return to_point(w[0]), to_point(w[1])
        elif len(w) == 4:
            return (int(w[0]), int(w[1])), (int(w[2]), int(w[3]))
    raise ValueError(f"Cannot parse wire format: {w}")


def _add_circuit_element(builder: CircuitBuilder, elem: Any, default_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Intelligently routes any element (Splitter, Gate, Arithmetic, Plexer, Memory, Probe, etc.)
    to the correct CircuitBuilder method, ensuring proper Logisim library selection.
    """
    if not isinstance(elem, dict):
        return {}

    raw_type = (elem.get("type") or elem.get("name") or elem.get("gate") or default_type or "AND").strip()
    type_upper = raw_type.upper()

    loc = elem.get("loc") or elem.get("pos") or [elem.get("x", 200), elem.get("y", 100)]
    x, y = _to_coords(loc, 200, 100)
    label = elem.get("label")
    width = int(elem.get("width", 1))

    # 1. Splitter detection: check type OR presence of incoming/fanout OR default_type="splitter"
    if "SPLIT" in type_upper or "incoming" in elem or "fanout" in elem or default_type == "splitter":
        incoming = int(elem.get("incoming", elem.get("width", 2)))
        fanout = int(elem.get("fanout", 2))
        appear = elem.get("appear", "left")
        facing = elem.get("facing", "east")
        bit_ranges = elem.get("bit_ranges")
        return builder.add_splitter(
            x=x,
            y=y,
            incoming=incoming,
            fanout=fanout,
            facing=facing,
            appear=appear,
            bit_ranges=bit_ranges,
        )

    # 2. Arithmetic detection (Adder, Subtractor, Multiplier, Divider, Comparator)
    arithmetic_names = ["ADDER", "SUBTRACTOR", "MULTIPLIER", "DIVIDER", "NEGATOR", "COMPARATOR", "SHIFTER"]
    if any(an in type_upper for an in arithmetic_names):
        return builder.add_arithmetic(
            op_type=raw_type,
            x=x,
            y=y,
            width=width if width > 1 else int(elem.get("bits", 8)),
            label=label,
        )

    # 3. Plexer detection (Multiplexer, Demultiplexer, Decoder, Priority Encoder)
    if "MUX" in type_upper or "MULTIPLEXER" in type_upper:
        select_bits = int(elem.get("select_bits", elem.get("select", 1)))
        return builder.add_mux(
            x=x,
            y=y,
            select_bits=select_bits,
            width=width,
            label=label,
        )

    if "PRIORITY" in type_upper or "ENCODER" in type_upper:
        select_val = str(elem.get("select", elem.get("select_bits", 2)))
        attrs = dict(elem.get("attrs") or {})
        if "select" not in attrs:
            attrs["select"] = select_val
        comp = builder.add_component(
            name="Priority Encoder",
            x=x,
            y=y,
            attrs=attrs,
            label=label,
        )
        return {"out": (x, y), "component": comp}

    # 4. Memory detection (Register, Counter)
    if "REGISTER" in type_upper:
        return builder.add_register(
            x=x,
            y=y,
            width=width if width > 1 else int(elem.get("bits", 8)),
            label=label,
        )

    # 5. Probe
    if "PROBE" in type_upper:
        radix_val = elem.get("radix", 16)
        pt = builder.add_probe(x=x, y=y, radix=radix_val, label=label)
        return {"out": pt}

    # 6. Tunnel
    if "TUNNEL" in type_upper:
        t_label = label or elem.get("name", "T1")
        pt = builder.add_tunnel(x=x, y=y, label=t_label, width=width)
        return {"out": pt}

    # 7. Constant
    if "CONSTANT" in type_upper:
        val = str(elem.get("value", elem.get("val", "0x1")))
        pt = builder.add_constant(x=x, y=y, value=val, width=width)
        return {"out": pt}

    # 8. Clock
    if "CLOCK" in type_upper:
        clk_label = label or "CLK"
        pt = builder.add_clock(x=x, y=y, label=clk_label)
        return {"out": pt}

    # 9. Logic Gates (AND, OR, NOT, NAND, NOR, XOR, XNOR)
    gate_types = ["AND", "OR", "NOT", "NAND", "NOR", "XOR", "XNOR", "BUFFER"]
    if any(gt == type_upper or gt in type_upper.split() for gt in gate_types):
        inputs = int(elem.get("inputs", 2))
        size = str(elem.get("size", "50"))
        facing = str(elem.get("facing", "east"))
        return builder.add_gate(
            gate_type=raw_type,
            x=x,
            y=y,
            inputs=inputs,
            size=size,
            width=width,
            facing=facing,
            label=label,
        )

    # Fallback: Generic component with canonical mapping
    comp = builder.add_component(
        name=raw_type,
        x=x,
        y=y,
        attrs=elem.get("attrs"),
        label=label,
    )
    return {"out": (x, y), "component": comp}


class ControllerAgent:
    """High-level orchestration agent for Logisim."""

    def __init__(
        self,
        gemini_client: GeminiClient,
        driver: LogisimDriver,
        workspace_dir: str = "output",
    ):
        self.client = gemini_client
        self.driver = driver
        self.workspace_dir = os.path.abspath(workspace_dir)
        os.makedirs(self.workspace_dir, exist_ok=True)
        self.current_circ_path = os.path.join(self.workspace_dir, "circuit.circ")

        self.current_builder: Optional[CircuitBuilder] = None
        self.active_pin_map: Dict[str, tuple] = {}
        self.conversation_history: List[Dict[str, str]] = []

    def execute_prompt(self, user_prompt: str) -> Dict[str, Any]:
        """
        Processes a user request through Gemini and executes corresponding actions.
        Returns detailed execution report.
        """
        self.conversation_history.append({"role": "user", "content": user_prompt})

        # Call Gemini
        result = self.client.generate_chat_response(
            messages=self.conversation_history,
            system_instruction=SYSTEM_PROMPT,
        )

        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "Failed to generate AI response."),
                "thought": "",
                "response": result.get("error") or "Could not contact Gemini. Please verify your API key and model in Settings.",
                "executed_actions": [],
            }

        response_data = result.get("data", {})
        thought = response_data.get("thought", "")
        reply_text = response_data.get("response", result.get("raw_text", ""))
        actions = response_data.get("actions", [])

        # Store model reply in history
        self.conversation_history.append({"role": "model", "content": reply_text})

        # Execute actions sequentially
        executed_actions = []
        screenshot_b64 = None

        for act in actions:
            action_type = act.get("action")
            action_status = {"action": action_type, "status": "pending", "details": ""}

            try:
                if action_type == "build_template":
                    tmpl = act.get("template", "").lower()
                    builder = CircuitBuilder(circuit_name="main")

                    if tmpl == "half_adder":
                        meta = build_half_adder(builder)
                    elif tmpl == "full_adder":
                        meta = build_full_adder(builder)
                    elif tmpl == "mux_2to1":
                        meta = build_mux_2to1(builder)
                    elif tmpl == "sr_latch":
                        meta = build_sr_latch(builder)
                    else:
                        raise ValueError(f"Unknown template: {tmpl}")

                    builder.save_file(self.current_circ_path)
                    self.current_builder = builder
                    self.active_pin_map = builder.pin_map.copy()
                    action_status["status"] = "success"
                    action_status["details"] = f"Generated {tmpl} at {os.path.basename(self.current_circ_path)} with pins {list(self.active_pin_map.keys())}"

                elif action_type == "build_custom_circuit":
                    circ_name = act.get("circuit_name", "main")
                    builder = CircuitBuilder(circuit_name=circ_name)

                    # 1. Add pins (supports width 1..32, input/output, facing)
                    for p in act.get("pins", []):
                        p_name, px, py, is_out, width, facing = _parse_pin(p)
                        builder.add_pin(
                            name=p_name,
                            x=px,
                            y=py,
                            is_output=is_out,
                            width=width,
                            facing=facing,
                        )

                    # 2. Add splitters (if explicitly declared in splitters array)
                    for s in act.get("splitters", []):
                        _add_circuit_element(builder, s, default_type="splitter")

                    # 3. Add gates & components (safely dispatched to correct Logisim libraries)
                    for g in act.get("gates", []):
                        _add_circuit_element(builder, g, default_type="AND")

                    for c in act.get("components", []):
                        _add_circuit_element(builder, c, default_type=None)

                    # 4. Add wires
                    for w in act.get("wires", []):
                        p1, p2 = _parse_wire(w)
                        builder.add_wire(p1, p2)

                    builder.save_file(self.current_circ_path)
                    self.current_builder = builder
                    self.active_pin_map = builder.pin_map.copy()
                    action_status["status"] = "success"
                    action_status["details"] = f"Custom circuit created with {len(builder.components)} components and {len(builder.wires)} wires."

                elif action_type == "open_in_logisim":
                    if os.path.exists(self.current_circ_path):
                        ok = self.driver.open_circuit_direct(self.current_circ_path)
                        action_status["status"] = "success" if ok else "warning"
                        action_status["details"] = (
                            f"Loaded {os.path.basename(self.current_circ_path)} directly into Logisim."
                            if ok
                            else "Circuit file ready. Click 'Load in Logisim' to view."
                        )
                    else:
                        action_status["status"] = "error"
                        action_status["details"] = "No circuit file exists to load."

                elif action_type == "poke_pin":
                    pin_name = act.get("pin")
                    if pin_name in self.active_pin_map:
                        coords = self.active_pin_map[pin_name]
                        ok = self.driver.poke_canvas_coord(coords[0], coords[1])
                        action_status["status"] = "success" if ok else "warning"
                        action_status["details"] = f"Poked pin '{pin_name}' at canvas ({coords[0]}, {coords[1]})."
                    else:
                        action_status["status"] = "warning"
                        action_status["details"] = f"Pin '{pin_name}' not found in active pin map {list(self.active_pin_map.keys())}."

                elif action_type == "tick_clock":
                    count = int(act.get("count", 1))
                    for _ in range(count):
                        self.driver.tick_once()
                        time.sleep(0.05)
                    action_status["status"] = "success"
                    action_status["details"] = f"Stepped clock {count} time(s)."

                elif action_type == "toggle_clock":
                    self.driver.toggle_ticks()
                    action_status["status"] = "success"
                    action_status["details"] = "Toggled continuous clock."

                elif action_type == "reset_simulation":
                    self.driver.reset_simulation()
                    action_status["status"] = "success"
                    action_status["details"] = "Simulation state reset."

                elif action_type == "inspect_state":
                    screenshot_b64 = self.driver.capture_screenshot_base64()
                    action_status["status"] = "success" if screenshot_b64 else "warning"
                    action_status["details"] = "Captured window snapshot." if screenshot_b64 else "Could not capture Logisim window."

                else:
                    action_status["status"] = "ignored"
                    action_status["details"] = f"Unrecognized action: {action_type}"

            except Exception as e:
                action_status["status"] = "error"
                action_status["details"] = str(e)

            executed_actions.append(action_status)

        # Guaranteed Auto-Open:
        # If a circuit was successfully built (custom or template), ensure it is opened in Logisim,
        # even if Gemini omitted "open_in_logisim" from the actions array.
        circuit_built = any(
            a.get("action") in ("build_custom_circuit", "build_template") and a.get("status") == "success"
            for a in executed_actions
        )
        already_opened = any(a.get("action") == "open_in_logisim" for a in executed_actions)

        if circuit_built and not already_opened and os.path.exists(self.current_circ_path):
            ok = self.driver.open_circuit_direct(self.current_circ_path)
            executed_actions.append({
                "action": "open_in_logisim",
                "status": "success" if ok else "warning",
                "details": (
                    f"Auto-loaded {os.path.basename(self.current_circ_path)} directly into Logisim."
                    if ok
                    else "Circuit file ready on disk."
                ),
            })

        return {
            "success": True,
            "thought": thought,
            "response": reply_text,
            "executed_actions": executed_actions,
            "screenshot": screenshot_b64,
            "pin_map": self.active_pin_map,
            "circuit_file": self.current_circ_path if os.path.exists(self.current_circ_path) else None,
        }
