"""
Logisim 2.7.1 Circuit XML Generator and Component Coordinate Tracker.
Builds valid, clean .circ XML files supporting the full suite of Logisim digital logic components:
Gates, Multi-bit Pins, Splitters, Multiplexers, Adders/Arithmetic, Registers/Memory, Probes, Tunnels, and Clocks.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Union
import collections
import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger("AI_Logisim_Controller.circ_builder")



COMPONENT_LIB_MAP = {
    # Wiring (lib=0)
    "PIN": (0, "Pin"),
    "SPLITTER": (0, "Splitter"),
    "PROBE": (0, "Probe"),
    "TUNNEL": (0, "Tunnel"),
    "CLOCK": (0, "Clock"),
    "CONSTANT": (0, "Constant"),
    "PULL RESISTOR": (0, "Pull Resistor"),
    "GROUND": (0, "Ground"),
    "POWER": (0, "Power"),
    "BIT EXTENDER": (0, "Bit Extender"),

    # Gates (lib=1)
    "AND": (1, "AND Gate"),
    "AND GATE": (1, "AND Gate"),
    "OR": (1, "OR Gate"),
    "OR GATE": (1, "OR Gate"),
    "NOT": (1, "NOT Gate"),
    "NOT GATE": (1, "NOT Gate"),
    "NAND": (1, "NAND Gate"),
    "NAND GATE": (1, "NAND Gate"),
    "NOR": (1, "NOR Gate"),
    "NOR GATE": (1, "NOR Gate"),
    "XOR": (1, "XOR Gate"),
    "XOR GATE": (1, "XOR Gate"),
    "XNOR": (1, "XNOR Gate"),
    "XNOR GATE": (1, "XNOR Gate"),
    "BUFFER": (1, "Buffer"),

    # Plexers (lib=2)
    "MULTIPLEXER": (2, "Multiplexer"),
    "MUX": (2, "Multiplexer"),
    "DEMULTIPLEXER": (2, "Demultiplexer"),
    "DEMUX": (2, "Demultiplexer"),
    "DECODER": (2, "Decoder"),
    "PRIORITY ENCODER": (2, "Priority Encoder"),
    "BIT SELECTOR": (2, "Bit Selector"),

    # Arithmetic (lib=3)
    "ADDER": (3, "Adder"),
    "FULL ADDER": (3, "Adder"),
    "FULLADDER": (3, "Adder"),
    "1-BIT FULL ADDER": (3, "Adder"),
    "1-BIT ADDER": (3, "Adder"),
    "SUBTRACTOR": (3, "Subtractor"),
    "MULTIPLIER": (3, "Multiplier"),
    "DIVIDER": (3, "Divider"),
    "NEGATOR": (3, "Negator"),
    "COMPARATOR": (3, "Comparator"),
    "SHIFTER": (3, "Shifter"),
    "BITADDER": (3, "BitAdder"),

    # Memory (lib=4)
    "REGISTER": (4, "Register"),
    "COUNTER": (4, "Counter"),
    "SHIFT REGISTER": (4, "Shift Register"),
    "D FLIP-FLOP": (4, "D Flip-Flop"),
    "T FLIP-FLOP": (4, "T Flip-Flop"),
    "J-K FLIP-FLOP": (4, "J-K Flip-Flop"),
    "S-R FLIP-FLOP": (4, "S-R Flip-Flop"),
    "RAM": (4, "RAM"),
    "ROM": (4, "ROM"),

    # I/O (lib=5)
    "BUTTON": (5, "Button"),
    "LED": (5, "LED"),
    "7-SEGMENT DISPLAY": (5, "7-Segment Display"),
    "HEX DIGIT DISPLAY": (5, "Hex Digit Display"),
}


@dataclass
class CircuitComponent:
    lib: int
    name: str
    x: int
    y: int
    attrs: Dict[str, str] = field(default_factory=dict)
    label: Optional[str] = None
    input_offsets: List[Tuple[int, int]] = field(default_factory=list)
    output_offset: Tuple[int, int] = (0, 0)
    ports: List[Tuple[int, int]] = field(default_factory=list)


@dataclass
class ComponentPort:
    x: int
    y: int
    width: int           # Bit width (1, 2, 4, 8, etc., or 0 for flexible/unknown)
    role: str            # 'in', 'out', 'c_in', 'c_out', 'select', 'clock', 'clear', 'enable', etc.
    name: str = ""       # Terminal label or role name


def get_component_port_specs(comp: CircuitComponent) -> List[ComponentPort]:
    """
    Computes all exact canvas terminal coordinates (px, py), bit widths, and roles
    for a Logisim component based on its library, canonical name, position, and attributes.
    """
    ports: List[ComponentPort] = []
    x, y = comp.x, comp.y
    name = comp.name
    attrs = comp.attrs

    if name == "Pin":
        width = int(attrs.get("width", 1))
        is_output = attrs.get("output", "false").lower() == "true"
        role = "out" if is_output else "in"
        ports.append(ComponentPort(x, y, width, role, attrs.get("label", "pin")))
    elif name == "Comparator":
        # Inputs: IN0 (top-left), IN1 (bottom-left) -> width
        # Outputs: GT (top-right '>'), EQ (middle-right '='), LT (bottom-right '<') -> 1 bit
        data_width = int(attrs.get("width", 8))
        ports.extend([
            ComponentPort(x - 40, y - 10, data_width, "in", "A"),
            ComponentPort(x - 40, y + 10, data_width, "in", "B"),
            ComponentPort(x, y - 10, 1, "out", "GT"),
            ComponentPort(x, y, 1, "out", "EQ"),
            ComponentPort(x, y + 10, 1, "out", "LT"),
        ])
    elif name in ("Adder", "Subtractor", "Multiplier"):
        data_width = int(attrs.get("width", 8))
        ports.extend([
            ComponentPort(x - 40, y - 10, data_width, "in", "A"),
            ComponentPort(x - 40, y + 10, data_width, "in", "B"),
            ComponentPort(x, y, data_width, "out", "Sum"),
            ComponentPort(x - 20, y - 20, 1, "in", "c_in"),
            ComponentPort(x - 20, y + 20, 1, "out", "c_out"),
        ])
    elif name == "Divider":
        data_width = int(attrs.get("width", 8))
        ports.extend([
            ComponentPort(x - 40, y - 10, data_width, "in", "A"),
            ComponentPort(x - 40, y + 10, data_width, "in", "B"),
            ComponentPort(x, y, data_width, "out", "Quotient"),
            ComponentPort(x - 20, y - 20, data_width, "in", "Upper"),
            ComponentPort(x - 20, y + 20, data_width, "out", "Remainder"),
        ])
    elif name in ("Negator", "Bit Extender"):
        data_width = int(attrs.get("width", 8))
        ports.extend([
            ComponentPort(x - 40, y, data_width, "in", "in"),
            ComponentPort(x, y, data_width, "out", "out"),
        ])
    elif name == "Shifter":
        data_width = int(attrs.get("width", 8))
        shift_bits = max(1, (data_width - 1).bit_length())
        ports.extend([
            ComponentPort(x - 40, y - 10, data_width, "in", "in"),
            ComponentPort(x - 40, y + 10, shift_bits, "in", "shift"),
            ComponentPort(x, y, data_width, "out", "out"),
        ])
    elif "Gate" in name or name == "Buffer":
        data_width = int(attrs.get("width", 1))
        inputs = int(attrs.get("inputs", 2))
        size = int(attrs.get("size", 50))
        ports.append(ComponentPort(x, y, data_width, "out", "out"))
        if "NOT" in name:
            ports.append(ComponentPort(x - 30, y, data_width, "in", "in"))
        elif inputs == 2:
            ports.extend([
                ComponentPort(x - size, y - 20, data_width, "in", "in0"),
                ComponentPort(x - size, y + 20, data_width, "in", "in1"),
            ])
        elif inputs == 3:
            ports.extend([
                ComponentPort(x - size, y - 20, data_width, "in", "in0"),
                ComponentPort(x - size, y, data_width, "in", "in1"),
                ComponentPort(x - size, y + 20, data_width, "in", "in2"),
            ])
        elif inputs == 4:
            ports.extend([
                ComponentPort(x - size, y - 20, data_width, "in", "in0"),
                ComponentPort(x - size, y - 10, data_width, "in", "in1"),
                ComponentPort(x - size, y + 10, data_width, "in", "in2"),
                ComponentPort(x - size, y + 20, data_width, "in", "in3"),
            ])
        else:
            for i in range(inputs):
                ports.append(ComponentPort(x - size, y + int((i - (inputs - 1) / 2) * 10), data_width, "in", f"in{i}"))
    elif name == "Register":
        data_width = int(attrs.get("width", 8))
        ports.extend([
            ComponentPort(x, y, data_width, "out", "Q"),
            ComponentPort(x - 30, y, data_width, "in", "D"),
            ComponentPort(x - 20, y + 20, 1, "in", "clock"),
            ComponentPort(x - 10, y + 20, 1, "in", "clear"),
            ComponentPort(x - 30, y + 10, 1, "in", "enable"),
        ])
    elif name == "Counter":
        data_width = int(attrs.get("width", 8))
        ports.extend([
            ComponentPort(x, y, data_width, "out", "Q"),
            ComponentPort(x - 30, y, data_width, "in", "Data"),
            ComponentPort(x - 20, y + 20, 1, "in", "clock"),
            ComponentPort(x - 10, y + 20, 1, "in", "clear"),
            ComponentPort(x - 30, y - 10, 1, "in", "load"),
            ComponentPort(x - 30, y + 10, 1, "in", "count_en"),
            ComponentPort(x, y + 10, 1, "out", "carry"),
        ])
    elif name in ("D Flip-Flop", "T Flip-Flop"):
        ports.extend([
            ComponentPort(x - 40, y, 1, "in", "D"),
            ComponentPort(x - 40, y + 20, 1, "in", "clock"),
            ComponentPort(x, y, 1, "out", "Q"),
            ComponentPort(x, y + 20, 1, "out", "notQ"),
            ComponentPort(x - 20, y + 30, 1, "in", "reset"),
        ])
    elif name == "J-K Flip-Flop":
        ports.extend([
            ComponentPort(x - 40, y, 1, "in", "J"),
            ComponentPort(x - 40, y + 10, 1, "in", "clock"),
            ComponentPort(x - 40, y + 20, 1, "in", "K"),
            ComponentPort(x, y, 1, "out", "Q"),
            ComponentPort(x, y + 20, 1, "out", "notQ"),
            ComponentPort(x - 20, y + 30, 1, "in", "reset"),
        ])
    elif name == "Multiplexer":
        data_width = int(attrs.get("width", 1))
        select_bits = int(attrs.get("select", 1))
        num_inputs = 1 << select_bits
        ports.append(ComponentPort(x, y, data_width, "out", "out"))
        ports.append(ComponentPort(x - 20, y + 20, select_bits, "in", "select"))
        if num_inputs == 2:
            ports.append(ComponentPort(x - 30, y - 10, data_width, "in", "in0"))
            ports.append(ComponentPort(x - 30, y + 10, data_width, "in", "in1"))
        else:
            dy = -(num_inputs // 2) * 10
            for i in range(num_inputs):
                ports.append(ComponentPort(x - 40, y + dy + 10 * i, data_width, "in", f"in{i}"))
    elif name == "Demultiplexer":
        data_width = int(attrs.get("width", 1))
        select_bits = int(attrs.get("select", 1))
        outputs = 1 << select_bits
        ports.append(ComponentPort(x, y, data_width, "in", "in"))
        ports.append(ComponentPort(x + 20, y + 20, select_bits, "in", "select"))
        for i in range(outputs):
            ports.append(ComponentPort(x + 30, y - 10 + i * 20, data_width, "out", f"out{i}"))
    elif name == "Decoder":
        select_bits = int(attrs.get("select", 1))
        outputs = 1 << select_bits
        ports.append(ComponentPort(x, y, select_bits, "in", "select"))
        for i in range(outputs):
            ports.append(ComponentPort(x + 30, y - 10 + i * 20, 1, "out", f"out{i}"))
    elif name == "Priority Encoder":
        select_bits = int(attrs.get("select", 3))
        n = 1 << select_bits
        y_start = y - 5 * n + 10
        for i in range(n):
            ports.append(ComponentPort(x - 40, y_start + 10 * i, 1, "in", f"D{i}"))
        ports.append(ComponentPort(x, y, select_bits, "out", "out"))
        ports.append(ComponentPort(x, y + 10, 1, "out", "GS"))
        ports.append(ComponentPort(x - 20, y_start - 10, 1, "out", "EO"))
        ports.append(ComponentPort(x - 20, y_start + 10 * n, 1, "in", "EI"))
    elif name == "Splitter":
        incoming = int(attrs.get("incoming", attrs.get("width", 2)))
        fanout = int(attrs.get("fanout", 2))
        ports.append(ComponentPort(x, y, incoming, "stem", "stem"))
        for k in range(fanout):
            ports.append(ComponentPort(x + 20, y - (fanout - k) * 10, 0, "arm", f"arm{k}"))
    elif name in ("Constant", "Tunnel"):
        width = int(attrs.get("width", 1))
        ports.append(ComponentPort(x, y, width, "inout", name))
    elif name == "Clock":
        ports.append(ComponentPort(x, y, 1, "out", "CLK"))
    elif name in ("Ground", "Power"):
        ports.append(ComponentPort(x, y, 1, "out", name))
    elif name == "Probe":
        ports.append(ComponentPort(x, y, 0, "in", "Probe"))
    else:
        ports.append(ComponentPort(x, y, 0, "inout", name))

    return ports


def get_component_ports(comp: CircuitComponent) -> List[Tuple[int, int]]:
    """
    Computes all exact canvas terminal coordinates (px, py) for a Logisim component
    based on its library, canonical name, position, and attributes.
    Preserves exact backward compatibility with all callers and test suites.
    """
    if comp.ports:
        return list(comp.ports)
    specs = get_component_port_specs(comp)
    return [(p.x, p.y) for p in specs]


def _normalize_probe_radix(val: Any) -> str:
    """Normalizes any radix input (10, '10', 'dec', etc.) to valid Logisim 2.7.1 RadixOption."""
    raw = str(val).strip().lower()
    if raw in ("10", "10signed", "signed", "dec", "decimal"):
        return "10signed"
    elif raw in ("10unsigned", "unsigned", "uint"):
        return "10unsigned"
    elif raw in ("2", "bin", "binary"):
        return "2"
    elif raw in ("8", "oct", "octal"):
        return "8"
    elif raw in ("16", "hex", "hexadecimal"):
        return "16"
    return str(val).strip()


@dataclass
class Wire:
    from_pos: Tuple[int, int]
    to_pos: Tuple[int, int]



class CircuitBuilder:
    """
    Constructs a Logisim 2.7.1 compatible circuit with full component support:
    - Multi-bit input/output Pins (1 to 32 bits)
    - Splitters & Combiners (any incoming bus width and fanout)
    - Standard & Bitwise Logic Gates (AND, OR, NOT, XOR, etc.)
    - Arithmetic blocks (Adder, Subtractor, Multiplier, Comparator)
    - Plexers (Multiplexer, Demultiplexer, Decoder)
    - Memory units (Register, Counter, Flip-Flops)
    - Probes, Tunnels, Constants, Clocks
    """

    def __init__(self, circuit_name: str = "main"):
        self.circuit_name = circuit_name
        self.components: List[CircuitComponent] = []
        self.wires: List[Wire] = []
        # Maps pin label -> canvas (x, y) coordinate
        self.pin_map: Dict[str, Tuple[int, int]] = {}
        # Stores input pins and output pins metadata
        self.input_pins: Dict[str, Dict] = {}
        self.output_pins: Dict[str, Dict] = {}

    def add_pin(
        self,
        name: str,
        x: int,
        y: int,
        is_output: bool = False,
        width: int = 1,
        facing: str = "east",
        label_loc: Optional[str] = None,
    ) -> Tuple[int, int]:
        """
        Adds an input or output pin (1 to 32 bits wide).
        Returns the terminal coordinate (x, y) where wires connect.
        """
        if label_loc is None:
            label_loc = "west" if not is_output else "east"

        attrs = {
            "tristate": "false",
            "label": name,
            "labelloc": label_loc,
            "width": str(width),
        }

        if is_output:
            attrs["facing"] = facing if facing != "east" else "west"
            attrs["output"] = "true"
            self.output_pins[name] = {"x": x, "y": y, "width": width}
        else:
            attrs["facing"] = facing
            attrs["output"] = "false"
            self.input_pins[name] = {"x": x, "y": y, "width": width}

        comp = CircuitComponent(
            lib=0,
            name="Pin",
            x=x,
            y=y,
            attrs=attrs,
            label=name,
            output_offset=(0, 0),
            ports=[(x, y)],
        )
        self.components.append(comp)
        self.pin_map[name] = (x, y)
        return (x, y)

    def add_splitter(
        self,
        x: int,
        y: int,
        incoming: int = 2,
        fanout: int = 2,
        facing: str = "east",
        appear: str = "left",
        bit_ranges: Optional[List[Tuple[int, int]]] = None,
    ) -> Dict[str, Any]:
        """
        Adds a bit Splitter or Bus Combiner.
        incoming: total width of combined bus (e.g. 32, 16, 8).
        fanout: number of split arms (e.g. 2 for two halves).
        appear: "left" (arms branch up) or "right" (arms branch down).
        bit_ranges: optional list of (start_bit, end_bit) for each arm.
                    e.g. [(0, 15), (16, 31)] for 32-bit into two 16-bit halves.

        Returns:
          'stem': (x, y) - coordinate of combined bus terminal.
          'arms': [(x, y), ...] - coordinates of each split branch terminal.
        """
        attrs: Dict[str, str] = {
            "facing": facing,
            "incoming": str(incoming),
            "fanout": str(fanout),
            "appear": appear,
        }

        # Configure bit mapping for each arm
        if bit_ranges and len(bit_ranges) == fanout:
            for arm_idx, (b_start, b_end) in enumerate(bit_ranges):
                for b in range(b_start, b_end + 1):
                    attrs[f"bit{b}"] = str(arm_idx)
        else:
            # Evenly divide incoming bits across arms
            bits_per_arm = max(1, incoming // fanout)
            for arm_idx in range(fanout):
                start_b = arm_idx * bits_per_arm
                end_b = (arm_idx + 1) * bits_per_arm if arm_idx < fanout - 1 else incoming
                for b in range(start_b, end_b):
                    attrs[f"bit{b}"] = str(arm_idx)

        # Calculate exact arm coordinates
        stem_coord = (x, y)
        arm_coords: List[Tuple[int, int]] = []
        dx = 20 if facing == "east" else -20

        if appear == "left":
            for k in range(fanout):
                arm_y = y - (fanout - k) * 10
                arm_coords.append((x + dx, arm_y))
        else:  # right
            for k in range(fanout):
                arm_y = y + (k + 1) * 10
                arm_coords.append((x + dx, arm_y))

        comp = CircuitComponent(
            lib=0,
            name="Splitter",
            x=x,
            y=y,
            attrs=attrs,
            label=f"Splitter_{incoming}to{fanout}",
            ports=[stem_coord] + arm_coords,
        )
        self.components.append(comp)

        return {
            "stem": stem_coord,
            "arms": arm_coords,
            "component": comp,
        }

    def add_gate(
        self,
        gate_type: str,
        x: int,
        y: int,
        inputs: int = 2,
        size: str = "50",
        width: int = 1,
        facing: str = "east",
        label: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Adds a standard or bitwise logic gate (AND, OR, NOT, NAND, NOR, XOR, XNOR).
        x, y is the output tip coordinate of the gate.
        width: 1 to 32 for bit-parallel gates!
        """
        gate_type_clean = gate_type.upper().strip()
        _, canonical_name = COMPONENT_LIB_MAP.get(gate_type_clean, (1, f"{gate_type_clean} Gate"))

        attrs: Dict[str, str] = {}
        if label:
            attrs["label"] = label
        if width > 1:
            attrs["width"] = str(width)
        if facing != "east":
            attrs["facing"] = facing

        if "NOT" in gate_type_clean or canonical_name == "NOT Gate":
            inputs = 1
            attrs["size"] = "30"
            input_coords = [(x - 30, y)]
        else:
            attrs["inputs"] = str(inputs)
            attrs["size"] = size
            if inputs == 2:
                input_coords = [(x - 50, y - 20), (x - 50, y + 20)]
            elif inputs == 3:
                input_coords = [(x - 50, y - 20), (x - 50, y), (x - 50, y + 20)]
            elif inputs == 4:
                input_coords = [
                    (x - 50, y - 20),
                    (x - 50, y - 10),
                    (x - 50, y + 10),
                    (x - 50, y + 20),
                ]
            else:
                input_coords = [(x - 50, y + int((i - (inputs - 1) / 2) * 10)) for i in range(inputs)]

        comp = CircuitComponent(
            lib=1,
            name=canonical_name,
            x=x,
            y=y,
            attrs=attrs,
            label=label,
            ports=[(x, y)] + input_coords,
        )
        self.components.append(comp)

        return {
            "out": (x, y),
            "inputs": input_coords,
            "component": comp,
        }

    def add_arithmetic(
        self,
        op_type: str,
        x: int,
        y: int,
        width: int = 8,
        label: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Adds an Arithmetic unit (Adder, Subtractor, Multiplier, Divider, Comparator, Negator, Shifter).
        x, y is the main result output terminal (or comparator right edge).
        """
        op_clean = op_type.upper().strip()
        _, canonical_name = COMPONENT_LIB_MAP.get(op_clean, (3, op_clean.title()))

        attrs = {"width": str(width)}
        if label:
            attrs["label"] = label

        comp = CircuitComponent(
            lib=3,
            name=canonical_name,
            x=x,
            y=y,
            attrs=attrs,
            label=label,
        )

        if "COMPARATOR" in op_clean:
            comp.ports = [
                (x - 40, y - 10),  # IN0 (Input A)
                (x - 40, y + 10),  # IN1 (Input B)
                (x, y - 10),       # GT (Greater '>')
                (x, y),            # EQ (Equal '=')
                (x, y + 10),       # LT (Less '<')
            ]
            self.components.append(comp)
            return {
                "in1": (x - 40, y - 10),
                "in2": (x - 40, y + 10),
                "gt": (x, y - 10),
                "eq": (x, y),
                "lt": (x, y + 10),
                "out": (x, y),
                "component": comp,
            }

        if "DIVIDER" in op_clean:
            comp.ports = [
                (x - 40, y - 10),
                (x - 40, y + 10),
                (x, y),
                (x - 20, y - 20),
                (x - 20, y + 20),
            ]
            self.components.append(comp)
            return {
                "in1": (x - 40, y - 10),
                "in2": (x - 40, y + 10),
                "out": (x, y),
                "upper": (x - 20, y - 20),
                "rem": (x - 20, y + 20),
                "component": comp,
            }

        if "NEGATOR" in op_clean:
            comp.ports = [(x - 40, y), (x, y)]
            self.components.append(comp)
            return {
                "in": (x - 40, y),
                "out": (x, y),
                "component": comp,
            }

        if "SHIFTER" in op_clean:
            comp.ports = [(x - 40, y - 10), (x - 40, y + 10), (x, y)]
            self.components.append(comp)
            return {
                "in1": (x - 40, y - 10),
                "in2": (x - 40, y + 10),
                "out": (x, y),
                "component": comp,
            }

        # Adder, Subtractor, Multiplier
        comp.ports = [
            (x - 40, y - 10),
            (x - 40, y + 10),
            (x, y),
            (x - 20, y - 20),
            (x - 20, y + 20),
        ]
        self.components.append(comp)

        return {
            "out": (x, y),
            "in1": (x - 40, y - 10),
            "in2": (x - 40, y + 10),
            "cin": (x - 20, y - 20),
            "cout": (x - 20, y + 20),
            "component": comp,
        }

    def add_mux(
        self,
        x: int,
        y: int,
        select_bits: int = 1,
        width: int = 1,
        label: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Adds a Multiplexer (Plexers library).
        select_bits: 1 for 2:1, 2 for 4:1, 3 for 8:1.
        width: bus width of data inputs and output.
        """
        attrs = {
            "select": str(select_bits),
            "width": str(width),
        }
        if label:
            attrs["label"] = label

        num_inputs = 2 ** select_bits
        input_coords = []
        for i in range(num_inputs):
            in_y = y - 10 + i * 20 if num_inputs == 2 else y - (num_inputs * 10 // 2) + i * 10
            input_coords.append((x - 40, in_y))

        comp = CircuitComponent(
            lib=2,
            name="Multiplexer",
            x=x,
            y=y,
            attrs=attrs,
            label=label,
            ports=[(x, y), (x - 20, y + 20)] + input_coords,
        )
        self.components.append(comp)

        return {
            "out": (x, y),
            "inputs": input_coords,
            "sel": (x - 20, y + 20),
            "component": comp,
        }

    def add_register(
        self,
        x: int,
        y: int,
        width: int = 8,
        label: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Adds an edge-triggered Register (Memory library).
        x, y is output Q.
        """
        attrs = {"width": str(width)}
        if label:
            attrs["label"] = label

        ports = [
            (x, y),             # Q
            (x - 30, y),        # D
            (x - 20, y + 20),   # Clock
            (x - 10, y + 20),   # Clear
            (x - 30, y + 10),   # Enable
        ]
        comp = CircuitComponent(
            lib=4,
            name="Register",
            x=x,
            y=y,
            attrs=attrs,
            label=label,
            ports=ports,
        )
        self.components.append(comp)

        return {
            "q": (x, y),
            "d": (x - 30, y),
            "clock": (x - 20, y + 20),
            "clear": (x - 10, y + 20),
            "enable": (x - 30, y + 10),
            "component": comp,
        }

    def add_probe(
        self,
        x: int,
        y: int,
        radix: Union[int, str] = 16,
        facing: str = "west",
        label: Optional[str] = None,
    ) -> Tuple[int, int]:
        """Adds a Probe display with auto-normalized radix."""
        norm_radix = _normalize_probe_radix(radix)
        attrs = {"radix": norm_radix, "facing": facing}
        if label:
            attrs["label"] = label
        comp = CircuitComponent(lib=0, name="Probe", x=x, y=y, attrs=attrs, label=label, ports=[(x, y)])
        self.components.append(comp)
        return (x, y)

    def add_tunnel(
        self,
        x: int,
        y: int,
        label: str,
        width: int = 1,
        facing: str = "east",
    ) -> Tuple[int, int]:
        """Adds a Tunnel."""
        attrs = {"label": label, "width": str(width), "facing": facing}
        comp = CircuitComponent(lib=0, name="Tunnel", x=x, y=y, attrs=attrs, label=label, ports=[(x, y)])
        self.components.append(comp)
        return (x, y)

    def add_constant(
        self,
        x: int,
        y: int,
        value: str = "0x1",
        width: int = 1,
        facing: str = "east",
    ) -> Tuple[int, int]:
        """Adds a Constant value."""
        attrs = {"value": str(value), "width": str(width), "facing": facing}
        comp = CircuitComponent(lib=0, name="Constant", x=x, y=y, attrs=attrs, label=value, ports=[(x, y)])
        self.components.append(comp)
        return (x, y)

    def add_clock(self, x: int, y: int, label: str = "CLK") -> Tuple[int, int]:
        """Adds a clock source."""
        attrs = {"facing": "east", "label": label, "labelloc": "west"}
        comp = CircuitComponent(lib=0, name="Clock", x=x, y=y, attrs=attrs, label=label, ports=[(x, y)])
        self.components.append(comp)
        self.pin_map[label] = (x, y)
        return (x, y)

    def add_component(
        self,
        name: str,
        x: int,
        y: int,
        lib: Optional[int] = None,
        attrs: Optional[Dict[str, Any]] = None,
        label: Optional[str] = None,
    ) -> CircuitComponent:
        """
        Generic component addition. Automatically resolves library and canonical Logisim name.
        """
        name_clean = name.upper().strip()
        canonical_lib, canonical_name = COMPONENT_LIB_MAP.get(name_clean, (lib if lib is not None else 1, name))

        str_attrs = {str(k): str(v) for k, v in (attrs or {}).items()}
        if canonical_name == "Probe" and "radix" in str_attrs:
            str_attrs["radix"] = _normalize_probe_radix(str_attrs["radix"])
        if label and "label" not in str_attrs:
            str_attrs["label"] = label

        comp = CircuitComponent(
            lib=canonical_lib,
            name=canonical_name,
            x=x,
            y=y,
            attrs=str_attrs,
            label=label,
        )
        comp.ports = get_component_ports(comp)
        self.components.append(comp)
        return comp

    def add_wire(self, p1: Tuple[int, int], p2: Tuple[int, int]):
        """
        Adds orthogonal wires between p1 and p2.
        If p1 and p2 don't share x or y, routes with a right-angle bend.
        """
        x1, y1 = int(p1[0]), int(p1[1])
        x2, y2 = int(p2[0]), int(p2[1])

        if x1 == x2 and y1 == y2:
            return

        if x1 == x2 or y1 == y2:
            self.wires.append(Wire((x1, y1), (x2, y2)))
        else:
            # Manhattan right-angle routing: horizontal then vertical
            mid_x = x2
            mid_y = y1
            self.wires.append(Wire((x1, y1), (mid_x, mid_y)))
            self.wires.append(Wire((mid_x, mid_y), (x2, y2)))

    def sanitize_cross_width_wires(self) -> int:
        """
        Electrical Rules Check (ERC) Cross-Width Sanitizer:
        Analyzes connected electrical nets across the circuit. If any wire net
        bridges terminals of conflicting known bit-widths (e.g. connecting an 8-bit
        data bus/gate to a 2-bit OpCode pin or a 1-bit control port), uses multi-source
        BFS Voronoi partitioning to identify and sever the illegal cross-domain bridge
        wire segment(s).
        Guarantees that no wire net in the final Logisim XML contains incompatible bit widths.
        """
        if not self.wires or not self.components:
            return 0

        def is_point_on_segment(pt: Tuple[int, int], p1: Tuple[int, int], p2: Tuple[int, int]) -> bool:
            px, py = pt
            x1, y1 = p1
            x2, y2 = p2
            if x1 == x2 == px and min(y1, y2) <= py <= max(y1, y2):
                return True
            if y1 == y2 == py and min(x1, x2) <= px <= max(x1, x2):
                return True
            return False

        all_port_specs: List[ComponentPort] = []
        for c in self.components:
            all_port_specs.extend(get_component_port_specs(c))
        port_spec_map: Dict[Tuple[int, int], ComponentPort] = {
            (p.x, p.y): p for p in all_port_specs if p.width > 0
        }

        wires = list(self.wires)
        wire_adj: Dict[int, List[int]] = collections.defaultdict(list)
        for i in range(len(wires)):
            w1 = wires[i]
            for j in range(i + 1, len(wires)):
                w2 = wires[j]
                if (w1.from_pos in (w2.from_pos, w2.to_pos) or
                    w1.to_pos in (w2.from_pos, w2.to_pos) or
                    is_point_on_segment(w1.from_pos, w2.from_pos, w2.to_pos) or
                    is_point_on_segment(w1.to_pos, w2.from_pos, w2.to_pos) or
                    is_point_on_segment(w2.from_pos, w1.from_pos, w1.to_pos) or
                    is_point_on_segment(w2.to_pos, w1.from_pos, w1.to_pos)):
                    wire_adj[i].append(j)
                    wire_adj[j].append(i)

        visited_wires = set()
        total_severed = 0
        reconstructed_wires: List[Wire] = []

        for i in range(len(wires)):
            if i in visited_wires:
                continue
            queue = collections.deque([i])
            visited_wires.add(i)
            current_net_wires = []
            while queue:
                curr = queue.popleft()
                current_net_wires.append(curr)
                for neighbor in wire_adj[curr]:
                    if neighbor not in visited_wires:
                        visited_wires.add(neighbor)
                        queue.append(neighbor)

            # Find all ports touched by this net
            net_ports = []
            for w_idx in current_net_wires:
                w = wires[w_idx]
                for pt in (w.from_pos, w.to_pos):
                    if pt in port_spec_map:
                        net_ports.append((pt, port_spec_map[pt]))
                for pt, ps in port_spec_map.items():
                    if is_point_on_segment(pt, w.from_pos, w.to_pos):
                        net_ports.append((pt, ps))

            width_set = set(ps.width for pt, ps in net_ports)
            if len(width_set) <= 1:
                for w_idx in current_net_wires:
                    reconstructed_wires.append(wires[w_idx])
                continue

            # Multi-width conflict detected on this net!
            logger.warning(f"ERC: Incompatible widths detected on net: {width_set}. Sanitizing cross-width bridge wires.")

            # Collect all vertices in this net
            net_all_pts = set(pt for pt, ps in net_ports)
            for w_idx in current_net_wires:
                w = wires[w_idx]
                net_all_pts.add(w.from_pos)
                net_all_pts.add(w.to_pos)

            # Build point-to-point adjacency for this net
            pt_adj = collections.defaultdict(set)
            for w_idx in current_net_wires:
                w = wires[w_idx]
                p1, p2 = w.from_pos, w.to_pos
                pts_on_w = [pt for pt in net_all_pts if is_point_on_segment(pt, p1, p2)]
                if p1[0] == p2[0]:
                    pts_on_w.sort(key=lambda p: p[1])
                else:
                    pts_on_w.sort(key=lambda p: p[0])
                pts_on_w = list(dict.fromkeys(pts_on_w))
                for k in range(len(pts_on_w) - 1):
                    u, v = pts_on_w[k], pts_on_w[k + 1]
                    if u != v:
                        pt_adj[u].add(v)
                        pt_adj[v].add(u)

            # Multi-source BFS Voronoi domain coloring
            dist = {}
            domain = {}
            bfs_q = collections.deque()

            for pt, ps in net_ports:
                dist[pt] = 0
                domain[pt] = ps.width
                bfs_q.append(pt)

            while bfs_q:
                curr = bfs_q.popleft()
                curr_d = dist[curr]
                curr_dom = domain[curr]
                for nxt in pt_adj[curr]:
                    if nxt not in dist:
                        dist[nxt] = curr_d + 1
                        domain[nxt] = curr_dom
                        bfs_q.append(nxt)

            # Reconstruct net wires, omitting cross-domain segments
            for w_idx in current_net_wires:
                w = wires[w_idx]
                p1, p2 = w.from_pos, w.to_pos
                pts_on_w = [pt for pt in net_all_pts if is_point_on_segment(pt, p1, p2)]
                if p1[0] == p2[0]:
                    pts_on_w.sort(key=lambda p: p[1])
                else:
                    pts_on_w.sort(key=lambda p: p[0])
                pts_on_w = list(dict.fromkeys(pts_on_w))
                if pts_on_w and (pts_on_w[0] != p1 or pts_on_w[-1] != p2):
                    if (p1[0] == p2[0] and p1[1] > p2[1]) or (p1[1] == p2[1] and p1[0] > p2[0]):
                        pts_on_w.reverse()

                for k in range(len(pts_on_w) - 1):
                    u, v = pts_on_w[k], pts_on_w[k + 1]
                    if u == v:
                        continue
                    dom_u = domain.get(u)
                    dom_v = domain.get(v)
                    if dom_u is not None and dom_v is not None and dom_u == dom_v:
                        reconstructed_wires.append(Wire(u, v))
                    else:
                        total_severed += 1
                        logger.info(f"ERC: Severed illegal cross-domain wire segment {u} ({dom_u}-bit) -> {v} ({dom_v}-bit)")

        if total_severed > 0:
            seen_wires = set()
            deduped_wires: List[Wire] = []
            for w in reconstructed_wires:
                key = (min(w.from_pos, w.to_pos), max(w.from_pos, w.to_pos))
                if key not in seen_wires:
                    seen_wires.add(key)
                    deduped_wires.append(w)
            self.wires = deduped_wires
            logger.info(f"ERC Sanitizer: safely pruned {total_severed} cross-width bridge wire segment(s).")

        return total_severed

    def snap_and_bridge_wire_gaps(self, max_snap_distance: int = 40) -> int:
        """
        Deterministic, Width-Aware Wire Gap Snapper & Bridge.
        Inspects the circuit geometry, analyzes electrical netlist bit widths,
        identifies dangling wire endpoints, and safely bridges them ONLY to
        terminals and trunks of strictly compatible bit widths.
        Eliminates both floating/blue wires AND incompatible-width orange errors.
        """
        if not self.wires or not self.components:
            return 0

        # Helper: check if a point lies on a wire segment
        def is_point_on_segment(pt: Tuple[int, int], p1: Tuple[int, int], p2: Tuple[int, int]) -> bool:
            px, py = pt
            x1, y1 = p1
            x2, y2 = p2
            if x1 == x2 == px and min(y1, y2) <= py <= max(y1, y2):
                return True
            if y1 == y2 == py and min(x1, x2) <= px <= max(x1, x2):
                return True
            return False

        # 1. Collect all component port specs with ground-truth bit widths
        all_port_specs: List[ComponentPort] = []
        for c in self.components:
            all_port_specs.extend(get_component_port_specs(c))
        port_spec_map: Dict[Tuple[int, int], ComponentPort] = {
            (p.x, p.y): p for p in all_port_specs
        }
        all_ports = [(p.x, p.y) for p in all_port_specs]
        port_set = set(all_ports)

        # 2. Count wire endpoints
        endpoint_counts: Dict[Tuple[int, int], int] = collections.defaultdict(int)
        for w in self.wires:
            endpoint_counts[w.from_pos] += 1
            endpoint_counts[w.to_pos] += 1

        # 3. Identify unconnected component ports
        unconnected_ports: List[Tuple[int, int]] = []
        for p in all_ports:
            connected = False
            if endpoint_counts[p] > 0:
                connected = True
            else:
                for w in self.wires:
                    if is_point_on_segment(p, w.from_pos, w.to_pos):
                        connected = True
                        break
            if not connected:
                unconnected_ports.append(p)

        if not unconnected_ports:
            return 0

        # 4. Electrical Netlist Analysis: Propagate bit widths across wire nets
        wire_adj: Dict[int, List[int]] = collections.defaultdict(list)
        for i in range(len(self.wires)):
            w1 = self.wires[i]
            for j in range(i + 1, len(self.wires)):
                w2 = self.wires[j]
                if (w1.from_pos in (w2.from_pos, w2.to_pos) or
                    w1.to_pos in (w2.from_pos, w2.to_pos) or
                    is_point_on_segment(w1.from_pos, w2.from_pos, w2.to_pos) or
                    is_point_on_segment(w1.to_pos, w2.from_pos, w2.to_pos) or
                    is_point_on_segment(w2.from_pos, w1.from_pos, w1.to_pos) or
                    is_point_on_segment(w2.to_pos, w1.from_pos, w1.to_pos)):
                    wire_adj[i].append(j)
                    wire_adj[j].append(i)

        wire_net: Dict[int, int] = {}
        net_widths: Dict[int, int] = {}
        visited_wires = set()
        net_idx = 0

        for i in range(len(self.wires)):
            if i in visited_wires:
                continue
            queue = collections.deque([i])
            visited_wires.add(i)
            current_net_wires = []
            while queue:
                curr = queue.popleft()
                current_net_wires.append(curr)
                wire_net[curr] = net_idx
                for neighbor in wire_adj[curr]:
                    if neighbor not in visited_wires:
                        visited_wires.add(neighbor)
                        queue.append(neighbor)

            net_port_widths = set()
            for w_idx in current_net_wires:
                w = self.wires[w_idx]
                for pt in (w.from_pos, w.to_pos):
                    if pt in port_spec_map:
                        pw = port_spec_map[pt].width
                        if pw > 0:
                            net_port_widths.add(pw)
                for pt, ps in port_spec_map.items():
                    if ps.width > 0 and is_point_on_segment(pt, w.from_pos, w.to_pos):
                        net_port_widths.add(ps.width)

            if len(net_port_widths) == 1:
                net_widths[net_idx] = next(iter(net_port_widths))
            elif len(net_port_widths) > 1:
                net_widths[net_idx] = max(net_port_widths)

            net_idx += 1

        def get_point_net_width(pt: Tuple[int, int]) -> int:
            for idx, w in enumerate(self.wires):
                if pt == w.from_pos or pt == w.to_pos or is_point_on_segment(pt, w.from_pos, w.to_pos):
                    n_id = wire_net.get(idx)
                    if n_id is not None and n_id in net_widths:
                        return net_widths[n_id]
            if pt in port_spec_map and port_spec_map[pt].width > 0:
                return port_spec_map[pt].width
            return 0

        # 5. Identify dangling wire endpoints
        dangling_endpoints: List[Tuple[int, int]] = []
        for ep, count in endpoint_counts.items():
            if ep in port_set:
                continue
            if count == 1:
                on_interior = False
                for w in self.wires:
                    if ep != w.from_pos and ep != w.to_pos and is_point_on_segment(ep, w.from_pos, w.to_pos):
                        on_interior = True
                        break
                if not on_interior:
                    dangling_endpoints.append(ep)

        if not dangling_endpoints:
            return 0

        # 6. Evaluate candidate snap pairs with STRICT WIDTH COMPATIBILITY
        candidates = []
        for ep in dangling_endpoints:
            ep_w = get_point_net_width(ep)
            for port in unconnected_ports:
                port_spec = port_spec_map.get(port)
                port_w = port_spec.width if port_spec else 0

                # WIDTH COMPATIBILITY FILTER:
                # Never bridge multi-bit data buses to 1-bit control ports or vice-versa!
                if ep_w > 0 and port_w > 0 and ep_w != port_w:
                    continue

                dx = abs(ep[0] - port[0])
                dy = abs(ep[1] - port[1])
                # Exact collinear horizontal match
                if ep[1] == port[1] and dx <= max_snap_distance:
                    candidates.append((dx, ep, port, 'collinear_h'))
                # Exact collinear vertical match
                elif ep[0] == port[0] and dy <= max_snap_distance:
                    candidates.append((dy, ep, port, 'collinear_v'))
                # Small Manhattan corner match
                elif dx <= 30 and dy <= 30 and (dx + dy) <= max_snap_distance + 10:
                    candidates.append((dx + dy + 15, ep, port, 'manhattan'))

        candidates.sort(key=lambda c: c[0])
        used_ep = set()
        used_ports = set()
        snapped_count = 0

        for score, ep, port, mtype in candidates:
            if ep in used_ep or port in used_ports:
                continue
            used_ep.add(ep)
            used_ports.add(port)
            snapped_count += 1

            extended = False
            if mtype in ('collinear_h', 'collinear_v'):
                for w in self.wires:
                    if w.from_pos == ep:
                        w.from_pos = port
                        extended = True
                        break
                    elif w.to_pos == ep:
                        w.to_pos = port
                        extended = True
                        break
            if not extended:
                self.add_wire(port, ep)

        # 7. Secondary pass: snap remaining dangling endpoints to nearby trunks
        # WITH STRICT WIDTH COMPATIBILITY
        remaining_dangling = [ep for ep in dangling_endpoints if ep not in used_ep]
        for ep in remaining_dangling:
            ep_w = get_point_net_width(ep)
            for w in list(self.wires):
                if w.from_pos == ep or w.to_pos == ep:
                    continue
                trunk_w = get_point_net_width(w.from_pos)

                # WIDTH COMPATIBILITY FILTER:
                # Never bridge control lines into different-width data trunks!
                if ep_w > 0 and trunk_w > 0 and ep_w != trunk_w:
                    continue

                x1, y1 = w.from_pos
                x2, y2 = w.to_pos
                # Vertical trunk: can horizontal wire branch into it?
                if x1 == x2:
                    y_min, y_max = min(y1, y2), max(y1, y2)
                    if y_min <= ep[1] <= y_max and abs(ep[0] - x1) <= max_snap_distance:
                        target = (x1, ep[1])
                        for ow in self.wires:
                            if ow.from_pos == ep:
                                ow.from_pos = target
                                snapped_count += 1
                                break
                            elif ow.to_pos == ep:
                                ow.to_pos = target
                                snapped_count += 1
                                break
                        break
                # Horizontal trunk: can vertical wire branch into it?
                elif y1 == y2:
                    x_min, x_max = min(x1, x2), max(x1, x2)
                    if x_min <= ep[0] <= x_max and abs(ep[1] - y1) <= max_snap_distance:
                        target = (ep[0], y1)
                        for ow in self.wires:
                            if ow.from_pos == ep:
                                ow.from_pos = target
                                snapped_count += 1
                                break
                            elif ow.to_pos == ep:
                                ow.to_pos = target
                                snapped_count += 1
                                break
                        break

        if snapped_count > 0:
            logger.info(f"Width-Aware Wire Snapper: seamlessly bridged {snapped_count} compatible terminal gap(s).")

        return snapped_count

    def to_xml(self) -> str:
        """Generates full, valid Logisim 2.7.1 XML document string."""
        self.sanitize_cross_width_wires()
        self.snap_and_bridge_wire_gaps()
        self.sanitize_cross_width_wires()
        root = ET.Element("project", source="2.7.1", version="1.0")


        # Standard Libraries
        libs = [
            ("#Wiring", "0", [("Pin", {"tristate": "false"})]),
            ("#Gates", "1", []),
            ("#Plexers", "2", []),
            ("#Arithmetic", "3", []),
            ("#Memory", "4", []),
            ("#I/O", "5", []),
            ("#Base", "6", [("Text Tool", {
                "text": "",
                "font": "SansSerif plain 12",
                "halign": "center",
                "valign": "base"
            })]),
        ]

        for desc, name, tools in libs:
            lib_elem = ET.SubElement(root, "lib", desc=desc, name=name)
            for tool_name, tool_attrs in tools:
                tool_elem = ET.SubElement(lib_elem, "tool", name=tool_name)
                for ak, av in tool_attrs.items():
                    ET.SubElement(tool_elem, "a", name=ak, val=av)

        # Main declaration
        ET.SubElement(root, "main", name=self.circuit_name)

        # Options
        opts = ET.SubElement(root, "options")
        ET.SubElement(opts, "a", name="gateUndefined", val="ignore")
        ET.SubElement(opts, "a", name="simlimit", val="1000")
        ET.SubElement(opts, "a", name="simrand", val="0")

        # Toolbar
        tb = ET.SubElement(root, "toolbar")
        ET.SubElement(tb, "tool", lib="6", name="Poke Tool")
        ET.SubElement(tb, "tool", lib="6", name="Edit Tool")
        text_tb = ET.SubElement(tb, "tool", lib="6", name="Text Tool")
        ET.SubElement(text_tb, "a", name="text", val="")
        ET.SubElement(text_tb, "a", name="font", val="SansSerif plain 12")
        ET.SubElement(text_tb, "a", name="halign", val="center")
        ET.SubElement(text_tb, "a", name="valign", val="base")
        ET.SubElement(tb, "sep")
        p_in = ET.SubElement(tb, "tool", lib="0", name="Pin")
        ET.SubElement(p_in, "a", name="tristate", val="false")
        p_out = ET.SubElement(tb, "tool", lib="0", name="Pin")
        ET.SubElement(p_out, "a", name="facing", val="west")
        ET.SubElement(p_out, "a", name="output", val="true")
        ET.SubElement(p_out, "a", name="labelloc", val="east")
        ET.SubElement(tb, "tool", lib="1", name="NOT Gate")
        ET.SubElement(tb, "tool", lib="1", name="AND Gate")
        ET.SubElement(tb, "tool", lib="1", name="OR Gate")

        # Circuit
        circ = ET.SubElement(root, "circuit", name=self.circuit_name)
        ET.SubElement(circ, "a", name="circuit", val=self.circuit_name)
        ET.SubElement(circ, "a", name="clabel", val="")
        ET.SubElement(circ, "a", name="clabelup", val="east")
        ET.SubElement(circ, "a", name="clabelfont", val="SansSerif plain 12")

        # Wires
        for w in self.wires:
            w_elem = ET.SubElement(circ, "wire")
            w_elem.attrib["from"] = f"({w.from_pos[0]},{w.from_pos[1]})"
            w_elem.attrib["to"] = f"({w.to_pos[0]},{w.to_pos[1]})"

        # Components
        for c in self.components:
            comp_elem = ET.SubElement(
                circ,
                "comp",
                lib=str(c.lib),
                loc=f"({c.x},{c.y})",
                name=c.name,
            )
            for ak, av in c.attrs.items():
                ET.SubElement(comp_elem, "a", name=ak, val=str(av))

        # Pretty print with minidom
        from xml.dom import minidom
        rough = ET.tostring(root, encoding="utf-8")
        parsed = minidom.parseString(rough)
        return parsed.toprettyxml(indent="  ")

    def save_file(self, filepath: str):
        """Saves circuit to a .circ file."""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_xml())
