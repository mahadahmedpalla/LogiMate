"""
Pre-engineered, pixel-perfect circuit templates for Logisim 2.7.1.
Guarantees flawless wiring and layout for standard digital logic building blocks.
"""

from typing import Tuple, Dict, Any
from logisim_engine.circ_builder import CircuitBuilder


def build_half_adder(builder: CircuitBuilder, base_x: int = 140, base_y: int = 140) -> Dict[str, Any]:
    """Builds a Half Adder (Sum = A ^ B, Carry = A & B)."""
    pA = builder.add_pin("A", base_x, base_y)
    pB = builder.add_pin("B", base_x, base_y + 40)

    # XOR Gate for Sum
    xor_gate = builder.add_gate("XOR", base_x + 120, base_y + 20, inputs=2)
    # AND Gate for Carry
    and_gate = builder.add_gate("AND", base_x + 120, base_y + 90, inputs=2)

    # Wires from A
    builder.add_wire(pA, (base_x + 40, base_y))
    builder.add_wire((base_x + 40, base_y), xor_gate["inputs"][0])
    builder.add_wire((base_x + 40, base_y), (base_x + 40, base_y + 70))
    builder.add_wire((base_x + 40, base_y + 70), and_gate["inputs"][0])

    # Wires from B
    builder.add_wire(pB, (base_x + 60, base_y + 40))
    builder.add_wire((base_x + 60, base_y + 40), xor_gate["inputs"][1])
    builder.add_wire((base_x + 60, base_y + 40), (base_x + 60, base_y + 110))
    builder.add_wire((base_x + 60, base_y + 110), and_gate["inputs"][1])

    # Outputs
    pSum = builder.add_pin("Sum", base_x + 190, base_y + 20, is_output=True)
    pCarry = builder.add_pin("Carry", base_x + 190, base_y + 90, is_output=True)

    builder.add_wire(xor_gate["out"], pSum)
    builder.add_wire(and_gate["out"], pCarry)

    return {
        "inputs": ["A", "B"],
        "outputs": ["Sum", "Carry"],
    }


def build_full_adder(builder: CircuitBuilder, base_x: int = 120, base_y: int = 120) -> Dict[str, Any]:
    """Builds a 1-bit Full Adder with inputs A, B, Cin and outputs Sum, Cout."""
    pA = builder.add_pin("A", base_x, base_y)
    pB = builder.add_pin("B", base_x, base_y + 40)
    pCin = builder.add_pin("Cin", base_x, base_y + 80)

    # First stage: XOR1 and AND1
    xor1 = builder.add_gate("XOR", base_x + 110, base_y + 20, inputs=2)
    and1 = builder.add_gate("AND", base_x + 110, base_y + 150, inputs=2)

    builder.add_wire(pA, (base_x + 30, base_y))
    builder.add_wire((base_x + 30, base_y), xor1["inputs"][0])
    builder.add_wire((base_x + 30, base_y), (base_x + 30, base_y + 130))
    builder.add_wire((base_x + 30, base_y + 130), and1["inputs"][0])

    builder.add_wire(pB, (base_x + 40, base_y + 40))
    builder.add_wire((base_x + 40, base_y + 40), xor1["inputs"][1])
    builder.add_wire((base_x + 40, base_y + 40), (base_x + 40, base_y + 170))
    builder.add_wire((base_x + 40, base_y + 170), and1["inputs"][1])

    # Second stage: XOR2 for Sum and AND2 for intermediate carry
    xor2 = builder.add_gate("XOR", base_x + 230, base_y + 30, inputs=2)
    and2 = builder.add_gate("AND", base_x + 230, base_y + 90, inputs=2)

    # Connect xor1 out to xor2 and and2
    builder.add_wire(xor1["out"], (base_x + 140, base_y + 20))
    builder.add_wire((base_x + 140, base_y + 20), (base_x + 140, base_y + 10))
    builder.add_wire((base_x + 140, base_y + 10), xor2["inputs"][0])
    builder.add_wire((base_x + 140, base_y + 20), (base_x + 140, base_y + 70))
    builder.add_wire((base_x + 140, base_y + 70), and2["inputs"][0])

    # Connect Cin to xor2 and and2
    builder.add_wire(pCin, (base_x + 160, base_y + 80))
    builder.add_wire((base_x + 160, base_y + 80), (base_x + 160, base_y + 50))
    builder.add_wire((base_x + 160, base_y + 50), xor2["inputs"][1])
    builder.add_wire((base_x + 160, base_y + 80), (base_x + 160, base_y + 110))
    builder.add_wire((base_x + 160, base_y + 110), and2["inputs"][1])

    # Final stage: OR gate for Cout (AND1_out | AND2_out)
    or_gate = builder.add_gate("OR", base_x + 330, base_y + 120, inputs=2)
    builder.add_wire(and2["out"], (base_x + 260, base_y + 90))
    builder.add_wire((base_x + 260, base_y + 90), (base_x + 260, base_y + 100))
    builder.add_wire((base_x + 260, base_y + 100), or_gate["inputs"][0])

    builder.add_wire(and1["out"], (base_x + 260, base_y + 150))
    builder.add_wire((base_x + 260, base_y + 150), (base_x + 260, base_y + 140))
    builder.add_wire((base_x + 260, base_y + 140), or_gate["inputs"][1])

    # Outputs
    pSum = builder.add_pin("Sum", base_x + 380, base_y + 30, is_output=True)
    pCout = builder.add_pin("Cout", base_x + 380, base_y + 120, is_output=True)

    builder.add_wire(xor2["out"], pSum)
    builder.add_wire(or_gate["out"], pCout)

    return {
        "inputs": ["A", "B", "Cin"],
        "outputs": ["Sum", "Cout"],
    }


