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
- **Caused | triggered**: 68.4% (67/98)
- **E2E caused** (all failing runs): 39.0% (n=67/172)
- Run caused rate (any-hit): 68.4%
- Not caused rate: 31.6%

## Occurrence-level verdict breakdown
- caused: 67 (68.4%)
- not_caused: 31 (31.6%)

## Example justifications (trace caused)
- trace_id=18: The highlighted window shows REQUEST → PLAN → ACT → VERIFY_FAIL, where the initial code is generated and then tests are written that assume specific error messages from the API. However, the initiating fault is the missing exception handling in the original code (ACT), which is present in the window but the failure is not caused by this window alone; the fault is the lack of exception handling, which is not addressed until later VERIFY_FAIL events outside the window.
- trace_id=38: The highlighted window shows REQUEST → PLAN → ACT → VERIFY_FAIL, where the ACT generates code that uses datetime.strptime with '%B' which raises ValueError for invalid month names, and the VERIFY_FAIL tests this scenario. This code defect is the initiating fault that caused the failure.
- trace_id=47: The highlighted window shows REQUEST → PLAN → ACT → VERIFY_FAIL, where the initial ACT (code generation) produced a flawed implementation that does not handle missing parts in the middle or missing first part. This concrete mistake is the initiating fault that put the execution on the path to failure, as subsequent VERIFY_FAIL and INFORM events stem from this flawed code.
