# Stage11 verification

Eight assignment scenarios passed actual HTTP -> Logisim/native execution and independent expected snapshots/statistics. Each directory contains expected.json, actual result/manifest, input image/binary, stdout/stderr and comparison. Existing failure logs in reports/stage7 document missing dependencies, process failures and deliberate mismatch.

Ten real browser acceptance groups passed; see browser-acceptance.json and screenshots. Native keyboard slider synchronization was separately observed. Scaled desktop iframe previews retain exact CSS viewport dimensions. An additional browser clipboard/download attempt stalled and is not counted as passed.

|Samples|HTTP median ms|HTTP p95 ms|Java median ms|Native median ms|Parse/compare median ms|
|---|---|---|---|---|---|
|1|1140.03|1144.61|931.69|1.41|0.46|
|10|1180.25|1220.70|966.00|1.24|0.85|
|100|1334.48|1356.70|1122.20|1.27|4.92|
|600|2009.12|2025.19|1679.58|4.17|26.26|

Five runs per size; nearest-rank p95 is the maximum of five observations. JVM startup/execution are combined. Backend responsiveness was measured with configuration requests during evaluation; worst observed21.49ms. Java60s/native5s timeouts retain substantial headroom; no60Hz hardware claim. Full-prefix replay remains cumulative O(N²), so batch is preferred for long scenarios. Optional Stage13 is deferred.

Full make check passed after the review, including all89 Python unit tests, ten frontend tests/formatting,43 combinational cases on core and GUI, counter/replay/native checks, real API success/failure/lifecycle workflows, doctor/builds/startup and four original bridge regressions. See full-check.log.
