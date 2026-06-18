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
- Triggered runs: 44
- Occurrence-level judge calls: 44
- Run-level units: 44

## Run-level metrics (primary)
- Trigger rate (failing runs): 62.0%
- **Caused | triggered**: 4.5% (2/44)
- **E2E caused** (all failing runs): 2.8% (n=2/71)
- Run caused rate (any-hit): 4.5%
- Not caused rate: 95.5%

## Occurrence-level verdict breakdown
- caused: 2 (4.5%)
- not_caused: 42 (95.5%)

## Example justifications (trace caused)
- trace_id=212: The highlighted window shows VERIFY_FAIL → ACT → VERIFY_FAIL, where the first VERIFY_FAIL is the test failure from the initial patch attempt, the ACT is the editor's code modification, and the second VERIFY_FAIL is the subsequent test failure. The initiating fault is the incorrect edit in the ACT step, which introduced a bug that caused the tests to fail.
- trace_id=252: The highlighted window shows VERIFY_FAIL → ACT → VERIFY_FAIL, where the first VERIFY_FAIL indicates the initial test failure, the ACT is the first attempt to fix the code, and the second VERIFY_FAIL shows the fix was incorrect. This window contains the initiating fault because the first ACT (the patch) introduced a bug (return before pop), which directly caused the subsequent failures.
