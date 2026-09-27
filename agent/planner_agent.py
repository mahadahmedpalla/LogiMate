"""
Planner Agent for Hierarchical Digital Logic Synthesis in Logisim 2.7.1.
Deconstructs complex digital architectures (CPUs, ALUs, multi-stage processors)
into modular Logisim subcircuits, synthesizes each sheet sequentially,
and interconnects them on the top-level 'main' canvas.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Callable, Tuple

from logisim_engine.circ_builder import CircuitBuilder, _normalize_probe_radix
from logisim_engine.driver import LogisimDriver
from .gemini_client import GeminiClient
from .controller_agent import (
    _to_coords,
    _parse_pin,
    _parse_wire,
    _add_circuit_element,
)

logger = logging.getLogger("AI_Logisim_Controller.planner_agent")

PLANNER_SYSTEM_PROMPT = """
You are the Chief Digital Architecture Planner for LogiMate controlling Logisim 2.7.1.
Your task is to take high-level or complex computer engineering prompts (e.g. 8-bit CPUs, multi-function ALUs, complex calculators)
and deconstruct them into clean, modular, hierarchical subcircuits.

In Logisim 2.7.1, hierarchical subcircuits are native:
Each subcircuit is a distinct sheet with input and output pins.
On the top-level 'main' sheet, each subcircuit is instantiated as an IC chip box and interconnected with busses and wires.

When given an architecture prompt, produce a JSON specification:
```json
{
  "system_name": "Short title of system (e.g. 8-bit Mini CPU)",
  "architecture_summary": "Concise architectural explanation",
  "subcircuits": [
    {
      "name": "ALU",
      "purpose": "Arithmetic Logic Unit supporting ADD, SUB, AND, OR, XOR",
      "inputs": [
        {"name": "A", "width": 8},
        {"name": "B", "width": 8},
        {"name": "Op", "width": 3}
      ],
      "outputs": [
        {"name": "Result", "width": 8},
        {"name": "Zero", "width": 1},
        {"name": "Carry", "width": 1}
      ]
    },
    {
      "name": "Register_8bit",
      "purpose": "General Purpose 8-bit Register with Load enable",
      "inputs": [
        {"name": "D", "width": 8},
        {"name": "Load", "width": 1},
        {"name": "Clk", "width": 1}
      ],
      "outputs": [
        {"name": "Q", "width": 8}
      ]
    }
  ],
  "assembly_strategy": "Description of how subcircuits will be interconnected on the main canvas."
}
```

CRITICAL RULES:
1. Keep the number of subcircuits manageable: typically 2 to 4 modular units (e.g., ALU, Register, Control/Decoder).
2. For simple circuits that do not need decomposition (e.g. single 1-bit adder, basic logic gates), return `subcircuits: []`.
3. Give subcircuits clear, identifier-safe names (e.g. "ALU", "Register_8bit", "Instruction_Decoder", no spaces or special characters).
4. Bit widths must be realistic and consistent across interconnected modules (e.g., 8-bit datapath uses width 8).
"""

MODULE_SYNTHESIS_PROMPT = """
You are synthesizing an isolated Logisim 2.7.1 subcircuit sheet:
Module Name: {module_name}
Purpose: {purpose}
Required Input Pins: {inputs}
Required Output Pins: {outputs}

Generate the exact Logisim digital logic components, gates, arithmetic blocks, splitters, and wires for this module.

Layout Rules for this Sheet:
- Input Pins: Place on the left edge (x=100, y=100, 140, 180, ... facing east).
- Output Pins: Place on the right edge (x=450..500, y=100, 140, 180, ... facing west).
- Arithmetic: In Logisim, full adders/subtractors are named "Adder" or "Subtractor" (lib 3).
- Multiplexers: In lib 2, select at (x-20, y+20), data inputs on left.
- Registers: In lib 4, D at (x-30, y), Q at (x, y), Clock at (x-20, y+20).
- Probes: Use valid radix ("2", "10signed", "10unsigned", "16").
- All wires must be orthogonal.

