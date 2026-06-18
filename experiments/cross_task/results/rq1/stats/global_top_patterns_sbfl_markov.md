# Global top patterns (SBFL vs Markov)

Batch: `2026-05-27T090031`  |  Label: `global`  |  Top-k: 5

## n = 3

| Framework | Lens | Rank | Pattern | Score | Fisher p | Fisher tested? |
|-----------|------|-----:|---------|------:|---------:|:--------------:|
| AG2 | SBFL | 1 | `TERMINATE :: PLAN :: ACT` | 0.732 |  | no |
| AG2 | SBFL | 2 | `PLAN :: ACT :: PROVIDE` | 0.657 |  | no |
| AG2 | SBFL | 3 | `PROVIDE :: PLAN :: TERMINATE` | 0.635 | 0.0008783 | yes |
| AG2 | SBFL | 4 | `TERMINATE :: PROVIDE :: PLAN` | 0.564 |  | no |
| AG2 | SBFL | 5 | `ACT :: PROVIDE :: TERMINATE` | 0.537 | 1.272e-07 | yes |
| AG2 | Markov | 1 | `TERMINATE :: PLAN :: ACT` | 0.062 | — | — |
| AG2 | Markov | 2 | `PLAN :: ACT :: PROVIDE` | 0.024 | — | — |
| AG2 | Markov | 3 | `PROVIDE :: PLAN :: TERMINATE` | 0.153 | — | — |
| AG2 | Markov | 4 | `TERMINATE :: PROVIDE :: PLAN` | 0.122 | — | — |
| AG2 | Markov | 5 | `PROVIDE :: PLAN :: ACT` | 0.000 | — | — |
| **AG2** | **rank-1 overlap** | — | **yes** | SBFL: `TERMINATE :: PLAN :: ACT` / Markov: `TERMINATE :: PLAN :: ACT` | | |

| MetaGPT | SBFL | 1 | `PLAN :: VERIFY_FAIL :: PROVIDE` | 0.846 | 5.547e-25 | yes |
| MetaGPT | SBFL | 2 | `REQUEST :: PLAN :: VERIFY_FAIL` | 0.846 | 5.547e-25 | yes |
| MetaGPT | SBFL | 3 | `ACT :: VERIFY_FAIL :: PROVIDE` | 0.314 |  | no |
| MetaGPT | SBFL | 4 | `PLAN :: ACT :: VERIFY_FAIL` | 0.314 |  | no |
| MetaGPT | SBFL | 5 | `REQUEST :: PLAN :: ACT` | 0.311 |  | no |
| MetaGPT | Markov | 1 | `PLAN :: VERIFY_FAIL :: PROVIDE` | 0.874 | — | — |
| MetaGPT | Markov | 2 | `REQUEST :: PLAN :: VERIFY_FAIL` | 0.874 | — | — |
| MetaGPT | Markov | 3 | `REQUEST :: PLAN :: PROVIDE` | -0.032 | — | — |
| MetaGPT | Markov | 4 | `PLAN :: PROVIDE :: VERIFY_FAIL` | -0.060 | — | — |
| MetaGPT | Markov | 5 | `REQUEST :: PLAN :: ACT` | -0.055 | — | — |
| **MetaGPT** | **rank-1 overlap** | — | **yes** | SBFL: `PLAN :: VERIFY_FAIL :: PROVIDE` / Markov: `PLAN :: VERIFY_FAIL :: PROVIDE` | | |

