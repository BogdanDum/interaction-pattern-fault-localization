# Judge report: trace judge

Config: deepseek-v4-pro, temperature=0, failing traces only.

Metric definitions (per-run):
- **Ranking**: first occurrence of rank-k failure-associated pattern.
- **Random baseline**: one late-2/3 random window per triggered failing run.
- **Verdict**: judge `caused` if highlighted interaction contains the initiating fault.
- **Per-run**: one MAD file per row (Claude/GPT-4o counted separately).
- **Judge window width**: n tokens.

## Coverage
- Task rows: 98 (98 failing-task rows)
- Failing runs: 98
- Triggered runs: 98
- Occurrence-level judge calls: 98
- Run-level units: 98

## Run-level metrics (primary)
- Trigger rate (failing runs): 100.0%
- **Caused | triggered**: 16.3% (16/98)
- **E2E caused** (all failing runs): 16.3% (n=16/98)
- Run caused rate (any-hit): 16.3%
- Not caused rate: 83.7%

## Occurrence-level verdict breakdown
- caused: 16 (16.3%)
- not_caused: 82 (83.7%)

## Example justifications (trace caused)
- trace_id=38: The window shows the initial ACT (code generation) that uses datetime.strptime with '%B' which raises ValueError for invalid month names, and the subsequent VERIFY_FAIL (test) that expects an error message but the code's exception handling is insufficient. This ACT is the initiating fault because it introduces the flawed input handling that leads to failure.
- trace_id=89: The highlighted window shows ACT (code generation) followed by VERIFY_FAIL (reviewer critique) and another ACT (test update). The initiating fault is the first ACT at [3], where the code incorrectly uses `psutil.virtual_mem()`, a non-existent function. This mistake is within the window and directly causes the failure.
- trace_id=83: The highlighted window shows ACT (code generation) followed by VERIFY_FAIL (reviewer critique) and then another ACT (incomplete test update) and VERIFY_FAIL (repeated critique). The initiating fault is the first ACT where the code lacks connection error handling, which is the root cause of the failure. This fault falls within the window.
