"""Generate the readable native counterpart of the website warning schematic.

Only real Logisim primitives evaluate the inputs. Explicit main-path wires and
spaced tunnel stubs prevent labels from covering component bodies. Protocol
packing and counter plumbing live in MonitorAux, outside the visible signal path.
"""

import xml.etree.ElementTree as ET

try:
    from .circuit_dsl import Circuit, Signal
except ImportError:
    from circuit_dsl import Circuit, Signal


def build_auxiliary(project: ET.Element, counters: Circuit) -> Circuit:
    """Validate numeric inputs and package the visible circuit's own outputs."""
    aux = Circuit(
        project,
        "MonitorAux",
        [(n, 8) for n in "VTGA"]
        + [("mask", 4)]
        + [("b" + n, 1) for n in "VTGA"]
        + [("e" + n, 1) for n in "VTGA"]
        + [
            ("k", 3),
            ("watch", 1),
            ("danger", 1),
            ("clk", 1),
            ("reset", 1),
            ("sample_enable", 1),
        ],
    )
    s = aux.signals
    ranges = [aux.compare(s[n], aux.constant(8, 100), "gt") for n in "VTGA"]
    range_mask = aux.join(ranges)
    connectivity = aux.split(s["mask"], [1] * 4)
    sensor_faults = [
        aux.gate("OR", ranges[i], aux.gate("NOT", connectivity[i])) for i in range(4)
    ]
    valid = aux.gate(
        "AND",
        aux.compare(range_mask, aux.constant(4, 0)),
        aux.compare(s["mask"], aux.constant(4, 15)),
    )
    fault = aux.gate("NOT", valid)
    flags = aux.join([s["e" + n] for n in "VTGA"])
    code = aux.join(
        [aux.gate("OR", s["watch"], fault), aux.gate("OR", s["danger"], fault)]
    )
    status = aux.join(
        [
            s["mask"],
            valid,
            flags,
            s["k"],
            code,
            s["danger"],
            fault,
            aux.join([s["b" + n] for n in "VTGA"]),
            range_mask,
            aux.constant(8, 0),
        ]
    )
    aux.finish(
        {
            "valid": valid,
            "status": status,
            **aux.instance(
                counters,
                {
                    "clk": s["clk"],
                    "reset": s["reset"],
                    "sample_enable": s["sample_enable"],
                    "flags": flags,
                    "k": s["k"],
                    "fault": fault,
                },
                "WINDOW_BANK",
            ),
            **{n + "_fault": sensor_faults[i] for i, n in enumerate("VTGA")},
        }
    )
    return aux


