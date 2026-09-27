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


if __name__ == "__main__":
    print("Running AI Logisim Controller Test Suite...")
    test_circ_builder()
    test_templates()
    test_wire_snapping()
    test_priority_encoder()
    test_normalization()
    test_driver()
    print("\nALL TESTS PASSED SUCCESSFULLY!")