def build_mux_2to1(builder: CircuitBuilder, base_x: int = 120, base_y: int = 120) -> Dict[str, Any]:
    """Builds a 2-to-1 Multiplexer (Y = (D0 & ~S) | (D1 & S))."""
    pD0 = builder.add_pin("D0", base_x, base_y)
    pD1 = builder.add_pin("D1", base_x, base_y + 120)
    pS = builder.add_pin("S", base_x, base_y + 60)

    # Inverter for S
    not_gate = builder.add_gate("NOT", base_x + 90, base_y + 40)
    builder.add_wire(pS, (base_x + 40, base_y + 60))
    builder.add_wire((base_x + 40, base_y + 60), (base_x + 40, base_y + 40))
    builder.add_wire((base_x + 40, base_y + 40), not_gate["inputs"][0])

    # AND Gate 0 (D0 & ~S)
    and0 = builder.add_gate("AND", base_x + 190, base_y + 20, inputs=2)
    builder.add_wire(pD0, and0["inputs"][0])
    builder.add_wire(not_gate["out"], and0["inputs"][1])

    # AND Gate 1 (D1 & S)
    and1 = builder.add_gate("AND", base_x + 190, base_y + 100, inputs=2)
    builder.add_wire((base_x + 40, base_y + 60), (base_x + 40, base_y + 80))
    builder.add_wire((base_x + 40, base_y + 80), and1["inputs"][0])
    builder.add_wire(pD1, and1["inputs"][1])

    # OR Gate (AND0 | AND1)
    or_gate = builder.add_gate("OR", base_x + 280, base_y + 60, inputs=2)
    builder.add_wire(and0["out"], (base_x + 210, base_y + 20))
    builder.add_wire((base_x + 210, base_y + 20), (base_x + 210, base_y + 40))
    builder.add_wire((base_x + 210, base_y + 40), or_gate["inputs"][0])

    builder.add_wire(and1["out"], (base_x + 210, base_y + 100))
    builder.add_wire((base_x + 210, base_y + 100), (base_x + 210, base_y + 80))
    builder.add_wire((base_x + 210, base_y + 80), or_gate["inputs"][1])

    pY = builder.add_pin("Y", base_x + 330, base_y + 60, is_output=True)
    builder.add_wire(or_gate["out"], pY)

    return {
        "inputs": ["D0", "S", "D1"],
        "outputs": ["Y"],
    }


def build_sr_latch(builder: CircuitBuilder, base_x: int = 140, base_y: int = 140) -> Dict[str, Any]:
    """Builds an SR Latch using two cross-coupled NOR gates."""
    pR = builder.add_pin("R", base_x, base_y)
    pS = builder.add_pin("S", base_x, base_y + 120)

    nor1 = builder.add_gate("NOR", base_x + 140, base_y + 20, inputs=2)
    nor2 = builder.add_gate("NOR", base_x + 140, base_y + 100, inputs=2)

    builder.add_wire(pR, nor1["inputs"][0])
    builder.add_wire(pS, nor2["inputs"][1])

    pQ = builder.add_pin("Q", base_x + 230, base_y + 20, is_output=True)
    pQnot = builder.add_pin("Q_not", base_x + 230, base_y + 100, is_output=True)

    builder.add_wire(nor1["out"], pQ)
    builder.add_wire(nor2["out"], pQnot)

    # Cross connections
    builder.add_wire((base_x + 160, base_y + 20), (base_x + 160, base_y + 60))
    builder.add_wire((base_x + 160, base_y + 60), (base_x + 70, base_y + 60))
    builder.add_wire((base_x + 70, base_y + 60), (base_x + 70, base_y + 80))
    builder.add_wire((base_x + 70, base_y + 80), nor2["inputs"][0])

    builder.add_wire((base_x + 180, base_y + 100), (base_x + 180, base_y + 70))
    builder.add_wire((base_x + 180, base_y + 70), (base_x + 80, base_y + 70))
    builder.add_wire((base_x + 80, base_y + 70), (base_x + 80, base_y + 40))
    builder.add_wire((base_x + 80, base_y + 40), nor1["inputs"][1])

    return {
        "inputs": ["R", "S"],
        "outputs": ["Q", "Q_not"],
    }
