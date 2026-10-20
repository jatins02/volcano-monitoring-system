"""Small typed XML builder for inspectable native Logisim components.

This generates wiring, never sensor results. All comparisons, additions and state
updates are evaluated by the actual simulator. Explicit port/bit maps avoid GUI
layout defaults changing the automated test interface.
"""

from dataclasses import dataclass
import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class Signal:
    name: str
    width: int


@dataclass(frozen=True)
class CircuitInterface:
    """Declared ports for an existing subcircuit, without a partially built object."""

    name: str
    inputs: list[tuple[str, int]]
    outputs: list[tuple[str, int]]


class Circuit:
    def __init__(
        self,
        project: ET.Element,
        name: str,
        inputs: list[tuple[str, int]],
        *,
        node: ET.Element | None = None,
    ):
        self.node = (
            node if node is not None else ET.SubElement(project, "circuit", name=name)
        )
        ET.SubElement(self.node, "a", name="appearance", val="custom")
        self.name = name
        self.inputs = inputs
        self.outputs: list[tuple[str, int]] = []
        self.pin_locations: list[tuple[str, int, int, bool]] = []
        self.index = 0
        self.serial = 0
        self.signals = {}
        for i, (label, width) in enumerate(inputs):
            signal = Signal(label, width)
            self.pin(100, 100 + i * 40, signal, label, False)
            self.signals[label] = signal

    def component(
        self, lib: str | None, name: str, x: int, y: int, **attributes
    ) -> ET.Element:
        attrs = {"name": name, "loc": f"({x},{y})"}
        if lib is not None:
            attrs["lib"] = lib
        node = ET.SubElement(self.node, "comp", attrs)
        for key, value in attributes.items():
            ET.SubElement(
                node,
                "a",
                name=key,
                val=str(value).lower() if isinstance(value, bool) else str(value),
            )
        return node

    def cell(self) -> tuple[int, int]:
        i = self.index
        self.index += 1
        return 450 + (i // 10) * 350, 100 + (i % 10) * 130

    def fresh(self, width: int, label: str = "net") -> Signal:
        self.serial += 1
        return Signal(f"{label}_{self.serial}", width)

    def net(self, x: int, y: int, signal: Signal) -> None:
        self.component("0", "Tunnel", x, y, width=signal.width, label=signal.name)

    def wire(self, x: int, y: int, tx: int, ty: int) -> None:
        ET.SubElement(self.node, "wire", {"from": f"({x},{y})", "to": f"({tx},{ty})"})

    def constant(self, width: int, value: int, label: str = "constant") -> Signal:
        x, y = self.cell()
        result = self.fresh(width, label)
        self.component("0", "Constant", x, y, width=width, value=hex(value))
        self.net(x, y, result)
        return result

    def pin(self, x: int, y: int, signal: Signal, label: str, output: bool) -> None:
        self.component(
            "0",
            "Pin",
            x,
            y,
            width=signal.width,
            label=label,
            output=output,
            facing="west" if output else "east",
        )
        self.net(x, y, signal)
        self.pin_locations.append((label, x, y, output))

    def finish(
        self,
        outputs: dict[str, Signal],
        *,
        pin_y: int = 100,
        output_positions: list[tuple[int, int]] | None = None,
    ) -> None:
        """Expose ports and bind their symbol contacts to their physical locations."""
        if output_positions is not None and len(output_positions) != len(outputs):
            raise ValueError("each output needs one physical pin position")
        x = 450 + (self.index // 10 + 2) * 350
        for i, (label, signal) in enumerate(outputs.items()):
            px, py = (
                output_positions[i]
                if output_positions is not None
                else (x, pin_y + i * 40)
            )
            self.pin(px, py, signal, label, True)
            self.outputs.append((label, signal.width))
        appear = ET.SubElement(self.node, "appear")
        height = max(len(self.inputs), len(self.outputs)) * 20 + 30
        ET.SubElement(
            appear,
            "rect",
            x="100",
            y="80",
            width="100",
            height=str(height),
            fill="none",
            stroke="#000000",
        )
        for group, output in [(self.inputs, False), (self.outputs, True)]:
            for i, (label, width) in enumerate(group):
                _, px, py, _ = next(
                    p for p in self.pin_locations if p[0] == label and p[3] == output
                )
                ET.SubElement(
                    appear,
                    "circ-port",
                    x="200" if output else "100",
                    y=str(100 + i * 20),
                    dir="out" if output else "in",
                    pin=f"{px},{py}",
                )
        ET.SubElement(appear, "circ-anchor", x="200", y="100", facing="east")

    def instance(
        self, child: "Circuit | CircuitInterface", inputs: dict[str, Signal], label: str
    ) -> dict[str, Signal]:
        x, y = self.cell()
        # A child symbol may be tall; reserve enough cell rows to prevent overlap.
        self.index += (max(len(child.inputs), len(child.outputs)) * 20) // 130
        self.component(None, child.name, x, y, label=label)
        for i, (name, width) in enumerate(child.inputs):
            assert inputs[name].width == width, (child.name, name, width, inputs[name])
            self.net(x - 100, y + i * 20, inputs[name])
        results = {}
        for i, (name, width) in enumerate(child.outputs):
            results[name] = self.fresh(width, label + "_" + name)
            self.net(x, y + i * 20, results[name])
        return results

    def gate(self, kind: str, a: Signal, b: Signal | None = None) -> Signal:
        x, y = self.cell()
        out = self.fresh(a.width, kind)
        if b is None:
            self.component("1", "NOT Gate", x, y, width=a.width, size=30)
            self.net(x - 30, y, a)
        else:
            assert a.width == b.width
            self.component("1", kind + " Gate", x, y, width=a.width, size=30, inputs=2)
            self.net(x - 30, y - 10, a)
            self.net(x - 30, y + 10, b)
        self.net(x, y, out)
        return out

    def compare(self, a: Signal, b: Signal, relation: str = "eq") -> Signal:
        assert a.width == b.width
        x, y = self.cell()
        out = self.fresh(1, relation)
        self.component("3", "Comparator", x, y, width=a.width, mode="unsigned")
        self.net(x - 40, y - 10, a)
        self.net(x - 40, y + 10, b)
        self.net(x, y + {"gt": -10, "eq": 0, "lt": 10}[relation], out)
        return out

    def add(self, a: Signal, b: Signal) -> Signal:
        assert a.width == b.width
        x, y = self.cell()
        out = self.fresh(a.width, "sum")
        self.component("3", "Adder", x, y, width=a.width)
        self.net(x - 40, y - 10, a)
        self.net(x - 40, y + 10, b)
        self.net(x - 20, y - 20, self.constant(1, 0))
        self.net(x, y, out)
        return out

    def join(self, parts: list[Signal]) -> Signal:
        """Concatenate little-bit-order fields with an explicit bit-to-end map."""
        x, y = self.cell()
        width = sum(s.width for s in parts)
        out = self.fresh(width, "packed")
        mapping = {}
        bit = 0
        for i, signal in enumerate(parts):
            for _ in range(signal.width):
                mapping[f"bit{bit}"] = i
                bit += 1
        self.component(
            "0",
            "Splitter",
            x,
            y,
            facing="east",
            incoming=width,
            fanout=len(parts),
            appear="right",
            **mapping,
        )
        self.wire(x - 20, y, x, y)
        self.net(x - 20, y, out)
        for i, signal in enumerate(parts):
            self.wire(x + 20, y + 10 + i * 10, x + 60, y + 10 + i * 10)
            self.net(x + 60, y + 10 + i * 10, signal)
        return out

    def split(self, signal: Signal, widths: list[int]) -> list[Signal]:
        assert sum(widths) == signal.width
        parts = [self.fresh(w, "part") for w in widths]
        joined = self.join(parts)
        # Join and split are electrically identical passive components.
        x, y = self.cell()
        self.net(x, y, signal)
        self.net(x, y, joined)
        return parts

    def extend(self, signal: Signal, width: int) -> Signal:
        assert width >= signal.width
        return (
            signal
            if width == signal.width
            else self.join([signal, self.constant(width - signal.width, 0)])
        )

    def mux(self, select: Signal, zero: Signal, one: Signal) -> Signal:
        # A bit mask built from gates avoids ambiguous mux enable defaults.
        assert select.width == 1 and zero.width == one.width
        mask = self.join([select] * zero.width) if zero.width > 1 else select
        return self.gate(
            "OR",
            self.gate("AND", self.gate("NOT", mask), zero),
            self.gate("AND", mask, one),
        )

    def register(
        self,
        width: int,
        data: Signal,
        clock: Signal,
        reset: Signal,
        enable: Signal,
        name: str,
        falling: bool = False,
    ) -> Signal:
        assert data.width == width
        x, y = self.cell()
        out = Signal(name, width)
        self.component(
            "4",
            "Register",
            x,
            y,
            width=width,
            appearance="classic",
            label=name,
            trigger="falling" if falling else "rising",
        )
        self.net(x - 30, y, data)
        self.net(x - 20, y + 20, clock)
        self.net(x - 10, y + 20, reset)
        self.net(x - 30, y + 10, enable)
        self.net(x, y, out)
        return out