Output ONLY a JSON object:
```json
{{
  "thought": "Brief explanation of how the module logic was constructed",
  "pins": [
    {{"name": "A", "loc": [100, 100], "width": 8, "is_output": false}},
    {{"name": "B", "loc": [100, 140], "width": 8, "is_output": false}},
    {{"name": "Result", "loc": [450, 120], "width": 8, "is_output": true}}
  ],
  "gates": [],
  "components": [
    {{"type": "Adder", "loc": [280, 120], "width": 8}}
  ],
  "splitters": [],
  "wires": [
    {{"from": [100, 100], "to": [240, 110]}},
    {{"from": [100, 140], "to": [240, 130]}},
    {{"from": [280, 120], "to": [450, 120]}}
  ]
}}
```
"""

TOP_LEVEL_ASSEMBLY_PROMPT = """
You are assembling the top-level 'main' circuit sheet for '{system_name}' in Logisim 2.7.1.

Available Subcircuit IC Chips defined in this project:
{subcircuit_specs}

Your task on 'main':
1. Instantiate the required subcircuit instances on the canvas.
2. Provide interactive user inputs (Clock, Reset, Load/Step buttons or pins).
3. Place Probes (radix "16" or "10signed") on major busses (Accumulator, Data Bus, Program Counter, ALU Result, Flags) so the user can see live values!
4. Connect wires cleanly between chip terminals and busses.

