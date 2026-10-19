# Demonstration (about8 minutes)

1. From a supported Linux x86_64 checkout, run `make doctor`, then `make run`. Open http://127.0.0.1:8000. Use New empty session if a previous session is recovered. Expand Reports/tool versions. Show NO DATA and explain the educational indices and real tool paths.
2. With all four values20 and connectivity enabled, press Run simulation. Await confirmation. Show NORMAL, alarm OFF and accepted1. Move a slider without Apply; confirmed values and accepted count stay fixed.
3. Set V=71 and Apply. Show WATCH and V flag1. Set T=61 and Apply. Show DANGER/alarm ON. Explain strict thresholds and K>=2, not a forecast.
4. Reset, select Window boundary, Append batch. Show accepted11, sample10 in history and completed totals(1,1,1,1,4,1,0); sample11 has current0,p=1,q=1. Return live. Explain sample time versus wall time.
5. Set values20 and Apply for recovery. Disconnect V and Apply; show FAULT, effective flags/alarm zero and diagnostic mask. Reconnect, or Reset and enable fault injection then enter101 for V; normal slider becomes unavailable. Statistics exclude complete fault rows. An all-fault fresh session shows NO VALID DATA.
6. Inspect circuit probes, zoom/pan/reset, download .circ and open MonitorGUI in native Logisim4.1.0 if available. Explain the SVG architecture and actual headless evaluation. Inspect matching assembly Code/source hash, Output/stdout/stderr, Statistics and Comparison. No register stepping is claimed.
7. Scrub history; show Historical label, disabled Apply and full-revision statistics scope. Return live. Reports offers CSV/JSON, native text and printable HTML. Open HTML and print for PDF if desired.
8. Run `make test-web` or `make test-native` to show a reproducible check. For the full browser suite use development servers and http://127.0.0.1:5173/qa.html. Explain measured~1–2s evaluation, serialized Play and batch for long runs. End by Reset and show no stale results return.

If dependencies fail, use doctor/visible error; repair/build and Retry accepted history. Never substitute browser calculations or manually edit RAM during the normal demo. Stop the server with Ctrl+C. Do not start a second backend worker against the same database.
