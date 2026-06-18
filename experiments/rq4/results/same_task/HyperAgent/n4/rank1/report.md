# Judge report: trace judge

Config: deepseek-v4-pro, temperature=0, failing traces only.

Metric definitions (per-run):
- **Ranking**: first occurrence of rank-k failure-associated pattern.
- **Random baseline**: one late-2/3 random window per triggered failing run.
- **Verdict**: judge `caused` if highlighted interaction contains the initiating fault.
- **Per-run**: one MAD file per row (Claude/GPT-4o counted separately).
- **Judge window width**: n tokens.

## Coverage
- Task rows: 186 (71 failing-task rows)
- Failing runs: 71
- Triggered runs: 42
- Occurrence-level judge calls: 42
- Run-level units: 42

## Run-level metrics (primary)
- Trigger rate (failing runs): 59.2%
- **Caused | triggered**: 64.3% (27/42)
- **E2E caused** (all failing runs): 38.0% (n=27/71)
- Run caused rate (any-hit): 64.3%
- Not caused rate: 35.7%

## Occurrence-level verdict breakdown
- caused: 27 (64.3%)
- not_caused: 15 (35.7%)

## Example justifications (trace caused)
- trace_id=1: The highlighted window shows REQUEST → PLAN → ACT → VERIFY_FAIL, where the ACT is the code modification that introduced the buggy fix. This ACT is the initiating fault because it directly caused the test failures, and without it the run would not have failed in this way.
- trace_id=10: The window shows REQUEST → PLAN → ACT → VERIFY_FAIL, where the ACT is the code edit that introduced the buggy fix (removing the unconditional Content-Length header but not handling all cases). This edit is the initiating fault because it directly caused the test failures.
- trace_id=104: The window shows REQUEST → PLAN → ACT → VERIFY_FAIL, where the ACT is the code modification that introduced the faulty fix. This fix is the initiating fault because it incorrectly removed the Content-Length header for all requests without body, which likely broke other functionality, leading to the test failures.
