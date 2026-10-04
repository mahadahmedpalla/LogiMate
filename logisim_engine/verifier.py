"""
Deep Mode Circuit Verifier (read-only static analysis).

Analyzes a finished CircuitBuilder the same way Logisim 2.7.1 connects things:
  - wires connect at shared endpoints, or where an endpoint lies on another wire
  - a component terminal connects to any wire whose endpoint/segment touches it
  - terminals sitting on the exact same point connect directly
  - tunnels with the same label are one net

It never modifies the circuit. It only reports problems, phrased so the AI
can fix them in a single repair pass:
  ERRORS   floating required inputs, undriven output pins, multiple drivers (shorts),
           wires cut by the bit-width sanitizer
  WARNINGS dangling wire ends (with the nearest terminal), unused input pins
"""

import collections
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .circ_builder import CircuitBuilder, ComponentPort, get_component_port_specs

Point = Tuple[int, int]

# Terminals Logisim treats as optional (an unconnected one has a safe default)
OPTIONAL_PORT_NAMES = {"c_in", "clear", "enable", "reset", "load", "count_en", "EI", "Upper"}

# Components whose terminals pass signals through, so source/sink can't be judged
PASS_THROUGH_COMPONENTS = {"Splitter", "Tunnel", "Bit Selector", "Pull Resistor"}


@dataclass
class Terminal:
    comp_index: int
    comp_name: str
    comp_label: str
    port: ComponentPort
    kind: str  # "source" | "sink" | "neutral"

    @property
    def point(self) -> Point:
        return (self.port.x, self.port.y)

    def describe(self) -> str:
        who = f"{self.comp_name} '{self.comp_label}'" if self.comp_label else f"{self.comp_name} #{self.comp_index}"
        return f"{who} terminal {self.port.name} at ({self.port.x},{self.port.y})"


@dataclass
class VerificationReport:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def score(self) -> int:
        """Lower is better. Errors weigh much more than warnings."""
        return len(self.errors) * 10 + len(self.warnings)

    def as_feedback(self, max_items: int = 25) -> str:
        lines: List[str] = []
        for e in self.errors[:max_items]:
            lines.append(f"ERROR: {e}")
        remaining = max(0, max_items - len(lines))
        for w in self.warnings[:remaining]:
            lines.append(f"WARNING: {w}")
        hidden = len(self.errors) + len(self.warnings) - len(lines)
        if hidden > 0:
            lines.append(f"(+{hidden} more similar issues)")
        return "\n".join(lines)

    def summary(self) -> str:
        if not self.errors and not self.warnings:
            return "All checks passed: every input is driven, every output is connected, no shorts."
        parts = []
        if self.errors:
            parts.append(f"{len(self.errors)} error(s)")
        if self.warnings:
            parts.append(f"{len(self.warnings)} warning(s)")
        return ", ".join(parts)


def _classify(comp_name: str, port: ComponentPort) -> str:
    if comp_name in PASS_THROUGH_COMPONENTS:
        return "neutral"
    if comp_name == "Pin":
        # An input pin drives the circuit; an output pin is driven by it
        return "sink" if port.role == "out" else "source"
    if comp_name in ("Clock", "Constant", "Ground", "Power"):
        return "source"
    if comp_name == "Probe":
        return "sink"
    if port.role in ("out", "c_out"):
        return "source"
    if port.role in ("in", "c_in", "select", "clock", "clear", "enable"):
        return "sink"
    return "neutral"


def _on_segment(pt: Point, a: Point, b: Point) -> bool:
    px, py = pt
    (x1, y1), (x2, y2) = a, b
    if x1 == x2 == px and min(y1, y2) <= py <= max(y1, y2):
        return True
    if y1 == y2 == py and min(x1, x2) <= px <= max(x1, x2):
        return True
    return False


