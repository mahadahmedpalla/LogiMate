"""
Unit and integration test suite for AI Logisim Controller.
"""

import os
import xml.etree.ElementTree as ET
from logisim_engine.circ_builder import CircuitBuilder, Wire
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


def test_width_aware_snapping():
    b = CircuitBuilder("test_width_snap")
    # 8-bit Adder at (220, 80): IN0 (180, 70)[8], IN1 (180, 90)[8], OUT (220, 80)[8], c_in (200, 60)[1], c_out (200, 100)[1]
    b.add_arithmetic("Adder", 220, 80, width=8)

    # 1. 8-bit input pin B: wire ending at (190, 100), 10px from 1-bit c_out at (200, 100)
    b.add_pin("B", 80, 100, width=8)
    b.add_wire((80, 100), (190, 100))

    # 2. 2-bit OpCode pin: wire ending at (130, 200), 10px from 8-bit vertical trunk at x=140
    b.add_pin("OpCode", 80, 200, width=2)
    b.add_wire((80, 200), (130, 200))

    # 3. 8-bit vertical trunk at x=140
    b.add_pin("Data_Trunk", 80, 50, width=8)
    b.add_wire((80, 50), (140, 50))
    b.add_wire((140, 50), (140, 250))

    xml = b.to_xml()
    root = ET.fromstring(xml)
    wires = root.find("circuit").findall("wire")
    wire_points = set()
    for w in wires:
        wire_points.add(w.attrib["from"])
        wire_points.add(w.attrib["to"])

    # Verify that the 8-bit wire was NEVER snapped to 1-bit c_out (200, 100)
    assert "(200,100)" not in wire_points, "ERROR: 8-bit bus was incorrectly snapped to 1-bit c_out!"

    # Verify that the 2-bit wire was NEVER snapped to the 8-bit trunk at (140, 200)
    assert not any(w.attrib.get("from") == "(80,200)" and w.attrib.get("to") == "(140,200)" for w in wires), \
        "ERROR: 2-bit OpCode was incorrectly merged into the 8-bit data trunk!"

    print("[PASS] Width-Aware Snapping test passed (1-bit c_out and 8-bit trunk protected from incompatible shorts)")


def test_mux_4to1_snapping():
    b = CircuitBuilder("test_mux_snap")
    # 4:1 MUX at (380, 200), select=2, width=8
    # Terminals: in0=(340, 180), in1=(340, 190), in2=(340, 200), in3=(340, 210)
    b.add_component("Multiplexer", 380, 200, attrs={"select": "2", "width": "8"})

    # 4 Wires ending 20px short at x=320 with staggered vertical trunks
    b.add_wire((240, 100), (280, 100))
    b.add_wire((280, 100), (280, 180))
    b.add_wire((280, 180), (320, 180)) # 20px short of (340, 180)

    b.add_wire((240, 180), (290, 180))
    b.add_wire((290, 180), (290, 190))
    b.add_wire((290, 190), (320, 190)) # 20px short of (340, 190)

    b.add_wire((240, 260), (300, 260))
    b.add_wire((300, 260), (300, 200))
    b.add_wire((300, 200), (320, 200)) # 20px short of (340, 200)

    b.add_wire((240, 340), (310, 340))
    b.add_wire((310, 340), (310, 210))
    b.add_wire((310, 210), (320, 210)) # 20px short of (340, 210)

    xml = b.to_xml()
    root = ET.fromstring(xml)
    wires = root.find("circuit").findall("wire")
    wire_points = set()
    for w in wires:
        wire_points.add(w.attrib["from"])
        wire_points.add(w.attrib["to"])

    expected = {"(340,180)", "(340,190)", "(340,200)", "(340,210)"}
    assert expected.issubset(wire_points), f"Missing MUX terminals: {expected - wire_points}"
    print("[PASS] 4:1 Multiplexer Snapping test passed (all 4 data inputs snapped cleanly without overlaps)")


def test_driver():
    driver = LogisimDriver()
    # Should safely report connection status without error
    info = driver.get_window_info()
    assert "connected" in info
    print(f"[PASS] LogisimDriver test passed (connected={info['connected']})")


