"""
Unit and integration test suite for AI Logisim Controller.
"""

import os
import xml.etree.ElementTree as ET
from logisim_engine.circ_builder import CircuitBuilder
from logisim_engine.driver import LogisimDriver
from agent.circuit_templates import (
    build_half_adder,
    build_full_adder,
    build_mux_2to1,
    build_sr_latch,
)


def test_circ_builder():
    b = CircuitBuilder("test_circ")
    p1 = b.add_pin("A", 100, 100)
    p2 = b.add_pin("B", 100, 140)
    g = b.add_gate("AND", 200, 120, inputs=2)
    b.add_wire(p1, g["inputs"][0])
    b.add_wire(p2, g["inputs"][1])
    p_out = b.add_pin("Out", 260, 120, is_output=True)
    b.add_wire(g["out"], p_out)

    xml_text = b.to_xml()
    # Verify XML can parse
    root = ET.fromstring(xml_text)
    assert root.tag == "project"
    assert root.attrib["source"] == "2.7.1"
    assert b.pin_map["A"] == (100, 100)
    assert b.pin_map["Out"] == (260, 120)
    print("[PASS] CircuitBuilder test passed")


def test_templates():
    templates = [
        ("Half Adder", build_half_adder),
        ("Full Adder", build_full_adder),
        ("2:1 MUX", build_mux_2to1),
        ("SR Latch", build_sr_latch),
    ]

    for name, fn in templates:
        b = CircuitBuilder()
        fn(b)
        xml = b.to_xml()
        root = ET.fromstring(xml)
        assert root.tag == "project"
        assert len(b.components) > 0
        assert len(b.wires) > 0
        print(f"[PASS] Template '{name}' passed ({len(b.components)} components, {len(b.wires)} wires, pins: {list(b.pin_map.keys())})")


def test_wire_snapping():
    b = CircuitBuilder("test_snap")
    b.add_arithmetic("Comparator", 200, 150, width=8)
    b.add_pin("A", 100, 140, width=8)
    b.add_pin("B", 100, 160, width=8)
    b.add_pin("A_greater_B", 280, 140, is_output=True)
    b.add_pin("A_equal_B", 280, 150, is_output=True)
    b.add_pin("A_less_B", 280, 160, is_output=True)

    # Inputs connect cleanly
    b.add_wire((100, 140), (160, 140))
    b.add_wire((100, 160), (160, 160))

    # Outputs have intentional 20px gap (start at x=220 instead of x=200)
    b.add_wire((220, 140), (280, 140))
    b.add_wire((220, 150), (280, 150))
    b.add_wire((220, 160), (280, 160))

    xml_text = b.to_xml()
    root = ET.fromstring(xml_text)
    circ = root.find("circuit")
    wires = circ.findall("wire")

    terminals = {"(200,140)", "(200,150)", "(200,160)"}
    connected = set()
    for w in wires:
        f, t = w.attrib.get("from"), w.attrib.get("to")
        if f in terminals:
            connected.add(f)
        if t in terminals:
            connected.add(t)

    assert connected == terminals, f"Failed to snap terminals: {terminals - connected}"
    print(f"[PASS] Wire Gap Snapper test passed ({len(wires)} wires perfectly connected to all 3 comparator terminals)")


def test_priority_encoder():
    b = CircuitBuilder("test_priority_encoder")
    # Add 4-to-2 Priority Encoder at (200, 150)
    b.add_component("Priority Encoder", 200, 150, attrs={"select": "2"})
    b.add_pin("D0", 100, 140)
    b.add_pin("D1", 100, 150)
    b.add_pin("D2", 100, 160)
    b.add_pin("D3", 100, 170)
    b.add_pin("Code", 280, 150, width=2, is_output=True)
    b.add_pin("AnyActive", 280, 160, is_output=True)

    # Wires with intentional gaps
    b.add_wire((100, 140), (150, 140)) # 10px short of (160, 140)
    b.add_wire((100, 150), (160, 150))
    b.add_wire((100, 160), (160, 160))
    b.add_wire((100, 170), (160, 170))
    b.add_wire((210, 150), (280, 150)) # 10px gap from (200, 150)
    b.add_wire((200, 160), (280, 160))

    xml_text = b.to_xml()
    root = ET.fromstring(xml_text)
    circ = root.find("circuit")
    comp = circ.find(".//comp[@name='Priority Encoder']")
    assert comp is not None, "Priority Encoder component missing from XML"
    assert comp.find(".//a[@name='select']").attrib["val"] == "2"

    # Verify that wire snapping closed the gaps to (160, 140) and (200, 150)
    wires = circ.findall("wire")
    wire_points = set()
    for w in wires:
        wire_points.add(w.attrib.get("from"))
        wire_points.add(w.attrib.get("to"))

    assert "(160,140)" in wire_points, "D0 terminal was not connected"
    assert "(200,150)" in wire_points, "Code OUT terminal was not connected"
    assert "(200,160)" in wire_points, "GS AnyActive terminal was not connected"
    print(f"[PASS] Priority Encoder test passed (select=2, all terminals verified)")


