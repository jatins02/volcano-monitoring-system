"""Full native RAM replay controller; no warning logic is calculated in Python."""

try:
    from .circuit_dsl import Circuit, Signal
except ImportError:
    from circuit_dsl import Circuit, Signal

STATES = [
    "BOOT_RESET",
    "SELECT_MAGIC",
    "CHECK_MAGIC",
    "SELECT_COUNT",
    "LATCH_COUNT",
    "CHECK_COUNT",
    "SELECT_DATA",
    "LATCH_DATA",
    "SELECT_META",
    "LATCH_META",
    "COMMIT",
    "SETTLE",
    "SNAPSHOT",
    "PUBLISH",
    "ADVANCE",
    "DONE",
    "ERROR",
]


def build_replay(project, core):
    c = Circuit(project, "ReplayHarness", [])
    x, y = c.cell()
    c.component("0", "Clock", x, y)
    clock = Signal("MASTER_CLOCK", 1)
    c.net(x, y, clock)
    zero = c.constant(1, 0)
    one = c.constant(1, 1)
    state = Signal("CONTROLLER_STATE", 5)
    phases = [c.compare(state, c.constant(5, i)) for i in range(len(STATES))]
    reset = phases[0]
    index = Signal("ROW_INDEX", 32)
    next_index = c.add(index, c.constant(32, 1))
    c.register(32, next_index, clock, reset, phases[14], index.name)
    count = Signal("SAMPLE_COUNT", 32)
    ram_word = Signal("RAM_WORD", 32)
    bad_magic = c.gate("NOT", c.compare(ram_word, c.constant(32, 0x564D0001)))
    bad_count = c.compare(count, c.constant(32, 600), "gt")
    empty = c.compare(count, c.constant(32, 0))
    _, reserved = c.split(ram_word, [4, 28])
    bad_metadata = c.gate("NOT", c.compare(reserved, c.constant(28, 0)))
    final = c.compare(next_index, count)
    next_states = [c.constant(5, i + 1) for i in range(15)] + [
        c.constant(5, 15),
        c.constant(5, 16),
    ]
    next_states[2] = c.mux(bad_magic, c.constant(5, 3), c.constant(5, 16))
    next_states[5] = c.mux(
        bad_count, c.mux(empty, c.constant(5, 6), c.constant(5, 15)), c.constant(5, 16)
    )
    next_states[9] = c.mux(bad_metadata, c.constant(5, 10), c.constant(5, 16))
    next_states[14] = c.mux(final, c.constant(5, 6), c.constant(5, 15))
    next_state = c.constant(5, 16)
    for phase, target in zip(phases, next_states, strict=True):
        next_state = c.mux(phase, next_state, target)
    # State register's reset is independent of BOOT_RESET; zero is its startup state.
    c.register(5, next_state, clock, zero, one, state.name)
    known = phases[0]
    for phase in phases[1:]:
        known = c.gate("OR", known, phase)
    error_value = c.mux(c.gate("NOT", known), c.constant(4, 0), c.constant(4, 4))
    for phase, bad, code in [
        (phases[2], bad_magic, 1),
        (phases[5], bad_count, 2),
        (phases[9], bad_metadata, 3),
    ]:
        error_value = c.mux(c.gate("AND", phase, bad), error_value, c.constant(4, code))
    error_enable = c.gate(
        "AND", c.compare(next_state, c.constant(5, 16)), c.gate("NOT", phases[16])
    )
    error = c.register(4, error_value, clock, reset, error_enable, "HARNESS_ERROR")

    low_index, _ = c.split(index, [10, 22])
    data_address = c.add(c.join([zero, low_index]), c.constant(11, 2))
    meta_address = c.add(data_address, c.constant(11, 1))
    address = c.constant(11, 0)
    for phase_ids, value in [
        ((3, 4), c.constant(11, 1)),
        ((6, 7), data_address),
        ((8, 9), meta_address),
    ]:
        address = c.mux(
            c.gate("OR", phases[phase_ids[0]], phases[phase_ids[1]]), address, value
        )
    x, y = c.cell()
    c.component(
        "4",
        "RAM",
        x,
        y,
        addrWidth=11,
        dataWidth=32,
        enables="byte",
        databus="bibus",
        asyncread=True,
        clearpin=False,
        appearance="classic",
        label="STIMULUS_RAM",
    )
    c.net(x, y + 10, address)
    c.net(x, y + 50, zero)
    c.net(x, y + 60, one)
    c.net(x, y + 70, zero)
    c.net(x, y + 90, c.constant(32, 0))
    c.net(x + 240, y + 90, ram_word)
    c.register(32, ram_word, clock, reset, phases[4], count.name)
    data = c.register(32, ram_word, clock, reset, phases[7], "SENSOR_WORD")
    metadata = c.register(32, ram_word, clock, reset, phases[9], "METADATA_WORD")
    values = c.split(data, [8] * 4)
    mask, _ = c.split(metadata, [4, 28])
    inputs = {name: values[i] for i, name in enumerate("VTGA")}
    inputs.update(mask=mask, clk=clock, reset=reset, sample_enable=phases[10])
    result = c.instance(core, inputs, "SUBMITTED_MONITOR")
    buses = [
        index,
        data,
        result["status"],
        result["current_counts"],
        result["last_completed"],
        result["window_meta"],
    ]
    outputs = {
        f"B{i}": c.register(32, bus, clock, reset, phases[12], f"SNAPSHOT_B{i}")
        for i, bus in enumerate(buses)
    }
    outputs.update(
        result_valid=phases[13],
        harness_error=error,
        halt=c.gate("OR", phases[15], phases[16]),
    )
    c.finish(outputs)
    return c
