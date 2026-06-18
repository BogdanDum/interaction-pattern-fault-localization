# Interaction Pattern-Based Fault Localization in Multi-Agent Systems

Research artifact for the thesis: SBFL and Markov surprise over interaction-pattern tokens on the MAST dataset, with RQ4 LLM-as-a-judge semantic validation.

All paths assume repository root `RP_Code_Final/`.

## Research questions

| RQ | Topic | Scripts |
|----|-------|---------|
| RQ1 | Cross-task pattern discovery (SBFL + Markov) | `scripts/cross_task/run_rankings.sh` |
| RQ2 | N-gram granularity and stability | rankings + `run_bootstrap.sh` |
| RQ3 | Same-task HyperAgent SBFL (`psf__requests-1142`) | `scripts/same_task/run_rankings.sh` |
| RQ4 | LLM-as-a-judge semantic validation | `scripts/*/run_judge.sh` |

## Install

```bash
cd RP_Code_Final
pip install -r requirements.txt
pip install -e fault_localization
export PYTHONPATH="$(pwd)/fault_localization"
export MPLBACKEND=Agg
```

| Variable | Purpose |
|----------|---------|
| `REPO_ROOT` | Set automatically by `scripts/_common.sh` |
| `DEEPSEEK_API_KEY` | Required to re-run RQ4 judge API calls (`.env`) |
| `PYTHONPATH` | Must include `fault_localization` |

## Pipeline overview

All runnable entry points live under **`scripts/`**. Python logic is in `fault_localization/rp_analysis/` (`python -m rp_analysis.cli`).

```
scripts/
  cross_task/
    run_rankings.sh         # SBFL + RRF + Fisher/BH + Markov (grid or single cell)
    run_significance.sh     # Re-apply Fisher+BH to existing CSV (optional)
    run_bootstrap.sh        # Bootstrap rank-1 / top-k stability
    run_judge.sh            # RQ4 cross-task judge
  same_task/
    run_rankings.sh         # SBFL only (Markov off)
    run_significance.sh     # Same as cross-task significance helper
    run_bootstrap.sh
    run_judge.sh            # RQ4 same-task judge
```

Pre-tokenized exports are bundled under `data/mast/tokenized/` and `data/rq3_hyperagent/tokenized/`.

### 1. Cross-task rankings (RQ1)

Single cell:

```bash
bash scripts/cross_task/run_rankings.sh --framework MetaGPT --n 4
```

Full grid (4 frameworks × n ∈ {2,3,4,5}):

```bash
bash scripts/cross_task/run_rankings.sh
```

Outputs: `experiments/cross_task/runs/framework_pooled/n{N}/{Framework}/out/runs/`
- `rankings__global.csv` — SBFL formulas + RRF + Fisher/BH
- `markov_pattern_rankings__global.csv` — Markov surprise ranking

Re-running overwrites those reference paths locally. Per-run audit files (`log.txt`, `config.resolved.json`, `traces.csv`, `runs/*.manifest.json`) are gitignored and use repo-relative paths when regenerated.

Options: `--fisher-top-k K` (1–20, default 20), `--no-markov`, `--export-top-k K`.

### 1b. Re-apply Fisher + BH significance (optional)

Fisher exact test and Benjamini–Hochberg FDR run automatically during `run_rankings.sh`.
Use this only to refresh significance columns (`p_value`, `q_value`, `reject_bh`, …) on an
existing `rankings__global.csv` after changing Fisher/BH settings in the config, without
recomputing SBFL scores.

Cross-task example (MetaGPT, n=4):

```bash
bash scripts/cross_task/run_significance.sh \
  --config experiments/cross_task/configs/n4/MetaGPT/config.json \
  --rankings experiments/cross_task/runs/framework_pooled/n4/MetaGPT/out/runs/rankings__global.csv
```

Same-task example (n=4):

```bash
bash scripts/same_task/run_significance.sh \
  --config experiments/rq3/configs/n4/config.json \
  --rankings experiments/rq3/runs/n4/runs/rankings__global.csv
```

- `--config` — experiment config under `experiments/*/configs/` (must match the rankings cell).
- `--rankings` — existing CSV with contingency columns (`e_f`, `e_p`, `n_f`, `n_p`, `ochiai`, …).
- `--out PATH` — optional; default overwrites `--rankings` in place.

### 2. Same-task rankings (RQ3)

```bash
bash scripts/same_task/run_rankings.sh          # n=3 and n=4
bash scripts/same_task/run_rankings.sh --n 4
```

Outputs: `experiments/rq3/runs/n{N}/runs/rankings__global.csv`

Top pattern at n=4: `REQUEST :: PLAN :: ACT :: VERIFY_FAIL` (Ochiai ≈ 0.79).

### 3. Bootstrap stability

```bash
bash scripts/cross_task/run_bootstrap.sh --framework MetaGPT --n 4
bash scripts/same_task/run_bootstrap.sh --n 4
```

Default: B=100, seed=42, top-k=10.

### 4. RQ4 LLM-as-a-judge

Frozen results (no API key): `experiments/rq4/results/`

Re-run (requires API key):

```bash
cp .env.example .env   # add DEEPSEEK_API_KEY
bash scripts/cross_task/run_judge.sh --full
bash scripts/same_task/run_judge.sh --full
```

Single cross-task cell (example: MetaGPT n=4; run rankings first):

```bash
bash scripts/cross_task/run_rankings.sh --framework MetaGPT --n 4

bash scripts/cross_task/run_judge.sh --framework MetaGPT --n 4

bash scripts/cross_task/run_judge.sh --framework MetaGPT --n 4 --condition random
```

Outputs: `experiments/rq4/results/cross_task/MetaGPT/n4/rank1/` and `.../random/`.

Re-running the judge uses the same tasks and `temperature=0`, but hosted LLM inference is not fully deterministic — expect **qualitative** agreement (rank-1 ≫ random), not necessarily identical caused counts. See `experiments/rq4/results/corrections.md` for headline metrics.

| Condition | Caused \| triggered |
|-----------|---------------------|
| MetaGPT cross-task rank-1, n=4 | 67/98 (68.4%) |
| MetaGPT cross-task random, n=4 | 15/98 (15.3%) |
| AG2 cross-task rank-1, n=4 | 149/235 (63.4%) |
| HyperAgent same-task rank-1, n=4 | 27/42 (64.3%) |
| HyperAgent same-task random, n=4 | 0/42 (0%) |

### CLI (direct)

```bash
python -m rp_analysis.cli rank --study cross_task --framework MetaGPT --n 4
python -m rp_analysis.cli rank-grid --study cross_task
python -m rp_analysis.cli significance \
  --config experiments/cross_task/configs/n4/MetaGPT/config.json \
  --rankings experiments/cross_task/runs/framework_pooled/n4/MetaGPT/out/runs/rankings__global.csv
python -m rp_analysis.cli bootstrap --study same_task --n 4
python -m rp_analysis.judge_cli all --study cross_task --framework MetaGPT --n 4 --condition sbfl ...
python -m rp_analysis.cli judge-summarize --base experiments/rq4/results
```

## Data

- **MAST traces (987):** `data/mast/full_set/`
- **MAST tokenized exports:** `data/mast/tokenized/vocab/`
- **RQ3 HyperAgent runs (186):** `data/rq3_hyperagent/same_task/` + tokenized exports
