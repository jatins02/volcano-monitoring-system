# Demonstration (about 8 minutes)

1. From a supported Linux x86_64 checkout, run `make doctor`, then `make run`. Open http://127.0.0.1:8000. Use Session options > New session if needed. Explain that the four values are simulated sensor readings.
2. Leave all four values at 20 with connectivity enabled. Press Run simulation and await confirmation. Show NORMAL and alarm OFF. Move a slider without pressing Step: the displayed result and reading count stay fixed.
3. Set V=71 and press Step: WATCH. Set T=61 and press Step: DANGER and alarm ON. Each digital input is ON only above its threshold. K counts the abnormal sensors: zero gives NORMAL, one WATCH, two or more DANGER.
4. In the circuit panel, follow the four inputs through the validity gates, adders and comparisons. Zoom or pan as needed. Download .circ to inspect MonitorGUI in native Logisim. The web drawing displays actual returned results.
5. Open the assembly Code tab. Explain the labelled teaching example: validate the inputs, count threshold violations, select a warning. It is display-only; the full `assembly/monitor.s` analyser runs in the background. Output shows that program's selected reading, Statistics its min/max/average, and Comparison the actual tool agreement.
6. Reset, select Window boundary, then Append scenario. Expand 10-reading counts. Inspect reading 10 in History: completed totals are (1,1,1,1,4,1,0). Reading 11 starts the next window. History changes the view only; Return live enables new readings. Statistics always says All N readings, including while viewing an older reading.
7. Disconnect V and press Step: FAULT, alarm OFF. Alternatively Reset, allow fault values and enter V=101. The V slider becomes unavailable until its value is restored. Fault readings are excluded from statistics; an all-fault session shows NO VALID DATA.
8. Downloads offers CSV/JSON, native text and a printable report containing full evidence. Use Session options > Retry after a recoverable failure; it adds no readings. Reset clears the active view. `make test-web` and `make test-native` provide reproducible checks; the development browser suite is http://127.0.0.1:5173/qa.html.

The teaching example is a GNU AT&T assembly function using `assembly/rules.inc`. To check it independently from the repository root: `gcc -c assembly/teaching-example.s -o /tmp/teaching-example.o`. It illustrates warning selection, not the production statistics, protocol or counter implementation.

If tools fail, retain the visible error and repair/build before Retry. Stop the server with Ctrl+C. Do not start a second backend worker against the same database.