| ChatDev | SBFL | 1 | `ACT :: TERMINATE :: PROVIDE` | 0.717 |  | no |
| ChatDev | SBFL | 2 | `PROVIDE :: ACT :: TERMINATE` | 0.717 |  | no |
| ChatDev | SBFL | 3 | `VERIFY_PASS :: PLAN :: ACT` | 0.641 |  | no |
| ChatDev | SBFL | 4 | `ACT :: PLAN :: PROVIDE` | 0.511 | 0.09387 | yes |
| ChatDev | SBFL | 5 | `VERIFY_PASS :: PLAN :: PROVIDE` | 0.498 |  | no |
| ChatDev | Markov | 1 | `ACT :: TERMINATE :: PROVIDE` | 0.095 | — | — |
| ChatDev | Markov | 2 | `PROVIDE :: ACT :: TERMINATE` | 0.095 | — | — |
| ChatDev | Markov | 3 | `VERIFY_PASS :: PLAN :: ACT` | 0.022 | — | — |
| ChatDev | Markov | 4 | `ACT :: PLAN :: PROVIDE` | 0.051 | — | — |
| ChatDev | Markov | 5 | `VERIFY_PASS :: PLAN :: PROVIDE` | 0.019 | — | — |
| **ChatDev** | **rank-1 overlap** | — | **yes** | SBFL: `ACT :: TERMINATE :: PROVIDE` / Markov: `ACT :: TERMINATE :: PROVIDE` | | |

| Magentic | SBFL | 1 | `REQUEST :: PLAN :: ACT` | 0.754 |  | no |
| Magentic | SBFL | 2 | `PLAN :: ACT :: TERMINATE` | 0.610 |  | no |
| Magentic | SBFL | 3 | `ACT :: PLAN :: TERMINATE` | 0.513 |  | no |
| Magentic | SBFL | 4 | `PLAN :: ERROR :: PLAN` | 0.470 | 0.04364 | yes |
| Magentic | SBFL | 5 | `ACT :: PLAN :: ERROR` | 0.442 | 0.08639 | yes |
| Magentic | Markov | 1 | `REQUEST :: PLAN :: ACT` | 0.073 | — | — |
| Magentic | Markov | 2 | `PLAN :: ACT :: TERMINATE` | -0.063 | — | — |
| Magentic | Markov | 3 | `ACT :: PLAN :: TERMINATE` | 0.134 | — | — |
| Magentic | Markov | 4 | `PLAN :: ERROR :: PLAN` | -0.110 | — | — |
| Magentic | Markov | 5 | `ACT :: PLAN :: ERROR` | -0.039 | — | — |
| **Magentic** | **rank-1 overlap** | — | **yes** | SBFL: `REQUEST :: PLAN :: ACT` / Markov: `REQUEST :: PLAN :: ACT` | | |

| HyperAgent | SBFL | 1 | `ACT :: TERMINATE :: ACT` | 0.621 | 0.1362 | yes |
| HyperAgent | SBFL | 2 | `ERROR :: PLAN :: ACT` | 0.564 | 0.1498 | yes |
| HyperAgent | SBFL | 3 | `TERMINATE :: ACT :: PLAN` | 0.552 | 0.3576 | yes |
| HyperAgent | SBFL | 4 | `PLAN :: ACT :: VERIFY_FAIL` | 0.546 | 0.059 | yes |
| HyperAgent | SBFL | 5 | `PLAN :: ACT :: ERROR` | 0.436 | 0.2613 | yes |
| HyperAgent | Markov | 1 | `ACT :: TERMINATE :: ACT` | 0.041 | — | — |
| HyperAgent | Markov | 2 | `TERMINATE :: ACT :: PLAN` | 0.028 | — | — |
| HyperAgent | Markov | 3 | `ERROR :: PLAN :: ACT` | 0.313 | — | — |
| HyperAgent | Markov | 4 | `PROVIDE :: PLAN :: ACT` | 0.056 | — | — |
| HyperAgent | Markov | 5 | `PLAN :: ACT :: VERIFY_FAIL` | 0.590 | — | — |
| **HyperAgent** | **rank-1 overlap** | — | **yes** | SBFL: `ACT :: TERMINATE :: ACT` / Markov: `ACT :: TERMINATE :: ACT` | | |

## n = 4

