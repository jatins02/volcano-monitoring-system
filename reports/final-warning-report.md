# Final warning report

Actual standalone assembly reports from the independent Stage11 acceptance runs. Current warning and worst-valid report are distinct: a recovered normal sample can retain a DANGER report for the observed session. Fault-only history has NO_VALID_DATA.

|Case|Rows|Current|Last valid|Worst valid|Assembly report|Valid/fault|
|---|---|---|---|---|---|---|
|normal|1|NORMAL|NORMAL|NORMAL|NORMAL|1/0|
|watch|1|WATCH|WATCH|WATCH|WATCH|1/0|
|danger-repeat|2|DANGER|DANGER|DANGER|DANGER|2/0|
|recovery|2|NORMAL|NORMAL|DANGER|DANGER|2/0|
|fault-only|1|FAULT|None|None|NO_VALID_DATA|0/1|
|window-boundary|11|NORMAL|NORMAL|DANGER|DANGER|11/0|
|fault-tenth|10|FAULT|NORMAL|NORMAL|NORMAL|9/1|
|required-statistics|2|NORMAL|NORMAL|NORMAL|NORMAL|2/0|
