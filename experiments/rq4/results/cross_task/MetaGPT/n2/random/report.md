# Judge report: trace judge

Config: deepseek-v4-pro, temperature=0, failing traces only.

Metric definitions (per-run):
- **Ranking**: first occurrence of rank-k failure-associated pattern.
- **Random baseline**: one late-2/3 random window per triggered failing run.
- **Verdict**: judge `caused` if highlighted interaction contains the initiating fault.
- **Per-run**: one MAD file per row (Claude/GPT-4o counted separately).
- **Judge window width**: n tokens.

## Coverage
- Task rows: 125 (125 failing-task rows)
- Failing runs: 125
- Triggered runs: 125
- Occurrence-level judge calls: 125
- Run-level units: 125

## Run-level metrics (primary)
- Trigger rate (failing runs): 100.0%
- **Caused | triggered**: 19.2% (24/125)
- **E2E caused** (all failing runs): 19.2% (n=24/125)
- Run caused rate (any-hit): 19.2%
- Not caused rate: 80.8%

## Occurrence-level verdict breakdown
- caused: 24 (19.2%)
- not_caused: 101 (80.8%)

## Example justifications (trace caused)
- trace_id=38: The highlighted window shows ACT (initial code generation) followed by VERIFY_FAIL (test cases that expose the bug). The initiating fault is the code in event [3] that uses datetime.strptime with '%B' without catching the ValueError for invalid month names, which directly leads to the failure.
- trace_id=79: The window shows INFORM (reviewer critique) → ACT (unrelated code) → VERIFY_FAIL (reviewer critique on unrelated code). The initiating fault is the ACT at [5] where the agent generates code for 'add_numbers' instead of addressing the recipe manager test issues, which derails the execution and leads to failure.
- trace_id=89: The highlighted window shows ACT (code generation) followed by VERIFY_FAIL (reviewer critique) and another ACT (test update). The initiating fault is the first ACT at [3], where the code incorrectly uses `psutil.virtual_mem()`. This mistake is inside the window and directly causes the failure.