| Framework | Lens | Rank | Pattern | Score | Fisher p | Fisher tested? |
|-----------|------|-----:|---------|------:|---------:|:--------------:|
| AG2 | SBFL | 1 | `TERMINATE :: PLAN :: ACT :: PROVIDE` | 0.635 |  | no |
| AG2 | SBFL | 2 | `TERMINATE :: PROVIDE :: PLAN :: TERMINATE` | 0.556 |  | no |
| AG2 | SBFL | 3 | `PLAN :: ACT :: PROVIDE :: TERMINATE` | 0.535 | 3.863e-08 | yes |
| AG2 | SBFL | 4 | `PROVIDE :: TERMINATE :: PROVIDE :: PLAN` | 0.475 | 1.067e-05 | yes |
| AG2 | SBFL | 5 | `ACT :: PROVIDE :: TERMINATE :: PROVIDE` | 0.475 | 1.067e-05 | yes |
| AG2 | Markov | 1 | `TERMINATE :: PLAN :: ACT :: PROVIDE` | 0.087 | — | — |
| AG2 | Markov | 2 | `TERMINATE :: PROVIDE :: PLAN :: TERMINATE` | 0.200 | — | — |
| AG2 | Markov | 3 | `PLAN :: ACT :: PROVIDE :: TERMINATE` | -0.115 | — | — |
| AG2 | Markov | 4 | `ACT :: PROVIDE :: TERMINATE :: PROVIDE` | -0.181 | — | — |
| AG2 | Markov | 5 | `PROVIDE :: TERMINATE :: PROVIDE :: PLAN` | -0.181 | — | — |
| **AG2** | **rank-1 overlap** | — | **yes** | SBFL: `TERMINATE :: PLAN :: ACT :: PROVIDE` / Markov: `TERMINATE :: PLAN :: ACT :: PROVIDE` | | |

| MetaGPT | SBFL | 1 | `PLAN :: REQUEST :: PLAN :: VERIFY_FAIL` | 0.846 | 5.547e-25 | yes |
| MetaGPT | SBFL | 2 | `REQUEST :: PLAN :: ACT :: VERIFY_FAIL` | 0.314 |  | no |
| MetaGPT | SBFL | 3 | `PLAN :: REQUEST :: PLAN :: ACT` | 0.311 |  | no |
| MetaGPT | SBFL | 4 | `PLAN :: REQUEST :: PLAN :: PROVIDE` | 0.216 |  | no |
| MetaGPT | SBFL | 5 | `REQUEST :: PLAN :: ACT :: PROVIDE` | 0.127 |  | no |
| MetaGPT | Markov | 1 | `PLAN :: REQUEST :: PLAN :: VERIFY_FAIL` | 1.035 | — | — |
| MetaGPT | Markov | 2 | `PLAN :: REQUEST :: PLAN :: PROVIDE` | 0.062 | — | — |
| MetaGPT | Markov | 3 | `PLAN :: REQUEST :: PLAN :: ACT` | 0.017 | — | — |
| MetaGPT | Markov | 4 | `REQUEST :: PLAN :: ACT :: VERIFY_FAIL` | 1.052 | — | — |
| MetaGPT | Markov | 5 | `REQUEST :: PLAN :: ACT :: PROVIDE` | -0.159 | — | — |
| **MetaGPT** | **rank-1 overlap** | — | **yes** | SBFL: `PLAN :: REQUEST :: PLAN :: VERIFY_FAIL` / Markov: `PLAN :: REQUEST :: PLAN :: VERIFY_FAIL` | | |

