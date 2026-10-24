# Downloadable circuit verification

The accepted presentation was checkpointed locally in `f0dab79` before this repair. The downloadable attachment is named `volcano.circ`; its generated source is `circuit/volcano-demo.circ`. The actual HTTP response exactly matched that source:151242 bytes, SHA-256 `b2404af81dd1fcb1242496ecdd83a8bd031279aa9e2f0eaa60b1bd69be048b01`. See `download.json`.

## Reproduced defects and repair

The installed desktop launcher uses classic Logisim2.7.1. The user's original downloaded bytes matched the old project. Actual native loading rejected missing bounding dimensions on custom appearance ports and anchors, broke contacts and produced incompatible widths. Evolution4.1.0 had tolerated the malformed appearance. Fixed SVG bounds preserve the original intended contact centres. Inputs now explicitly disable three-state startup, and the project supplies the native Poke/Edit toolbar. The lower instrumentation spacing accommodates classic's binary bus display.

The standalone export retains the exact three reachable circuit definitions: MonitorGUI, MonitorAux and WindowCounters. It contains813 components and49 custom ports. The strict native checker, `scripts/java/CheckCircuitImport.java`, loaded all saved components and verified port coordinates/bindings against the XML in both versions. The production backend still evaluates the complete Evolution project. Classic's incompatible RAM port geometry is not claimed to support the backend replay harness.

## Actual execution

`make check` completed successfully; see `full-check.log`. This includes102 Python unit tests, four actual bridge integration tests, frontend checks/build,43 independent combinational fixtures,17 replay scenarios, counter checks,12 native analyser comparisons, malformed-input checks and real HTTP success/failure acceptance.

The following additionally passed against the exact HTTP response, rather than a reconstructed circuit:

```sh
DISPLAY=:97 python3 -B -m scripts.check_download --project runtime/logisim-compat/downloaded-volcano.circ --classic-jar /usr/share/logisim/logisim.jar
python3 -B -m scripts.check_download --project runtime/logisim-compat/downloaded-volcano.circ
```

Each engine passed43 independent threshold/truth/fault fixtures and two635-tick scenarios covering600 commits, tenth-sample abnormal/fault boundaries, disabled-sample hold, reset and restart. See `classic-download.log`, `evolution-download.log` and the corresponding results JSON. The classic check used the installed2.7.1 JAR; Evolution used the pinned4.1.0 JAR. Runtime wrappers and detailed native output remain under ignored `runtime/download-check/`.

## Visual inspection

The computer surface did not expose the laptop's open Logisim. Used the installed classic Logisim JAR in an isolated Xvfb display, exposed only through localhost noVNC in the in-app browser. These screenshots show the actual Java editor, not a recreated circuit:

- `classic-before.jpg`: original custom-appearance import error.
- `classic-broken-wiring.jpg`: original incompatible wiring.
- `classic-normal.jpg`: corrected standalone circuit with mask1111.
- `classic-watch.jpg`: V71 produces WATCH.
- `classic-danger.jpg`: V71/T61 produces DANGER and committed counters update.

Classic ignores Evolution's saved initial/radix attributes: inputs start at0 and display binary. Select the hand tool, set mask1111 and sample_enable1, then edit V/T/G/A. Toggle clk0 to1 to commit counters. Evolution preserves its saved numeric defaults. This startup difference does not alter thresholds or warning rules.

The running API was restarted with its existing settings to serve the repaired attachment. Before/after persisted session/sample/job counts matched, and no jobs were active. The download has Cache-Control:no-store. Re-download and open the fresh file; an already-open older file does not update automatically.
