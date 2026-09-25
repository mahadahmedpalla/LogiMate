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
    test_driver()
    print("\nALL TESTS PASSED SUCCESSFULLY!")