class _UnionFind:
    def __init__(self):
        self.parent: Dict[object, object] = {}

    def find(self, a):
        self.parent.setdefault(a, a)
        while self.parent[a] != a:
            self.parent[a] = self.parent[self.parent[a]]
            a = self.parent[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def verify_circuit(builder: CircuitBuilder, severed_wires: int = 0) -> VerificationReport:
    """Runs all static checks on an already-sanitized builder and returns a report."""
    report = VerificationReport()

    # 1. Collect every component terminal
    terminals: List[Terminal] = []
    for idx, comp in enumerate(builder.components):
        label = comp.label or comp.attrs.get("label", "") or ""
        for port in get_component_port_specs(comp):
            terminals.append(Terminal(idx, comp.name, label, port, _classify(comp.name, port)))

    wires = list(builder.wires)
    uf = _UnionFind()

    # 2. Wires touching each other form nets
    for i, w in enumerate(wires):
        uf.find(("w", i))
    for i in range(len(wires)):
        a1, a2 = wires[i].from_pos, wires[i].to_pos
        for j in range(i + 1, len(wires)):
            b1, b2 = wires[j].from_pos, wires[j].to_pos
            if (_on_segment(a1, b1, b2) or _on_segment(a2, b1, b2) or
                    _on_segment(b1, a1, a2) or _on_segment(b2, a1, a2)):
                uf.union(("w", i), ("w", j))

    # 3. Attach terminals to wires / coincident terminals
    point_to_terms: Dict[Point, List[int]] = collections.defaultdict(list)
    for t_idx, t in enumerate(terminals):
        point_to_terms[t.point].append(t_idx)
        uf.find(("t", t_idx))

    touched_points = set()
    for t_idx, t in enumerate(terminals):
        for i, w in enumerate(wires):
            if _on_segment(t.point, w.from_pos, w.to_pos):
                uf.union(("t", t_idx), ("w", i))
                touched_points.add(t.point)

    for pt, idxs in point_to_terms.items():
        for other in idxs[1:]:
            uf.union(("t", idxs[0]), ("t", other))

    # Tunnels with identical labels are electrically the same net
    tunnels_by_label: Dict[str, List[int]] = collections.defaultdict(list)
    for t_idx, t in enumerate(terminals):
        if t.comp_name == "Tunnel" and t.comp_label:
            tunnels_by_label[t.comp_label].append(t_idx)
    for idxs in tunnels_by_label.values():
        for other in idxs[1:]:
            uf.union(("t", idxs[0]), ("t", other))

    # 4. Group terminals per net
    net_terms: Dict[object, List[int]] = collections.defaultdict(list)
    for t_idx in range(len(terminals)):
        net_terms[uf.find(("t", t_idx))].append(t_idx)

    def net_is_judgeable(idxs: List[int]) -> bool:
        return not any(terminals[i].kind == "neutral" for i in idxs)

    for root, idxs in net_terms.items():
        sources = [terminals[i] for i in idxs if terminals[i].kind == "source"]
        sinks = [terminals[i] for i in idxs if terminals[i].kind == "sink"]
        judgeable = net_is_judgeable(idxs)

        # Short circuit: two or more drivers on one net
        if len(sources) >= 2 and judgeable:
            drivers = "; ".join(s.describe() for s in sources[:4])
            report.errors.append(
                f"Short circuit: {len(sources)} outputs drive the same wire net ({drivers}). "
                f"Each net must have exactly one driver."
            )

        if sources or not judgeable:
            continue

        for s in sinks:
            if s.comp_name == "Probe":
                continue
            if s.comp_name == "Pin":
                report.errors.append(
                    f"Output pin '{s.comp_label}' at ({s.port.x},{s.port.y}) is not driven by anything."
                )
            elif s.port.name not in OPTIONAL_PORT_NAMES:
                report.errors.append(f"Floating input: {s.describe()} is not connected to any signal.")

    # 5. Unused input pins
    for t_idx, t in enumerate(terminals):
        if t.comp_name == "Pin" and t.kind == "source":
            net = net_terms[uf.find(("t", t_idx))]
            if len(net) == 1 and t.point not in touched_points:
                report.warnings.append(f"Input pin '{t.comp_label}' at ({t.port.x},{t.port.y}) is not connected to anything.")

    # 6. Dangling wire ends (most common cause of floating inputs: an endpoint a few pixels off)
    all_points = [t.point for t in terminals]
    for i, w in enumerate(wires):
        for end in (w.from_pos, w.to_pos):
            if end in point_to_terms:
                continue
            touches_wire = any(
                j != i and _on_segment(end, wires[j].from_pos, wires[j].to_pos) for j in range(len(wires))
            )
            if touches_wire:
                continue
            nearest = _nearest_terminal(end, terminals)
            hint = f" Nearest terminal: {nearest.describe()}." if nearest else ""
            report.warnings.append(f"Wire end at ({end[0]},{end[1]}) touches nothing.{hint}")

    if severed_wires > 0:
        report.errors.append(
            f"{severed_wires} wire segment(s) had to be cut because they connected terminals of different bit widths. "
            f"Check widths on pins, gates and buses, and use a Splitter where widths change."
        )

    report.stats = {
        "components": len(builder.components),
        "wires": len(wires),
        "nets": len(net_terms),
    }
    return report


def _nearest_terminal(pt: Point, terminals: List[Terminal], max_dist: int = 60) -> Optional[Terminal]:
    best, best_d = None, None
    for t in terminals:
        d = abs(t.point[0] - pt[0]) + abs(t.point[1] - pt[1])
        if d <= max_dist and (best_d is None or d < best_d):
            best, best_d = t, d
    return best
