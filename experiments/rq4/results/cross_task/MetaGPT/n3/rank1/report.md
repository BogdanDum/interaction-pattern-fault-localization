# Judge report: trace judge

Config: deepseek-v4-pro, temperature=0, failing traces only.

Metric definitions (per-run):
- **Ranking**: first occurrence of rank-k failure-associated pattern.
- **Random baseline**: one late-2/3 random window per triggered failing run.
- **Verdict**: judge `caused` if highlighted interaction contains the initiating fault.
- **Per-run**: one MAD file per row (Claude/GPT-4o counted separately).
- **Judge window width**: n tokens.

## Coverage
- Task rows: 230 (172 failing-task rows)
- Failing runs: 172
- Triggered runs: 98
- Occurrence-level judge calls: 98
- Run-level units: 98

## Run-level metrics (primary)
- Trigger rate (failing runs): 57.0%
- **Caused | triggered**: 70.4% (69/98)
- **E2E caused** (all failing runs): 40.1% (n=69/172)
- Run caused rate (any-hit): 70.4%
- Not caused rate: 29.6%

## Occurrence-level verdict breakdown
- caused: 69 (70.4%)
- not_caused: 29 (29.6%)

## Example justifications (trace caused)
- trace_id=18: The highlighted window shows PLAN (task specification) → ACT (initial code generation) → VERIFY_FAIL (test case expecting error message). The initiating fault is the ACT step where the code omits exception handling for requests.post, which directly leads to the failure. This fault is within the window.
- trace_id=38: The highlighted window shows PLAN (task specification) → ACT (code generation) → VERIFY_FAIL (test failure). The initiating fault is in the ACT step: the code uses datetime.strptime with '%B' which raises ValueError for invalid month names, but the outer try-except catches it and prints a generic error message, which is insufficient. This mistake directly leads to the subsequent test failures and the run's failure.
- trace_id=47: The highlighted window shows PLAN (user requirement) → ACT (code generation) → VERIFY_FAIL (reviewer critique). The initiating fault is the ACT step where the code assumes sequential parts without handling gaps, which directly leads to the failure. This fault is within the window.
