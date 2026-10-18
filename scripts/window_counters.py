"""Native synchronous counters, including the tenth reading before window reset."""

try:
    from .circuit_dsl import Circuit, Signal
except ImportError:
    from circuit_dsl import Circuit, Signal

COUNTERS = [
    ("V", 4),
    ("T", 4),
    ("G", 4),
    ("A", 4),
    ("readings", 6),
    ("abnormal_samples", 4),
    ("faults", 4),
]


def build_window_counters(project):
    c = Circuit(
        project,
        "WindowCounters",
        [
            ("clk", 1),
            ("reset", 1),
            ("sample_enable", 1),
            ("flags", 4),
            ("k", 3),
            ("fault", 1),
        ],
    )
    s = c.signals
    position = Signal("POSITION", 4)
    sequence = Signal("COMPLETED_SEQUENCE", 6)
    boundary = c.compare(position, c.constant(4, 9))
    close_enable = c.gate("AND", boundary, s["sample_enable"])
    deltas = c.split(s["flags"], [1] * 4) + [
        s["k"],
        c.compare(s["k"], c.constant(3, 0), "gt"),
        s["fault"],
    ]
    current = []
    completed = []
    for (name, width), delta in zip(COUNTERS, deltas, strict=True):
        old = Signal("CURRENT_" + name, width)
        updated = c.add(old, c.extend(delta, width))
        # The completed latch sees C+d directly, before current C clears.
        current.append(
            c.register(
                width,
                c.mux(boundary, updated, c.constant(width, 0)),
                s["clk"],
                s["reset"],
                s["sample_enable"],
                old.name,
            )
        )
        completed.append(
            c.register(
                width, updated, s["clk"], s["reset"], close_enable, "COMPLETED_" + name
            )
        )
    c.register(
        4,
        c.mux(boundary, c.add(position, c.constant(4, 1)), c.constant(4, 0)),
        s["clk"],
        s["reset"],
        s["sample_enable"],
        position.name,
    )
    c.register(
        6,
        c.add(sequence, c.constant(6, 1)),
        s["clk"],
        s["reset"],
        close_enable,
        sequence.name,
    )
    has_completed = c.register(
        1, c.constant(1, 1), s["clk"], s["reset"], close_enable, "HAS_COMPLETED"
    )
    c.finish(
        {
            "current_counts": c.join(current + [c.constant(2, 0)]),
            "last_completed": c.join(completed + [c.constant(2, 0)]),
            "window_meta": c.join(
                [position, sequence, has_completed, c.constant(21, 0)]
            ),
        }
    )
    return c
