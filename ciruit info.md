# Circuit guide: left to right

This describes **MonitorGUI** and its supporting circuits. Expand the named library in the left sidebar to find each component. Select a component to edit its attributes. **Data Bits** means wire width: 1 bit is ON/OFF; 8 bits represent 0–255.

## 1. Main signal path

The four rows are **V** (vibration), **T** (temperature), **G** (gas) and **A** (surface activity). Follow each row to the right.

| Position / component | What it does here | Where to find it / settings |
|---|---|---|
| Far-left **input Pins**, V/T/G/A | Supply numeric sensor values, normally 0–100. | **Wiring → Pin**. Data Bits = **8**, Output? = **No**, Three-state? = **No**. Use the hand-shaped **Poke Tool** to change values. |
| Small **Constants** below the input wires | Supply fixed thresholds: **V=70, T=60, G=65, A=70**.  | **Wiring → Constant**. Data Bits = **8**; set Value to the threshold. |
| First rectangular **Comparators**, marked `>`, `=`, `<` | Compare upper sensor input with lower threshold input. Use **`>`**: above gives 1; equal/below gives 0. Outputs: bV/bT/bG/bA. | **Arithmetic → Comparator**. Data Bits = **8**, Numeric Type = **Unsigned**. |
| D-shaped **AND Gates** after the comparators | Combine each raw flag with VALID: `eV = bV AND VALID`, likewise T/G/A. Invalid readings force all four flags to 0. | **Gates → AND Gate**. Two inputs, Data Bits = **1**. |
| Small round **LEDs** branching from these gates | Show each effective sensor flag. ON means that sensor is abnormal in a valid reading. | **Input/Output → LED** (sometimes labelled **I/O**). |
| Rectangular **Bit Extenders**, labelled `0 ext 1 → 3` | Convert a flag into a three-bit number: `0 → 000`, `1 → 001`. This changes width, not value. | **Wiring → Bit Extender**. Bit Width In = **1**, Out = **3**, Extension Type = **Zero**. |
| Three square **Adders**, marked `+` | Add eV+eT and eG+eA, then their results. **K** counts abnormal sensors: 0–4. | **Arithmetic → Adder**. Data Bits = **3**. Connect carry-in to a **one-bit Constant 0**. |
| Three right-side **Comparators** with Constants | Test **K=0**, **K=1** and **K>1**. The first two use the `=` output; the last uses `>`. Constants: 0, 1, 1. | **Arithmetic → Comparator**, unsigned, **3 bits**; **Wiring → Constant**, **3 bits**. |
| Final **AND Gates** and warning **LEDs** | Gate each test with VALID. **NORMAL:** valid and K=0. **WATCH:** valid and K=1. **DANGER / EMERGENCY:** valid and K≥2. | **Gates → AND Gate**; **Input/Output → LED**. |

Rectangles with comparison signs are **comparators**, not flowchart boxes; **+** identifies adders.

## 2. Lower controls and support block

| Component / label | Purpose and Logisim location |
|---|---|
| **mask Pin** | Four connectivity bits: bit0=V, bit1=T, bit2=G, bit3=A. Set **1111 binary (15 decimal)** for all connected. **Wiring → Pin**, 4 bits. |
| **clk, reset, sample_enable Pins** | One-bit controls: **Wiring → Pin**. With reset=0 and enable=1, clk **0→1** records one reading. Enable=0 holds counters. Reset=1 clears counts; return it to 0 afterward. Warnings need no clock edge. |
| Triangle with a small output circle: **NOT Gate** | Inverts VALID to produce **FAULT**. Its LED turns on for an invalid reading. **Gates → NOT Gate**, 1 bit. |
| Large **MonitorAux** rectangle | Custom subcircuit: checks connectivity and values ≤100, produces VALID/faults, packages outputs and contains WindowCounters. Double-click **MonitorAux** in the project list to inspect it. Create subcircuits through **Project → Add Circuit**; select their names to place instances. |
| Labelled **Tunnels** and wires | Matching names connect signals within one circuit without long wires. **Wiring → Tunnel**; match both Label and Data Bits. Draw wires using the **Edit/Wiring Tool**. |
| Bottom **output Pins**: STATUS, CUR, LAST, META | Display status, current counts, completed counts and window progress. Each contains several packed fields. **Wiring → Pin**, Output? = **Yes**, Data Bits = **32**. |
| Explanatory **Text** | Labels only; no electrical function. **Base → Text Tool**. |

## 3. Inside the counter block

Open **WindowCounters** from the project list. **Splitters** (**Wiring → Splitter**) separate or combine bus fields. **Adders** calculate updated totals. **Comparators** detect the tenth reading. **AND, OR and NOT gates** (**Gates**) implement selection and enables. This design implements its selection logic with gates; it does not contain a separate Multiplexer component.

**Registers** (**Memory → Register**) store current totals, completed totals and window progress. The counters are built from registers and adders, rather than the built-in Counter component. Every ten enabled readings, the completed totals include the tenth reading, then the current totals clear. Fault readings advance the window and fault count, but add no abnormal sensor flags.

**Example:** V=71, T=61, G=20, A=20, mask=1111 → flags 1,1,0,0 → K=2 → DANGER. At V=70, V's threshold flag is still 0.

References: official [Logisim 2.7 library reference](https://www.cburch.com/logisim/docs/2.7/en/html/libs/index.html), [Comparator terminals](https://www.cburch.com/logisim/docs/2.7/en/html/libs/arith/comparator.html) and [Register controls](https://www.cburch.com/logisim/docs/2.7/en/html/libs/mem/register.html). Connections checked against this repository’s circuit sources.
