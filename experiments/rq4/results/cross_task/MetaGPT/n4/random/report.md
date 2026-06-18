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
- **Caused | triggered**: 15.3% (15/98)
- **E2E caused** (all failing runs): 15.3% (n=15/98)
- Run caused rate (any-hit): 15.3%
- Not caused rate: 84.7%

## Occurrence-level verdict breakdown
- caused: 15 (15.3%)
- not_caused: 83 (84.7%)

## Example justifications (trace caused)
- trace_id=38: The window shows the initial ACT (code generation) that contains the initiating fault: using datetime.strptime with '%B' which raises ValueError for invalid month names, and the except block only catches ValueError but does not distinguish between invalid month names and other errors, leading to incorrect handling. This fault is the earliest point that sets the run on the path to failure.
- trace_id=89: The highlighted window shows ACT (code generation) followed by VERIFY_FAIL (reviewer critique) and another ACT (test update). The initiating fault is the misspelled function call `psutil.virtual_mem()` in the first ACT, which is inside the window. This error propagates through subsequent steps, leading to failure.
- trace_id=83: The highlighted window shows ACT (code generation) followed by VERIFY_FAIL (reviewer critique) and then another ACT (test update) and VERIFY_FAIL (same critique repeated). The initiating fault is the first ACT where the coder produced a chat client that lacks error handling for connection failures, which is the root cause of the failure. This fault falls inside the window.