| ChatDev | SBFL | 1 | `PROVIDE :: ACT :: TERMINATE :: PROVIDE` | 0.717 |  | no |
| ChatDev | SBFL | 2 | `ACT :: PROVIDE :: ACT :: TERMINATE` | 0.703 |  | no |
| ChatDev | SBFL | 3 | `ACT :: VERIFY_PASS :: PLAN :: ACT` | 0.641 |  | no |
| ChatDev | SBFL | 4 | `VERIFY_PASS :: PLAN :: ACT :: PROVIDE` | 0.618 | 0.07154 | yes |
| ChatDev | SBFL | 5 | `PROVIDE :: ACT :: PLAN :: PROVIDE` | 0.511 | 0.09387 | yes |
| ChatDev | Markov | 1 | `PROVIDE :: ACT :: TERMINATE :: PROVIDE` | 0.111 | — | — |
| ChatDev | Markov | 2 | `ACT :: PROVIDE :: ACT :: TERMINATE` | 0.085 | — | — |
| ChatDev | Markov | 3 | `ACT :: VERIFY_PASS :: PLAN :: ACT` | 0.034 | — | — |
| ChatDev | Markov | 4 | `VERIFY_PASS :: PLAN :: ACT :: PROVIDE` | 0.018 | — | — |
| ChatDev | Markov | 5 | `PROVIDE :: ACT :: PLAN :: PROVIDE` | 0.055 | — | — |
| **ChatDev** | **rank-1 overlap** | — | **yes** | SBFL: `PROVIDE :: ACT :: TERMINATE :: PROVIDE` / Markov: `PROVIDE :: ACT :: TERMINATE :: PROVIDE` | | |

| Magentic | SBFL | 1 | `REQUEST :: PLAN :: ACT :: PLAN` | 0.735 |  | no |
| Magentic | SBFL | 2 | `PLAN :: ACT :: PLAN :: ERROR` | 0.447 | 0.03961 | yes |
| Magentic | SBFL | 3 | `PLAN :: ERROR :: PLAN :: ACT` | 0.434 | 0.1013 | yes |
| Magentic | SBFL | 4 | `ERROR :: PLAN :: ACT :: PLAN` | 0.427 |  | no |
| Magentic | SBFL | 5 | `ACT :: PLAN :: ERROR :: PLAN` | 0.425 | 0.06841 | yes |
| Magentic | Markov | 1 | `REQUEST :: PLAN :: ACT :: PLAN` | 0.097 | — | — |
| Magentic | Markov | 2 | `PLAN :: ACT :: PLAN :: ERROR` | -0.021 | — | — |
| Magentic | Markov | 3 | `PLAN :: ERROR :: PLAN :: ACT` | -0.111 | — | — |
| Magentic | Markov | 4 | `ERROR :: PLAN :: ACT :: PLAN` | -0.122 | — | — |
| Magentic | Markov | 5 | `ACT :: PLAN :: ERROR :: PLAN` | -0.114 | — | — |
| **Magentic** | **rank-1 overlap** | — | **yes** | SBFL: `REQUEST :: PLAN :: ACT :: PLAN` / Markov: `REQUEST :: PLAN :: ACT :: PLAN` | | |

| HyperAgent | SBFL | 1 | `PLAN :: ACT :: TERMINATE :: ACT` | 0.621 | 0.1362 | yes |
| HyperAgent | SBFL | 2 | `TERMINATE :: PLAN :: ACT :: PLAN` | 0.583 |  | no |
| HyperAgent | SBFL | 3 | `ACT :: PLAN :: ACT :: PLAN` | 0.538 |  | no |
| HyperAgent | SBFL | 4 | `ACT :: TERMINATE :: ACT :: PLAN` | 0.519 | 0.3745 | yes |
| HyperAgent | SBFL | 5 | `ERROR :: PLAN :: ACT :: VERIFY_FAIL` | 0.478 | 0.1264 | yes |
| HyperAgent | Markov | 1 | `TERMINATE :: PLAN :: ACT :: PLAN` | 0.165 | — | — |
| HyperAgent | Markov | 2 | `ACT :: PLAN :: ACT :: PLAN` | 0.136 | — | — |
| HyperAgent | Markov | 3 | `PLAN :: ACT :: TERMINATE :: ACT` | 0.050 | — | — |
| HyperAgent | Markov | 4 | `ACT :: TERMINATE :: ACT :: PLAN` | 0.038 | — | — |
| HyperAgent | Markov | 5 | `TERMINATE :: ACT :: PLAN :: ACT` | 0.040 | — | — |
| **HyperAgent** | **rank-1 overlap** | — | **no** | SBFL: `PLAN :: ACT :: TERMINATE :: ACT` / Markov: `TERMINATE :: PLAN :: ACT :: PLAN` | | |
