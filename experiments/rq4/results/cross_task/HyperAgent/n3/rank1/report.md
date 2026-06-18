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
- Occurrence-level judge calls: 8
- Run-level units: 8

## Run-level metrics (primary)
- Trigger rate (failing runs): 64.3%
- **Caused | triggered**: 12.5% (1/8)
- **E2E caused** (all failing runs): 7.1% (n=1/14)
- Run caused rate (any-hit): 12.5%
- Not caused rate: 87.5%

## Occurrence-level verdict breakdown
- caused: 1 (12.5%)
- not_caused: 7 (87.5%)

## Example justifications (trace caused)
- trace_id=10: The highlighted window shows ACT (code_search) → TERMINATE (summary) → ACT (code snippet). The initiating fault is the ACT at event 4, where the agent proposed an incorrect solution using user_functions instead of adding a proper _print_sinc method, which later led to the faulty implementation. This fault falls inside the window.
