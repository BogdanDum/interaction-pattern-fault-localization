# Judge report: trace judge

Config: deepseek-v4-pro, temperature=0, failing traces only.

Metric definitions (per-run):
- **Ranking**: first occurrence of rank-k failure-associated pattern.
- **Random baseline**: one late-2/3 random window per triggered failing run.
- **Verdict**: judge `caused` if highlighted interaction contains the initiating fault.
- **Per-run**: one MAD file per row (Claude/GPT-4o counted separately).
- **Judge window width**: n tokens.

## Coverage
- Task rows: 597 (497 failing-task rows)
- Failing runs: 497
- Triggered runs: 235
- Occurrence-level judge calls: 235
- Run-level units: 235

## Run-level metrics (primary)
- Trigger rate (failing runs): 47.3%
- **Caused | triggered**: 63.4% (149/235)
- **E2E caused** (all failing runs): 30.0% (n=149/497)
- Run caused rate (any-hit): 63.4%
- Not caused rate: 36.6%

## Occurrence-level verdict breakdown
- caused: 149 (63.4%)
- not_caused: 86 (36.6%)

## Example justifications (trace caused)
- trace_id=100: The highlighted window shows REQUEST → PLAN → ACT → INFORM, where the agent plans and executes a calculation that misinterprets the problem (using 20% of original length per day instead of 20% of remaining length). This misinterpretation is the initiating fault that leads to the incorrect final answer.
- trace_id=129: The highlighted window shows REQUEST → PLAN → ACT → INFORM, where the initial PLAN and ACT incorrectly assume that the total rows is simply the sum of red, blue, and yellow rows, without properly interpreting the placement constraint. This faulty reasoning is the initiating fault that leads to the wrong answer.
- trace_id=144: The highlighted window shows REQUEST → PLAN → ACT → INFORM, where the assistant plans and writes code that correctly computes the total as $19, but then in the INFORM step incorrectly states the answer as $18.50. This mistake in the INFORM step is the initiating fault that leads to the failure, as it contradicts the correct computation and causes the run to end with an incorrect answer.