def test_normalization():
    b = CircuitBuilder("test_norm")
    # 1. Full Adder alias test
    comp1 = b.add_component("Full Adder", 200, 100)
    assert comp1.lib == 3, f"Expected lib 3, got {comp1.lib}"
    assert comp1.name == "Adder", f"Expected 'Adder', got {comp1.name}"

    res = b.add_arithmetic("FullAdder", 200, 160)
    assert res["component"].name == "Adder"

    # 2. Probe radix normalization test
    b.add_probe(300, 100, radix=10)
    b.add_probe(300, 140, radix="10")
    b.add_probe(300, 180, radix="10unsigned")
    b.add_probe(300, 220, radix=2)

    xml_text = b.to_xml()
    root = ET.fromstring(xml_text)
    circ = root.find("circuit")

    # Verify no 'Full Adder' in XML, only 'Adder' in lib 3
    adders = circ.findall(".//comp[@name='Adder']")
    assert len(adders) == 2, f"Expected 2 Adders, found {len(adders)}"

    # Verify Probes
    probes = circ.findall(".//comp[@name='Probe']")
    assert len(probes) == 4
    radixes = [p.find(".//a[@name='radix']").attrib["val"] for p in probes]
    assert radixes == ["10signed", "10signed", "10unsigned", "2"], f"Unexpected radixes: {radixes}"
    print(f"[PASS] Normalization test passed (Full Adder -> Adder, radix 10 -> 10signed)")


def test_driver():
    driver = LogisimDriver()
    # Should safely report connection status without error
    info = driver.get_window_info()
    assert "connected" in info
    print(f"[PASS] LogisimDriver test passed (connected={info['connected']})")


def test_multi_circuit():
    b = CircuitBuilder("main")
    # Subcircuit 1: ALU
    b.set_active_circuit("ALU")
    p1 = b.add_pin("A", 100, 100, width=8)
    p2 = b.add_pin("B", 100, 140, width=8)
    adder = b.add_arithmetic("Adder", 200, 120, width=8)
    p_out = b.add_pin("Result", 260, 120, is_output=True, width=8)
    b.add_wire(p1, (160, 110))
    b.add_wire(p2, (160, 130))
    b.add_wire((200, 120), p_out)

    # Subcircuit 2: Register
    b.set_active_circuit("Register")
    d_in = b.add_pin("D", 100, 100, width=8)
    reg = b.add_register(200, 100, width=8)
    q_out = b.add_pin("Q", 260, 100, is_output=True, width=8)
    b.add_wire(d_in, reg["d"])
    b.add_wire(reg["q"], q_out)

    # Top-Level: main
    b.set_active_circuit("main")
    alu_chip = b.add_subcircuit_instance("ALU", 220, 160, label="ALU_1")
    reg_chip = b.add_subcircuit_instance("Register", 120, 120, label="REG_A")

    xml_text = b.to_xml()
    root = ET.fromstring(xml_text)

    # Verify main project element
    main_elem = root.find("main")
    assert main_elem is not None and main_elem.attrib["name"] == "main"

    # Verify circuits defined
    circuits = {c.attrib["name"]: c for c in root.findall("circuit")}
    assert "ALU" in circuits, "ALU circuit missing from project XML"
    assert "Register" in circuits, "Register circuit missing from project XML"
    assert "main" in circuits, "main circuit missing from project XML"

    # Verify main circuit has the subcircuit instances without lib attribute
    main_comps = circuits["main"].findall("comp")
    assert len(main_comps) == 2
    comp_names = [c.attrib.get("name") for c in main_comps]
    assert "ALU" in comp_names and "Register" in comp_names
    for c in main_comps:
        assert "lib" not in c.attrib, f"Subcircuit component should not have lib attribute: {ET.tostring(c)}"

    print(f"[PASS] Multi-Circuit test passed (Subcircuits: {list(circuits.keys())})")


