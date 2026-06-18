# Judge report: trace judge

Config: deepseek-v4-pro, temperature=0, failing traces only.

Metric definitions (per-run):
- **Ranking**: first occurrence of rank-k failure-associated pattern.
- **Random baseline**: one late-2/3 random window per triggered failing run.
- **Verdict**: judge `caused` if highlighted interaction contains the initiating fault.
- **Per-run**: one MAD file per row (Claude/GPT-4o counted separately).
- **Judge window width**: n tokens.

## Coverage
- Task rows: 235 (235 failing-task rows)
- Failing runs: 235
- Triggered runs: 235
- Occurrence-level judge calls: 234
- Run-level units: 234

## Run-level metrics (primary)
- Trigger rate (failing runs): 100.0%
- **Caused | triggered**: 20.9% (49/234)
- **E2E caused** (all failing runs): 20.9% (n=49/235)
- Run caused rate (any-hit): 20.9%
- Not caused rate: 79.1%

## Occurrence-level verdict breakdown
- caused: 49 (20.9%)
- not_caused: 185 (79.1%)

## Example justifications (trace caused)
- trace_id=129: The highlighted window shows a TERMINATE action where the agent outputs code and reasoning that incorrectly interprets the problem, followed by INFORM and PLAN actions that reinforce the flawed interpretation. This window contains the initiating fault because it is where the agent makes the critical mistake of assuming the total rows is just the sum of all rows, which directly leads to the wrong answer.
- trace_id=15: The highlighted window shows a TERMINATE action with an incorrect answer (504) followed by INFORM with correct output and a PLAN to correct, but the initiating fault is the premature TERMINATE at [4] which outputs the wrong answer before the code is run, putting the run on a path to failure.
- trace_id=182: The highlighted window shows TERMINATE → INFORM → PLAN → VERIFY_FAIL, where the assistant outputs the final answer in \boxed{} and then receives a VERIFY_FAIL. The initiating fault is the premature TERMINATE at token 4, which is inside the window, as it ends the run without proper validation.