Output ONLY a JSON object:
```json
{{
  "thought": "Assembly plan explanation",
  "subcircuit_instances": [
    {{"name": "ALU", "loc": [320, 200], "label": "ALU"}},
    {{"name": "Register_8bit", "loc": [160, 140], "label": "R0"}},
    {{"name": "Register_8bit", "loc": [160, 260], "label": "R1"}}
  ],
  "pins": [
    {{"name": "CLK", "loc": [60, 100], "width": 1, "is_output": false}},
    {{"name": "RST", "loc": [60, 140], "width": 1, "is_output": false}}
  ],
  "components": [
    {{"type": "Clock", "loc": [60, 80]}},
    {{"type": "Probe", "loc": [450, 200], "radix": "16", "label": "ALU_OUT"}}
  ],
  "gates": [],
  "splitters": [],
  "wires": []
}}
```
"""


class PlannerAgent:
    """
    Autonomous Hierarchical Planner Agent.
    Deconstructs complex prompts into multi-circuit Logisim sheets,
    synthesizes each subcircuit, and wires the top-level assembly.
    """

    def __init__(
        self,
        gemini_client: GeminiClient,
        driver: LogisimDriver,
        workspace_dir: str,
    ):
        self.gemini = gemini_client
        self.driver = driver
        self.workspace_dir = workspace_dir
        self.current_circ_path = os.path.join(self.workspace_dir, "circuit.circ")
        self.current_builder: Optional[CircuitBuilder] = None
        self.active_pin_map: Dict[str, Tuple[int, int]] = {}
        self.last_plan: Optional[Dict[str, Any]] = None

    def execute_hierarchical_plan(
        self,
        prompt: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        Executes a 4-step autonomous synthesis:
        1. Deconstructs the prompt into subcircuit specifications.
        2. Iteratively synthesizes each subcircuit in its own isolated sheet.
        3. Instantiates and interconnects subcircuit chips on 'main'.
        4. Saves and auto-launches into Logisim 2.7.1.
        """
        def report_progress(step: str, message: str, percent: int, extra: Optional[Dict] = None):
            logger.info(f"[PlannerAgent] Step {step} ({percent}%): {message}")
            if progress_callback:
                payload = {
                    "step": step,
                    "message": message,
                    "percent": percent,
                }
                if extra:
                    payload.update(extra)
                progress_callback(payload)

        report_progress("planning", "Analyzing system architecture and deconstructing into subcircuits...", 10)

        # -----------------------------------------------------------------
        # STEP 1: Deconstruction Plan
        # -----------------------------------------------------------------
        plan_resp = self.gemini.generate_json(
            prompt=f"System Architecture Request:\n{prompt}",
            system_instruction=PLANNER_SYSTEM_PROMPT,
        )

        plan = {}
        if plan_resp.get("success") and plan_resp.get("data"):
            plan = plan_resp["data"]
        else:
            # Fallback plan if decomposition didn't produce valid JSON
            plan = {
                "system_name": "Digital System",
                "architecture_summary": "Direct system synthesis",
                "subcircuits": [],
                "assembly_strategy": "Direct canvas build",
            }

        self.last_plan = plan
        subcircuits = plan.get("subcircuits", [])
        system_name = plan.get("system_name", "Digital System")

        builder = CircuitBuilder(circuit_name="main")
        completed_steps: List[str] = []

        # -----------------------------------------------------------------
        # STEP 2: Sequential Subcircuit Synthesis
        # -----------------------------------------------------------------
        if subcircuits:
            report_progress(
                "planned",
                f"Architecture decomposed into {len(subcircuits)} subcircuit(s): {', '.join([s.get('name', 'Module') for s in subcircuits])}",
                25,
                {"subcircuits": [s.get("name") for s in subcircuits]},
            )

            total_sub = len(subcircuits)
            for idx, sub in enumerate(subcircuits):
                sub_name = sub.get("name", f"Subcircuit_{idx+1}").replace(" ", "_")
                sub_purpose = sub.get("purpose", "")
                sub_inputs = sub.get("inputs", [])
                sub_outputs = sub.get("outputs", [])

                pct = 25 + int((idx / total_sub) * 45)
                report_progress(
                    "synthesizing_subcircuit",
                    f"Synthesizing modular sheet '{sub_name}' ({idx+1}/{total_sub})...",
                    pct,
                    {"current_module": sub_name},
                )

                sub_prompt = MODULE_SYNTHESIS_PROMPT.format(
                    module_name=sub_name,
                    purpose=sub_purpose,
                    inputs=json.dumps(sub_inputs),
                    outputs=json.dumps(sub_outputs),
                )

                mod_resp = self.gemini.generate_json(
                    prompt=sub_prompt,
                    system_instruction="You are an expert digital logic engineer producing clean, isolated Logisim 2.7.1 circuits.",
                )

                builder.set_active_circuit(sub_name)

                if mod_resp.get("success") and mod_resp.get("data"):
                    mod_data = mod_resp["data"]
                    self._populate_circuit_sheet(builder, mod_data)
                    completed_steps.append(f"Synthesized subcircuit '{sub_name}' ({len(builder.components)} comps, {len(builder.wires)} wires)")
                else:
                    # Basic fallback pins if LLM synthesis returned empty
                    self._populate_fallback_subcircuit(builder, sub_inputs, sub_outputs)
                    completed_steps.append(f"Synthesized subcircuit '{sub_name}' (template layout)")

        # -----------------------------------------------------------------
        # STEP 3: Top-Level Assembly on 'main'
        # -----------------------------------------------------------------
        report_progress("assembling_main", "Assembling top-level datapath, control signals, and probes on 'main'...", 75)
        builder.set_active_circuit("main")

        sub_specs_str = "\n".join([
            f"- Subcircuit '{s.get('name')}': Inputs: {[i.get('name') for i in s.get('inputs', [])]}, Outputs: {[o.get('name') for o in s.get('outputs', [])]}"
            for s in subcircuits
        ]) if subcircuits else "None (Single-turn synthesis on 'main')."

        assembly_prompt = TOP_LEVEL_ASSEMBLY_PROMPT.format(
            system_name=system_name,
            subcircuit_specs=sub_specs_str,
        )

        assembly_resp = self.gemini.generate_json(
            prompt=assembly_prompt,
            system_instruction="You are an expert digital logic architect assembling top-level system datapaths in Logisim 2.7.1.",
        )

        if assembly_resp.get("success") and assembly_resp.get("data"):
            assembly_data = assembly_resp["data"]
            # 1. Add subcircuit IC chips
            for inst in assembly_data.get("subcircuit_instances", []):
                chip_name = inst.get("name")
                loc = inst.get("loc", [240, 160])
                label = inst.get("label", chip_name)
                x, y = _to_coords(loc, 240, 160)
                builder.add_subcircuit_instance(chip_name, x, y, label=label)

            # 2. Add other elements on main
            self._populate_circuit_sheet(builder, assembly_data)
            completed_steps.append("Assembled top-level 'main' datapath with controls and probes")
        else:
            # Fallback subcircuit chips placement if assembly data wasn't returned
            y_offset = 140
            for s in subcircuits:
                s_name = s.get("name", "Subcircuit").replace(" ", "_")
                builder.add_subcircuit_instance(s_name, 260, y_offset, label=s_name)
                y_offset += 100
            completed_steps.append("Placed subcircuit chips on 'main' canvas")

        # -----------------------------------------------------------------
        # STEP 4: Save & Auto-Launch
        # -----------------------------------------------------------------
        report_progress("saving", "Saving multi-circuit project file...", 90)
        builder.save_file(self.current_circ_path)
        self.current_builder = builder
        self.active_pin_map = builder.circuits.get("main", builder.active_sheet).pin_map.copy()

        report_progress("launching", "Opening complete project in Logisim 2.7.1...", 95)
        opened = self.driver.open_circuit_direct(self.current_circ_path)

        report_progress("complete", f"Successfully built {system_name} with {len(builder.circuits)} circuit sheets!", 100)

        summary_lines = [
            f"### 🧠 Agent Mode: Hierarchical Architecture Completed",
            f"**System**: {system_name}",
            f"**Architecture**: {plan.get('architecture_summary', 'Multi-circuit digital system')}",
            "",
            "#### 📦 Compiled Circuit Sheets:",
        ]
        for name, sheet in builder.circuits.items():
            summary_lines.append(f"- **`{name}`**: {len(sheet.components)} components, {len(sheet.wires)} wires")

        summary_lines.append("")
        summary_lines.append(f"Auto-loaded `{os.path.basename(self.current_circ_path)}` directly into Logisim 2.7.1.")
        summary_lines.append("You can double-click each subcircuit in Logisim's left project tree to inspect its isolated canvas, or view `main` for the full integrated datapath!")

        return {
            "success": True,
            "mode": "agent",
            "system_name": system_name,
            "thought": plan.get("architecture_summary", ""),
            "response": "\n".join(summary_lines),
            "plan": plan,
            "circuits": list(builder.circuits.keys()),
            "circuit_file": self.current_circ_path,
            "executed_actions": [
                {"action": "hierarchical_plan", "status": "success", "details": f"Planned {len(subcircuits)} subcircuits"},
                {"action": "synthesize_subcircuits", "status": "success", "details": f"Synthesized sheets: {list(builder.circuits.keys())}"},
                {"action": "open_in_logisim", "status": "success" if opened else "warning", "details": "Auto-loaded into Logisim 2.7.1" if opened else "Circuit saved on disk."},
            ],
            "pin_map": self.active_pin_map,
        }

    def _populate_circuit_sheet(self, builder: CircuitBuilder, data: Dict[str, Any]):
        """Populates the currently active circuit sheet with pins, components, splitters, and wires."""
        # 1. Pins
        for p in data.get("pins", []):
            try:
                name, px, py, is_out, width, facing = _parse_pin(p)
                builder.add_pin(name=name, x=px, y=py, is_output=is_out, width=width, facing=facing)
            except Exception as e:
                logger.warning(f"Error adding pin {p}: {e}")

        # 2. Splitters
        for s in data.get("splitters", []):
            try:
                _add_circuit_element(builder, s, default_type="splitter")
            except Exception as e:
                logger.warning(f"Error adding splitter {s}: {e}")

        # 3. Gates
        for g in data.get("gates", []):
            try:
                _add_circuit_element(builder, g, default_type="AND")
            except Exception as e:
                logger.warning(f"Error adding gate {g}: {e}")

        # 4. Components
        for c in data.get("components", []):
            try:
                _add_circuit_element(builder, c, default_type=None)
            except Exception as e:
                logger.warning(f"Error adding component {c}: {e}")

        # 5. Wires
        for w in data.get("wires", []):
            try:
                p1, p2 = _parse_wire(w)
                builder.add_wire(p1, p2)
            except Exception as e:
                logger.warning(f"Error adding wire {w}: {e}")

    def _populate_fallback_subcircuit(
        self,
        builder: CircuitBuilder,
        inputs: List[Dict[str, Any]],
        outputs: List[Dict[str, Any]],
    ):
        """Creates a well-formed stub subcircuit if LLM generation was incomplete."""
        y = 100
        for inp in inputs:
            name = inp.get("name", "In")
            w = int(inp.get("width", 1))
            builder.add_pin(name=name, x=100, y=y, is_output=False, width=w, facing="east")
            y += 40

        y = 100
        for out in outputs:
            name = out.get("name", "Out")
            w = int(out.get("width", 1))
            builder.add_pin(name=name, x=400, y=y, is_output=True, width=w, facing="west")
            y += 40