def test_planner_agent():
    from unittest.mock import MagicMock
    from agent.planner_agent import PlannerAgent
    import tempfile

    mock_gemini = MagicMock()
    mock_driver = MagicMock()
    mock_driver.open_circuit_direct.return_value = True

    mock_gemini.generate_json.side_effect = [
        # Decomposition plan
        {
            "success": True,
            "data": {
                "system_name": "Test CPU",
                "architecture_summary": "8-bit micro architecture",
                "subcircuits": [
                    {
                        "name": "ALU",
                        "purpose": "8-bit ALU",
                        "inputs": [{"name": "A", "width": 8}, {"name": "B", "width": 8}],
                        "outputs": [{"name": "Result", "width": 8}]
                    },
                    {
                        "name": "Register",
                        "purpose": "8-bit Register",
                        "inputs": [{"name": "D", "width": 8}],
                        "outputs": [{"name": "Q", "width": 8}]
                    }
                ],
                "assembly_strategy": "Interconnect on main"
            }
        },
        # ALU synthesis
        {
            "success": True,
            "data": {
                "pins": [
                    {"name": "A", "loc": [100, 100], "width": 8, "is_output": False},
                    {"name": "B", "loc": [100, 140], "width": 8, "is_output": False},
                    {"name": "Result", "loc": [300, 120], "width": 8, "is_output": True}
                ],
                "components": [
                    {"type": "Adder", "loc": [200, 120], "width": 8}
                ],
                "wires": [
                    {"from": [100, 100], "to": [160, 110]},
                    {"from": [100, 140], "to": [160, 130]},
                    {"from": [200, 120], "to": [300, 120]}
                ]
            }
        },
        # Register synthesis
        {
            "success": True,
            "data": {
                "pins": [
                    {"name": "D", "loc": [100, 100], "width": 8, "is_output": False},
                    {"name": "Q", "loc": [300, 100], "width": 8, "is_output": True}
                ],
                "components": [
                    {"type": "Register", "loc": [200, 100], "width": 8}
                ],
                "wires": [
                    {"from": [100, 100], "to": [170, 100]},
                    {"from": [200, 100], "to": [300, 100]}
                ]
            }
        },
        # Assembly on main
        {
            "success": True,
            "data": {
                "subcircuit_instances": [
                    {"name": "ALU", "loc": [260, 160], "label": "ALU_1"},
                    {"name": "Register", "loc": [120, 120], "label": "R0"}
                ],
                "pins": [
                    {"name": "CLK", "loc": [60, 100], "width": 1, "is_output": False}
                ],
                "components": [
                    {"type": "Probe", "loc": [380, 160], "radix": "16", "label": "ALU_OUT"}
                ],
                "wires": []
            }
        }
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        planner = PlannerAgent(gemini_client=mock_gemini, driver=mock_driver, workspace_dir=tmpdir)
        progress_events = []
        result = planner.execute_hierarchical_plan(
            "Build an 8-bit Mini CPU",
            progress_callback=lambda evt: progress_events.append(evt)
        )

        assert result["success"] is True
        assert result["mode"] == "agent"
        assert set(result["circuits"]) == {"main", "ALU", "Register"}
        assert os.path.exists(result["circuit_file"])
        assert len(progress_events) >= 5

        # Verify generated XML
        root = ET.parse(result["circuit_file"]).getroot()
        circs = {c.attrib["name"]: c for c in root.findall("circuit")}
        assert "main" in circs and "ALU" in circs and "Register" in circs
        print(f"[PASS] PlannerAgent Hierarchical Synthesis test passed ({len(progress_events)} progress steps verified)")


def test_server_endpoints():
    from unittest.mock import patch
    from starlette.testclient import TestClient
    from server import app, agent, planner_agent

    client = TestClient(app)

    # 1. Normal Mode Chat
    with patch.object(agent, "execute_prompt") as mock_exec:
        mock_exec.return_value = {
            "success": True,
            "thought": "Normal mode synthesis",
            "response": "Built half adder",
            "executed_actions": [],
            "pin_map": {"A": [100, 100]}
        }
        res = client.post("/api/chat", json={"prompt": "build half adder", "mode": "normal"})
        assert res.status_code == 200
        data = res.json()
        assert data["thought"] == "Normal mode synthesis"
        mock_exec.assert_called_once_with("build half adder")

    # 2. Agent Mode Chat (synchronous)
    with patch.object(planner_agent, "execute_hierarchical_plan") as mock_plan:
        mock_plan.return_value = {
            "success": True,
            "mode": "agent",
            "system_name": "8-bit CPU",
            "response": "Built 8-bit CPU",
            "circuits": ["main", "ALU", "Register"],
            "executed_actions": []
        }
        res = client.post("/api/chat", json={"prompt": "build cpu", "mode": "agent"})
        assert res.status_code == 200
        data = res.json()
        assert data["mode"] == "agent"
        mock_plan.assert_called_once_with("build cpu")

    # 3. Agent Mode Streaming
    with patch.object(planner_agent, "execute_hierarchical_plan") as mock_plan_stream:
        def fake_exec(prompt, callback=None):
            if callback:
                callback({"step": "planning", "message": "Analyzing system...", "percent": 10})
                callback({"step": "synthesizing", "message": "Synthesized ALU", "percent": 50})
            return {
                "success": True,
                "mode": "agent",
                "system_name": "8-bit CPU",
                "response": "Finished streaming build",
                "circuits": ["main", "ALU"],
                "executed_actions": []
            }
        mock_plan_stream.side_effect = fake_exec
        res = client.post("/api/chat-agent-stream", json={"prompt": "build cpu", "mode": "agent"})
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]
        events = [line for line in res.text.split("\n\n") if line.strip().startswith("data: ")]
        assert len(events) >= 2

    print(f"[PASS] Server Endpoints & Streaming test passed (Normal + Agent Mode)")


