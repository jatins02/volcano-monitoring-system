# WindowCounters timing

MonitorCore and MonitorGUI now expose clk, reset and sample_enable in addition to the sensor inputs. Their shared WindowCounters instance receives effective flags, K and fault. Every register uses the same ungated rising-edge clock. Reset asynchronously clears all state and has priority over sample-enable; when sample-enable=0 the bank holds, including completed-window outputs.

The seven current fields have widths (4,4,4,4,6,4,4) in V,T,G,A,readings,abnormal_samples,faults order. Position has four bits, completed sequence six, has_completed one. Current and completed counters pack B3/B4; position, sequence and completed flag pack B5 exactly as in spec/protocol.md.

For each field the adder computes C+d. If old position<9, enabled registers store C+d and increment position. If old position=9, the current bank and position store zero while the completed bank stores C+d; sequence increments and has_completed sets. The completed bank's enable is sample_enable AND position=9. This direct sum-to-latch path includes the tenth reading and avoids clearing it before capture. Faults have effective flags/K zero, increment fault count only, and still advance position.

`python3 -B -m scripts.check_counters` drives the actual submitted counter bank. Two 635-tick runs check every observed state against the independent test oracle. They cover nine normal then all-abnormal/fault, boundaries 9/10/11/20/600, a 25-clock disabled interval, explicit reset, and three subsequent normal samples. Curated raw traces and summary checks are in reports/stage4/. `make test-combinational` continues to check the core and GUI's combinational paths with their sampling controls held inactive.