class Schematic(Circuit):
    """Place native symbols and keep every label away from its component body."""

    def __init__(self, project: ET.Element, inputs: list[tuple[str, int]]) -> None:
        super().__init__(project, "MonitorGUI", [])
        self.inputs = inputs
        self.sources: dict[str, tuple[int, int]] = {}
        for i, (name, width) in enumerate(inputs):
            y = 140 + i * 120 if i < 4 else 650 + (i - 4) * 70
            signal = Signal(name, width)
            self.pin(100, y, signal, name, False)
            self.signals[name] = signal
            self.sources[name] = (100, y)
            if i < 4:
                self.wire(140, y, 140, y - 30)
                self.net(140, y - 30, signal)

    def pin(self, x: int, y: int, signal: Signal, label: str, output: bool) -> None:
        self.component(
            "0",
            "Pin",
            x,
            y,
            width=signal.width,
            label=label,
            output=output,
            # Classic Logisim otherwise starts editable pins at floating X.
            # Evolution additionally honours the explicit initial value below.
            tristate=False,
            facing="west" if output else "east",
            radix="16" if signal.width == 32 else "10unsigned",
            labelfont="SansSerif plain 12",
            initial=hex(
                20
                if label in "VTGA"
                else 15 if label == "mask" else 1 if label == "sample_enable" else 0
            ),
        )
        self.pin_locations.append((label, x, y, output))
        if output:
            self.wire(x - 110, y, x, y)
            self.net(x - 110, y, signal, facing="east")
        elif label not in "VTGA":
            self.wire(x, y, x + 50, y)
            self.net(x + 50, y, signal)

    def net(self, x: int, y: int, signal: Signal, *, facing: str = "west") -> None:
        self.component(
            "0",
            "Tunnel",
            x,
            y,
            width=signal.width,
            label=signal.name,
            labelfont="SansSerif plain 10",
            facing=facing,
        )

    def caption(self, x: int, y: int, text: str) -> None:
        # Text belongs to Base, not Wiring. A wrong library silently loses labels.
        self.component(
            "6",
            "Text",
            x,
            y,
            text=text,
            halign="left",
            valign="base",
            font="SansSerif plain 12",
        )

    def feed(self, signal: Signal, x: int, y: int, bend: int | None = None) -> None:
        if signal.name not in self.sources:
            # VALID enters from below each gate. This keeps its tunnel label
            # away from the neighbouring raw-input wire and its diagnostic tap.
            self.wire(x, y + 40, x, y)
            self.net(x, y + 40, signal, facing="north")
            return
        sx, sy = self.sources[signal.name]
        if sy == y:
            self.wire(sx, sy, x, y)
        else:
            mid = bend if bend is not None else x - 30
            self.wire(sx, sy, mid, sy)
            self.wire(mid, sy, mid, y)
            self.wire(mid, y, x, y)

    def tap(self, x: int, y: int, signal: Signal) -> None:
        """Branch a short labelled tunnel off a wire, clear of the actual symbol."""
        self.wire(x, y, x, y + 50)
        self.net(x, y + 30, signal)

    def comparator(
        self, x: int, y: int, a: Signal, b: Signal, name: str, relation: str = "gt"
    ) -> Signal:
        self.component("3", "Comparator", x, y, width=a.width, mode="unsigned")
        self.feed(a, x - 40, y - 10, bend=x - 110)
        self.feed(b, x - 40, y + 10)
        out = Signal(name, 1)
        self.sources[name] = (x, y - 10 if relation == "gt" else y)
        return out

    def conjunction(self, x: int, y: int, a: Signal, b: Signal, name: str) -> Signal:
        self.component("1", "AND Gate", x, y, width=1, size=30, inputs=2)
        self.feed(a, x - 30, y - 10)
        self.feed(b, x - 30, y + 10)
        self.sources[name] = (x, y)
        return Signal(name, 1)

    def adder(self, x: int, y: int, a: Signal, b: Signal, name: str) -> Signal:
        self.component("3", "Adder", x, y, width=3)
        self.feed(a, x - 40, y - 10, bend=x - 110)
        self.feed(b, x - 40, y + 10)
        self.component(
            "0", "Constant", x - 20, y - 40, width=1, value="0x0", facing="south"
        )
        self.wire(x - 20, y - 40, x - 20, y - 20)
        self.sources[name] = (x, y)
        return Signal(name, 3)

    def finish(self, outputs: dict[str, Signal], *, pin_y: int = 1160) -> None:
        # Keep protocol outputs along a single instrumentation row; the normal
        # path above remains the same comparator/adder circuit as the website.
        super().finish(
            outputs,
            output_positions=[(340 + i * 350, pin_y) for i in range(len(outputs))],
        )