def test_gemini_client_resilience():
    from unittest.mock import MagicMock, patch
    from agent.gemini_client import GeminiClient

    # Test 1: Verify HttpOptions has timeout=45000 (45s)
    client = GeminiClient(api_key="test_key_abc", model_id="gemini-3.6-flash")
    assert client._client is not None
    assert client._client._api_client._http_options.timeout == 45000

    # Test 2: Simulate 429 Rate Limit on gemini-3.6-flash, followed by successful fallback on gemini-2.5-flash
    mock_resp_success = MagicMock()
    mock_resp_success.text = '{"success": true, "pins": []}'
    status_updates = []

    def mock_generate_content(model, contents, config):
        if model == "gemini-3.6-flash":
            raise Exception("429 RESOURCE_EXHAUSTED: Rate limit exceeded")
        return mock_resp_success

    client._client.models.generate_content = mock_generate_content

    with patch("time.sleep", return_value=None):
        resp = client.generate_json(
            prompt="Build ALU",
            status_callback=lambda msg: status_updates.append(msg)
        )

    assert resp["success"] is True
    assert resp["data"] == {"success": True, "pins": []}
    assert any("rate limit reached" in msg for msg in status_updates)
    assert any("Switching from gemini-3.6-flash to fallback gemini-2.5-flash" in msg for msg in status_updates)

    print(f"[PASS] GeminiClient Resilience test passed (Timeout 45s, 429 auto-backoff & fallback verified)")


if __name__ == "__main__":
    print("Running AI Logisim Controller Test Suite...")
    test_circ_builder()
    test_templates()
    test_wire_snapping()
    test_priority_encoder()
    test_normalization()
    test_multi_circuit()
    test_planner_agent()
    test_gemini_client_resilience()
    test_server_endpoints()
    test_driver()
    print("\nALL TESTS PASSED SUCCESSFULLY!")



