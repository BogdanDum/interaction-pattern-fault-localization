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
- Triggered runs: 125
- Occurrence-level judge calls: 111
- Run-level units: 111

## Run-level metrics (primary)
- Trigger rate (failing runs): 72.7%
- **Caused | triggered**: 48.6% (54/111)
- **E2E caused** (all failing runs): 31.4% (n=54/172)
- Run caused rate (any-hit): 48.6%
- Not caused rate: 51.4%

## Occurrence-level verdict breakdown
- caused: 54 (48.6%)
- not_caused: 57 (51.4%)

## Example justifications (trace caused)
- trace_id=38: The highlighted window shows ACT (initial code) followed by VERIFY_FAIL (test for invalid month). The initiating fault is in the ACT: the code uses datetime.strptime with '%B' which raises a ValueError for invalid month names, but the outer try-except catches it and prints a generic error message, which is correct. However, the test expects that output, so the fault is not in the code logic but in the test expectation. The window contains the first occurrence of the failure pattern, and the initiating fault (the test expecting the error message) is within this window.
- trace_id=47: The highlighted window shows ACT (initial code generation) followed by VERIFY_FAIL (test that expects ValueError for invalid file name, but the code does not raise ValueError). The initiating fault is the initial code's failure to handle invalid file names, which is present in the ACT event within the window.
- trace_id=48: The highlighted window shows ACT (initial code generation) followed by VERIFY_FAIL (first test suite with flawed tests). The initiating fault is the initial code's lack of proper error handling and the tests' failure to capture output, which set the path to failure. This fault is contained within the window.
