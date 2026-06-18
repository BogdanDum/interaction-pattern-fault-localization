# Judge report: trace judge

Config: deepseek-v4-pro, temperature=0, failing traces only.

Metric definitions (per-run):
- **Ranking**: first occurrence of rank-k failure-associated pattern.
- **Random baseline**: one late-2/3 random window per triggered failing run.
- **Verdict**: judge `caused` if highlighted interaction contains the initiating fault.
- **Per-run**: one MAD file per row (Claude/GPT-4o counted separately).
- **Judge window width**: n tokens.

## Coverage
- Task rows: 42 (42 failing-task rows)
- Failing runs: 42
- Triggered runs: 42
- Occurrence-level judge calls: 42
- Run-level units: 42

## Run-level metrics (primary)
- Trigger rate (failing runs): 100.0%
- **Caused | triggered**: 0.0% (0/42)
- **E2E caused** (all failing runs): 0.0% (n=0/42)
- Run caused rate (any-hit): 0.0%
- Not caused rate: 100.0%

## Occurrence-level verdict breakdown
- not_caused: 42 (100.0%)
