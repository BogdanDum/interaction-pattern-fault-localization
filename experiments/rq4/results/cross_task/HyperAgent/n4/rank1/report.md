# Judge report: trace judge

Config: deepseek-v4-pro, temperature=0, failing traces only.

Metric definitions (per-run):
- **Ranking**: first occurrence of rank-k failure-associated pattern.
- **Random baseline**: one late-2/3 random window per triggered failing run.
- **Verdict**: judge `caused` if highlighted interaction contains the initiating fault.
- **Per-run**: one MAD file per row (Claude/GPT-4o counted separately).
- **Judge window width**: n tokens.

## Coverage
- Task rows: 30 (14 failing-task rows)
- Failing runs: 14
- Triggered runs: 9
- Occurrence-level judge calls: 9
- Run-level units: 9

## Run-level metrics (primary)
- Trigger rate (failing runs): 64.3%
- **Caused | triggered**: 22.2% (2/9)
- **E2E caused** (all failing runs): 14.3% (n=2/14)
- Run caused rate (any-hit): 22.2%
- Not caused rate: 77.8%

## Occurrence-level verdict breakdown
- caused: 2 (22.2%)
- not_caused: 7 (77.8%)

## Example justifications (trace caused)
- trace_id=11: The highlighted window shows a PLAN → ACT → TERMINATE → ACT sequence where the planner initially plans to investigate the issue, then the navigator acts to locate code, then terminates with a premature conclusion that the bug is already fixed, and finally acts by proposing a wrong solution. The initiating fault is the TERMINATE action at event [3], where the agent incorrectly decides the issue is resolved without verifying the fast-delete path, which is the core of the bug. This faulty decision leads the entire run astray.
- trace_id=10: The highlighted window shows a PLAN → ACT → TERMINATE → ACT sequence where the agent plans to add a _print_sinc method, then executes code to add it, terminates with a summary, and then executes a test. The initiating fault is the addition of the _print_sinc method with the wrong condition (Ne instead of Eq), which occurs within this window. This mistake directly causes the failure because the generated C code for sinc(x) would be incorrect.
