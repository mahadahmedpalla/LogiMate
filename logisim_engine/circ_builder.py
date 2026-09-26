"""
Logisim 2.7.1 Circuit XML Generator and Component Coordinate Tracker.
Builds valid, clean .circ XML files supporting the full suite of Logisim digital logic components:
Gates, Multi-bit Pins, Splitters, Multiplexers, Adders/Arithmetic, Registers/Memory, Probes, Tunnels, and Clocks.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
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


def get_component_ports(comp: CircuitComponent) -> List[Tuple[int, int]]:
    """
    Computes all exact canvas terminal coordinates (px, py) for a Logisim component
    based on its library, canonical name, position, and attributes.
    """
    if comp.ports:
        return list(comp.ports)

    ports: List[Tuple[int, int]] = []
    x, y = comp.x, comp.y
    name = comp.name
    attrs = comp.attrs

    if name == "Pin":
        ports.append((x, y))
    elif name == "Comparator":
        # Inputs: IN0 (top-left), IN1 (bottom-left)
        # Outputs: GT (top-right '>'), EQ (middle-right '='), LT (bottom-right '<')
        ports.extend([
            (x - 40, y - 10),
            (x - 40, y + 10),
            (x, y - 10),
            (x, y),
            (x, y + 10),
        ])
    elif name in ("Adder", "Subtractor", "Multiplier"):
        ports.extend([
            (x - 40, y - 10),
            (x - 40, y + 10),
            (x, y),
            (x - 20, y - 20),
            (x - 20, y + 20),
        ])
    elif name == "Divider":
        ports.extend([
            (x - 40, y - 10),
            (x - 40, y + 10),
            (x, y),
            (x - 20, y - 20),
            (x - 20, y + 20),
        ])
    elif name == "Negator":
        ports.extend([(x - 40, y), (x, y)])
    elif name == "Shifter":
        ports.extend([(x - 40, y - 10), (x - 40, y + 10), (x, y)])
    elif name == "Bit Extender":
        ports.extend([(x - 40, y), (x, y)])
    elif "Gate" in name or name == "Buffer":
        ports.append((x, y))
        inputs = int(attrs.get("inputs", 2))
        size = int(attrs.get("size", 50))
        if "NOT" in name:
            ports.append((x - 30, y))
        elif inputs == 2:
            ports.extend([(x - size, y - 20), (x - size, y + 20)])
        elif inputs == 3:
            ports.extend([(x - size, y - 20), (x - size, y), (x - size, y + 20)])
        elif inputs == 4:
            ports.extend([
                (x - size, y - 20),
                (x - size, y - 10),
                (x - size, y + 10),
                (x - size, y + 20),
            ])
        else:
            for i in range(inputs):
                ports.append((x - size, y + int((i - (inputs - 1) / 2) * 10)))
    elif name == "Register":
        ports.extend([
            (x, y),             # Q
            (x - 30, y),        # D
            (x - 20, y + 20),   # Clock
            (x - 10, y + 20),   # Clear
            (x - 30, y + 10),   # Enable
        ])
    elif name == "Counter":
        ports.extend([
            (x, y),             # Q
            (x - 30, y),        # Data In
            (x - 20, y + 20),   # Clock
            (x - 10, y + 20),   # Clear
            (x - 30, y - 10),   # Load
            (x - 30, y + 10),   # Count enable
            (x, y + 10),        # Carry
        ])
    elif name in ("D Flip-Flop", "T Flip-Flop"):
        ports.extend([
            (x - 40, y),        # D / T
            (x - 40, y + 20),   # Clock
            (x, y),             # Q
            (x, y + 20),        # ~Q
            (x - 20, y + 30),   # Reset
        ])
    elif name == "J-K Flip-Flop":
        ports.extend([
            (x - 40, y),        # J
            (x - 40, y + 10),   # Clock
            (x - 40, y + 20),   # K
            (x, y),             # Q
            (x, y + 20),        # ~Q
            (x - 20, y + 30),   # Reset
        ])
    elif name == "Multiplexer":
        ports.append((x, y))           # Output
        ports.append((x - 20, y + 20)) # Select
        select_bits = int(attrs.get("select", 1))
        num_inputs = 2 ** select_bits
        for i in range(num_inputs):
            in_y = y - 10 + i * 20 if num_inputs == 2 else y - (num_inputs * 10 // 2) + i * 10
            ports.append((x - 40, in_y))
    elif name == "Demultiplexer":
        ports.append((x, y))           # Input
        ports.append((x + 20, y + 20)) # Select
        ports.extend([(x + 30, y - 10), (x + 30, y + 10)])
    elif name == "Decoder":
        ports.append((x, y))           # Select
        ports.extend([(x + 30, y - 10), (x + 30, y + 10)])
    elif name == "Splitter":
        ports.append((x, y))           # Stem
        fanout = int(attrs.get("fanout", 2))
        for k in range(fanout):
            ports.append((x + 20, y - (fanout - k) * 10))
    elif name in ("Probe", "Tunnel", "Constant", "Clock", "Ground", "Power"):
        ports.append((x, y))
    else:
        ports.append((x, y))

    return ports


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
        radix: int = 16,
        facing: str = "west",
        label: Optional[str] = None,
    ) -> Tuple[int, int]:
        """Adds a Probe display."""
        attrs = {"radix": str(radix), "facing": facing}
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

    def snap_and_bridge_wire_gaps(self, max_snap_distance: int = 40) -> int:
        """
        Deterministic Wire Gap Snapper & Bridge.
        Inspects the circuit geometry, identifies any dangling wire endpoints that stop
        within max_snap_distance of an unconnected component port or wire trunk,
        and seamlessly extends or bridges them. Eliminates floating/blue disconnected wires.
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

        # 1. Collect all component ports
        all_ports: List[Tuple[int, int]] = []
        for c in self.components:
            all_ports.extend(get_component_ports(c))
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

        # 4. Identify dangling wire endpoints (endpoints that touch no port, no other wire, and not on interior)
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

        # 5. Evaluate candidate snap pairs between dangling endpoints and unconnected ports
        candidates = []
        for ep in dangling_endpoints:
            for port in unconnected_ports:
                dx = abs(ep[0] - port[0])
                dy = abs(ep[1] - port[1])
                # Exact collinear horizontal match (e.g. comparator output gap)
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

            # Extend collinear existing wire in-place for cleanest possible single wire
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

        # 6. Secondary pass: snap remaining dangling endpoints to nearby wire trunks (T-junctions)
        remaining_dangling = [ep for ep in dangling_endpoints if ep not in used_ep]
        for ep in remaining_dangling:
            for w in list(self.wires):
                if w.from_pos == ep or w.to_pos == ep:
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
            logger.info(f"Deterministic Wire Snapper: seamlessly bridged {snapped_count} terminal gap(s).")

        return snapped_count

    def to_xml(self) -> str:
        """Generates full, valid Logisim 2.7.1 XML document string."""
        self.snap_and_bridge_wire_gaps()
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
