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
- Triggered runs: 10
- Occurrence-level judge calls: 9
- Run-level units: 9

## Run-level metrics (primary)
- Trigger rate (failing runs): 71.4%
- **Caused | triggered**: 11.1% (1/9)
- **E2E caused** (all failing runs): 7.1% (n=1/14)
- Run caused rate (any-hit): 11.1%
- Not caused rate: 88.9%

## Occurrence-level verdict breakdown
- caused: 1 (11.1%)
- not_caused: 8 (88.9%)

## Example justifications (trace caused)
- trace_id=10: The highlighted window shows a TERMINATE → ACT sequence where the agent finalizes its analysis and then proposes code options. The initiating fault is the incorrect piecewise definition in the ACT at event [4], which uses Ne(expr.args[0], 0) as the condition for sin(x)/x, whereas the correct condition should be Eq(x, 0) for the 1 case. This mistake directly leads to the failure.