def test_erc_cross_width_pruning():
    b = CircuitBuilder("test_erc_alu")
    b.add_pin("A", 100, 100, width=8)
    b.add_pin("B", 100, 200, width=8)
    b.add_pin("OpCode", 280, 360, width=2)
    b.add_component("XOR Gate", 240, 360, attrs={"width": "8", "inputs": "2", "size": "50"})
    b.add_component("Multiplexer", 380, 200, attrs={"select": "2", "width": "8"})

    # Raw Gemini wires containing illegal cross-width bridges:
    # 1. 8-bit XOR to 2-bit OpCode
    b.add_wire((240, 360), (280, 360))
    # 2. 2-bit OpCode to 8-bit MUX In3
    b.add_wire((280, 360), (340, 210))
    # 3. 2-bit OpCode to 2-bit MUX Select (valid!)
    b.add_wire((280, 360), (360, 220))

    xml = b.to_xml()
    root = ET.fromstring(xml)
    wires = root.find("circuit").findall("wire")

    # Verify that illegal cross-width bridges were severed
    for w in wires:
        p1, p2 = w.attrib["from"], w.attrib["to"]
        pts = {p1, p2}
        assert not ("(240,360)" in pts and "(280,360)" in pts), "ERROR: Illegal 8-bit to 2-bit bridge was not pruned!"
        assert not ("(340,210)" in pts and "(280,360)" in pts), "ERROR: Illegal 2-bit to 8-bit bridge was not pruned!"

    # Verify that the 2-bit OpCode connects to MUX select (360, 220)
    wire_points = set()
    for w in wires:
        wire_points.add(w.attrib["from"])
        wire_points.add(w.attrib["to"])
    assert "(360,220)" in wire_points, "ERROR: Valid 2-bit MUX select wire was lost!"
    assert "(280,360)" in wire_points, "ERROR: Valid OpCode pin connection was lost!"

    print("[PASS] Electrical Rules Check (ERC) test passed (illegal cross-width bridges severed, valid nets preserved)")


def test_manhattan_enforcement():
    b = CircuitBuilder("test_manhattan")
    b.add_pin("In", 100, 100)
    b.add_pin("Out", 300, 300, is_output=True)

    # Intentionally inject diagonal and degenerate wires
    b.wires.append(Wire((100, 100), (200, 200)))   # Diagonal wire!
    b.wires.append(Wire((200, 200), (300, 300)))   # Diagonal wire!
    b.wires.append(Wire((150, 150), (150, 150)))   # Zero-length degenerate wire!
    b.wires.append(Wire((100, 100), (200, 100)))   # Valid orthogonal wire
    b.wires.append(Wire((200, 100), (100, 100)))   # Reverse duplicate of above

    xml = b.to_xml()
    root = ET.fromstring(xml)
    wires = root.find("circuit").findall("wire")

    # Verify that every wire in the XML is strictly Manhattan orthogonal (x1 == x2 or y1 == y2)
    for w in wires:
        p1 = eval(w.attrib["from"])
        p2 = eval(w.attrib["to"])
        assert p1 != p2, f"ERROR: Degenerate zero-length wire {p1} -> {p2} was not pruned!"
        assert p1[0] == p2[0] or p1[1] == p2[1], (
            f"CRITICAL ERROR: Non-orthogonal (diagonal) wire {p1} -> {p2} detected! "
            f"Diagonal wires cause Logisim to hang in an infinite heap allocation loop."
        )

    print("[PASS] Manhattan Enforcer test passed (all diagonal wires decomposed, zero diagonals in XML)")


def test_groq_client():
    from agent.groq_client import GroqClient, _extract_json_response, AVAILABLE_GROQ_MODELS

    # Verify requested models exist in available roster
    model_ids = [m["id"] for m in AVAILABLE_GROQ_MODELS]
    assert "qwen/qwen3.8-27b" in model_ids, "Missing Qwen 3.8 model in Groq roster"
    assert "llama-3.3-70b-versatile" in model_ids, "Missing Llama 3.3 70B model in Groq roster"

    # Test 1: Markdown code block parsing
    sample_md = "```json\n{\"thought\": \"Routing adder\", \"response\": \"Adder built.\", \"actions\": [{\"action\": \"open_in_logisim\"}]}\n```"
    p1 = _extract_json_response(sample_md)
    assert p1.get("thought") == "Routing adder"
    assert p1.get("response") == "Adder built."
    assert len(p1.get("actions", [])) == 1

    # Test 2: Chain of thought <think> tag extraction (Qwen / DeepSeek reasoning)
    sample_think = "<think>Calculating carry bits for adder</think>\n{\"response\": \"Calculated\", \"actions\": []}"
    p2 = _extract_json_response(sample_think)
    assert p2.get("thought") == "Calculating carry bits for adder"
    assert p2.get("response") == "Calculated"

    # Test 3: Client instantiation and credentials
    client = GroqClient(api_key="gsk_test", model_id="qwen/qwen3.8-27b")
    assert client.model_id == "qwen/qwen3.8-27b"
    client.set_credentials("gsk_test2", "llama-3.3-70b-versatile")
    assert client.model_id == "llama-3.3-70b-versatile"

    # Test 4: Empty API key check
    empty_client = GroqClient(api_key="")
    res = empty_client.generate_chat_response([{"role": "user", "content": "test"}])
    assert res["success"] is False
    assert "No Groq API key" in res["error"]

    print("[PASS] Groq Client test passed (Qwen 3.8 & Llama 3.3 models verified, JSON/CoT parsing clean)")


if __name__ == "__main__":
    print("Running AI Logisim Controller Test Suite...")
    test_circ_builder()
    test_templates()
    test_wire_snapping()
    test_priority_encoder()
    test_normalization()
    test_width_aware_snapping()
    test_mux_4to1_snapping()
    test_erc_cross_width_pruning()
    test_manhattan_enforcement()
    test_groq_client()
    test_driver()
    print("\nALL TESTS PASSED SUCCESSFULLY!")