def build_monitor_gui(
    project: ET.Element, inputs: list[tuple[str, int]], counters: Circuit, rules: dict
) -> Circuit:
    aux = build_auxiliary(project, counters)
    gui = Schematic(project, inputs)
    s = gui.signals
    gui.caption(
        60,
        45,
        "VOLCANO MONITOR - numeric thresholds followed by the website digital warning circuit",
    )
    gui.caption(
        60,
        75,
        "Unsigned sensor values 0..100. Strict > comparison: equality leaves the digital input OFF.",
    )
    gui.caption(
        60, 95,
        "Manual setup: mask=15 connects all sensors; sample_enable=1 enables clocked sampling.",
    )
    raw, flags, extended = [], [], []
    valid = Signal("VALID", 1)
    for i, name in enumerate("VTGA"):
        y = 150 + i * 120
        threshold = Signal("THRESHOLD_" + name, 8)
        gui.component(
            "0",
            "Constant",
            190,
            y + 10,
            width=8,
            value=hex(rules["sensors"][name]["threshold"]),
            label=name + " threshold",
        )
        gui.sources[threshold.name] = (190, y + 10)
        bit = gui.comparator(300, y, s[name], threshold, "b" + name)
        raw.append(bit)
        gui.caption(
            205, y + 40, "Threshold " + str(rules["sensors"][name]["threshold"])
        )
        gui.caption(
            320,
            y - 40,
            name + " > " + str(rules["sensors"][name]["threshold"]) + " -> b" + name,
        )
        flag = gui.conjunction(460, y - 10, bit, valid, "e" + name)
        flags.append(flag)
        gui.tap(350, y - 10, bit)
        gui.tap(490, y - 10, flag)
        gui.wire(520, y - 10, 520, y + 50)
        gui.component("5", "LED", 520, y + 50)
        gui.caption(540, y + 55, name + " flag")
        gui.component(
            "0", "Bit Extender", 600, y - 10, in_width=1, out_width=3, type="zero"
        )
        gui.feed(flag, 560, y - 10)
        ext = Signal("x" + name, 3)
        gui.sources[ext.name] = (600, y - 10)
        extended.append(ext)
        gui.caption(540, y - 40, "0 ext 1 -> 3")
    pair0 = gui.adder(780, 200, extended[0], extended[1], "V_PLUS_T")
    pair1 = gui.adder(780, 440, extended[2], extended[3], "G_PLUS_A")
    k = gui.adder(980, 320, pair0, pair1, "K")
    gui.caption(745, 240, "V + T")
    gui.caption(745, 480, "G + A")
    gui.caption(945, 410, "K = eV + eT + eG + eA")
    gui.tap(1000, 320, k)
    lamps = {}
    for i, (name, value, relation) in enumerate(
        [("normal", 0, "eq"), ("watch", 1, "eq"), ("danger", 1, "gt")]
    ):
        y = 140 + i * 180
        test_y = y + (10 if relation == "gt" else 0)
        constant = Signal("TEST_" + name, 3)
        gui.component("0", "Constant", 1090, test_y + 10, width=3, value=hex(value))
        gui.sources[constant.name] = (1090, test_y + 10)
        condition = gui.comparator(1160, test_y, k, constant, "K_" + name, relation)
        lamps[name] = gui.conjunction(1300, y, condition, valid, name.upper())
        gui.wire(1300, y, 1380, y)
        gui.component("5", "LED", 1380, y)
        gui.caption(
            1400, y + 5, name.upper() + (" / EMERGENCY" if name == "danger" else "")
        )
        gui.caption(1120, y - 40, "K > 1" if name == "danger" else "K = " + str(value))
        if name != "normal":
            gui.tap(1330, y, lamps[name])
    gui.caption(
        60,
        590,
        "NORMAL: K=0   WATCH: K=1   DANGER / emergency: K>=2. Invalid rows force eV,eT,eG,eA to 0.",
    )
    gui.caption(
        60,
        620,
        "Sampling controls and validity/counter interface (same 10-sample window policy as the website)",
    )
    gui.component("1", "NOT Gate", 460, 650, width=1, size=30)
    gui.feed(valid, 430, 650)
    gui.wire(460, 650, 520, 650)
    gui.component("5", "LED", 520, 650)
    gui.caption(540, 655, "FAULT = NOT VALID")
    gui.caption(60, 950, "Set mask=15 for all four sensors connected.")
    gui.caption(
        60, 975, "Pulse reset, then clk with sample_enable=1 to commit a reading."
    )
    # Support ports use spaced stubs rather than tunnels on the symbol itself.
    ax, ay = 1100, 690
    gui.component(
        None, aux.name, ax, ay, label="Validity, counters and protocol packing"
    )
    connections = {
        **s,
        **{"b" + n: raw[i] for i, n in enumerate("VTGA")},
        **{"e" + n: flags[i] for i, n in enumerate("VTGA")},
        "k": k,
        "watch": lamps["watch"],
        "danger": lamps["danger"],
    }
    for i, (name, _) in enumerate(aux.inputs):
        x, y = ax - 100, ay + i * 20
        gui.wire(x - 150, y, x, y)
        gui.net(x - 150, y, connections[name], facing="east")
    outputs = {}
    gui.caption(1320, 765, "Sensor faults")
    for i, (name, width) in enumerate(aux.outputs):
        x, y = ax, ay + i * 20
        if name.endswith("_fault"):
            gui.wire(x, y, 1320, y)
            gui.component("5", "LED", 1320, y)
            gui.caption(1340, y + 5, name[0] + " fault")
            continue
        value = Signal(
            {
                "valid": "VALID",
                "status": "STATUS",
                "current_counts": "CUR",
                "last_completed": "LAST",
                "window_meta": "META",
            }[name],
            width,
        )
        x, y = ax, ay + i * 20
        gui.wire(x, y, x + 50, y)
        gui.net(x + 50, y, value)
        if name != "valid":
            outputs[name] = value
    gui.caption(
        60,
        1060,
        "Instrument outputs for verification: B2 status, B3 current counters, B4 completed counters, B5 window metadata",
    )
    gui.finish(outputs)
    return gui
