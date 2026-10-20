# Native circuit import and website label repair

Date: 19 October 2026. Maintenance of the approved circuit presentation; no warning/protocol change.

## Findings and repair

The downloaded `/home/jatins02/Downloads/volcano.circ` matched the workspace's starting file, SHA256 `263cc5caa8c30392b1d6e34c6b5e29d9e63ed23bc79b5b8134985ed36d682831`. It was not a different cached design. The native loader discarded 24 of MonitorGUI's 318 saved components: text was assigned to Wiring instead of Base, and the I/O library descriptor was `#Input/Output` instead of the pinned release's actual `#I/O`. Numerical fixture tests alone had not detected those missing presentation components.

The original drawing also put tunnels directly on component bodies, routed wires through tunnel labels and mixed the main warning path with a large scattered collection of packing/diagnostic cells. The native before render occupied bounds `3287x2306`.

The repaired file uses the correct libraries, spaced and oriented tunnel stubs, explicit main-path wires, real 1-to-3 zero-extending primitives, fixed comparator constants, three-bit adders, VALID gates, per-sensor abnormal/fault LEDs and the warning/fault LEDs. MonitorAux contains validity checking, counter coordination and protocol packing; the main circuit exposes four readable instrumentation buses rather than seventeen sprawling probe columns. The production ReplayHarness still uses MonitorCore. The test-only GUI harness is rebuilt against the GUI's explicit interface and physical output schema.

Website rectangles are now 90 units wide, with single-line labels `0 ext 1→3`, `+ (3 bit)` and `K = 0` / `K = 1` / `K > 1`. Connections were repositioned to match their new boundaries. An expandable explanation describes the components.

## Evidence

- [Native before](native-before.png), rendered from the original download using Logisim's component painters.
- [Native after](native-after.png), rendered from the final submitted circuit using those same painters, with all component imports checked.
- [Website DANGER preview](website-danger.png), rasterized from the React component's actual SVG.
- [Native loader check](native-render.log): all 2,313 components preserved across ten circuits; final bounds `1610x1158`.
- [Original-file rejection](old-loader-rejection.log): the new loader-count check rejects the old file (294/318 GUI components).
- [Hardware checks](hardware-check.log): regeneration/rule integrity, 43 independent cases on both core and GUI, then full actual GUI replays at 11 and 600 samples compared with the independent model.
- [Python checks](unit-check.log): 94 tests, including rejection of both unsupported native library mappings.
- [Frontend checks](web-check.log): TypeScript/Vite build, formatting and 12 individual controller/transport/export/schematic tests.
- [Production replay and smoke](replay-check.log): 17 scenarios, fresh repetition, three malformed inputs and real constant/halt smoke.

The final circuit SHA256 is `324e02eafa4e4c7668d70ba0ae066e71e21324a4bebd73d482508fb884cf6f36`.

## Reproducing native visual QA

`scripts/java/RenderCircuit.java` uses the pinned Logisim loader and native painters; it fails if a circuit's loaded component count differs from its saved XML. The approach follows the project's [native image exporter](https://github.com/logisim-evolution/logisim-evolution/blob/v4.1.0/src/main/java/com/cburch/logisim/gui/main/ExportImage.java). Port positions and zero-extension attributes were checked against the [native BitExtender implementation](https://github.com/logisim-evolution/logisim-evolution/blob/v4.1.0/src/main/java/com/cburch/logisim/std/wiring/BitExtender.java).

The installed runtime has no compiler. For this optional developer check, Eclipse ECJ3.40.0 was downloaded to `/tmp` from the official Maven repository, checked against its published SHA1, and recorded with SHA256 `05cc22a24e7982970f63a405fc6c820bc80b806f27f3c5a6236fc475f8f7152b`. No global install or application dependency was added. With that temporary compiler:

```sh
mkdir -p runtime/native-layout
tools/java/bin/java -jar /tmp/volcano-ecj-3.40.0.jar -21 -cp tools/logisim-evolution-4.1.0-all.jar -d runtime/native-layout scripts/java/RenderCircuit.java
tools/java/bin/java -XX:-UsePerfData -Djava.awt.headless=true -Djava.util.prefs.userRoot=runtime/native-layout/prefs -cp runtime/native-layout:tools/logisim-evolution-4.1.0-all.jar RenderCircuit circuit/volcano.circ MonitorGUI runtime/native-layout/after-final.png 1
```

The renderer's printer view proves native import and drawing; CLI fixture suites separately prove numerical behavior. It does not control or inspect a desktop window. The computer tool exposed no apps or browsers, so the user's existing Logisim window and live browser view were not accessible. No desktop screenshot or live browser pass is claimed. Re-download the file and open MonitorGUI for interactive inspection; the original downloaded copy was preserved.
