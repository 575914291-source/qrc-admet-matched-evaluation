from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import (
    BOOTSTRAP_REPLICATES,
    PERMUTATION_REPLICATES,
    RESULTS_ROOT,
    SPLIT_SEEDS,
)
from src.data import write_json
from src.external_data import (
    EXTERNAL_ROOT,
    _tdc_canonical_set,
    canonical_smiles,
)
from src.fast_metrics import metric_value
from src.report import _bootstrap_delta, _holm, _permutation_delta
from src.run_external_validation import (
    EXTERNAL_TASKS,
    OUTPUT_ROOT as EXTERNAL_RUN_ROOT,
)


OUTPUT_ROOT = RESULTS_ROOT / "external_continuous"
CONTRASTS = (
    ("qrc_gated", "orth_gated"),
    ("qrc_plus_orth", "orth_gated"),
    ("qrc_gated", "base"),
)
METHODS = (
    "base",
    "qrc_ungated",
    "orth_ungated",
    "qrc_gated",
    "orth_gated",
    "qrc_plus_orth",
)


def _deduplicate(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["canonical_smiles"] = frame["SMILES"].map(canonical_smiles)
    return (
        frame.dropna(subset=["canonical_smiles"])
        .drop_duplicates("canonical_smiles", keep="first")
        .reset_index(drop=True)
    )


def _continuous_labels(task: str) -> pd.DataFrame:
    if task == "herg":
        frame = pd.read_csv(EXTERNAL_ROOT / "hERG_Dataset.csv")
        frame = frame[frame["USED_AS"].eq("Test-set")].copy()
        frame = _deduplicate(frame)
        frame = frame[
            ~frame["canonical_smiles"].isin(_tdc_canonical_set("herg"))
        ].reset_index(drop=True)
        frame["continuous"] = frame["PIC50"].astype(float)
        frame["binary_label"] = (frame["continuous"] >= 4.5).astype(int)
        frame["continuous_name"] = "PIC50"
        return frame

    if task == "bbb_martins":
        frame = pd.read_csv(
            EXTERNAL_ROOT / "B3DB_classification.tsv", sep="\t"
        )
        frame = frame.dropna(subset=["SMILES", "BBB+/BBB-"]).copy()
        frame = _deduplicate(frame)
        frame = frame[
            ~frame["canonical_smiles"].isin(_tdc_canonical_set("bbb_martins"))
        ].reset_index(drop=True)
        frame["continuous"] = pd.to_numeric(frame["logBB"], errors="coerce")
        frame["binary_label"] = frame["BBB+/BBB-"].map(
            {"BBB+": 1, "BBB-": 0}
        )
        frame["continuous_name"] = "logBB"
        return frame

    raise ValueError(f"Unsupported external task: {task}")


def _load_runs(base: str, task: str) -> list[dict[str, np.ndarray]]:
    runs = []
    for seed in SPLIT_SEEDS:
        path = EXTERNAL_RUN_ROOT / base / task / f"split_{seed}.npz"
        if not path.exists():
            raise FileNotFoundError(path)
        with np.load(path, allow_pickle=False) as values:
            runs.append({name: np.asarray(values[name]) for name in values.files})
    return runs


def _effect(
    truth: np.ndarray,
    method_predictions: list[np.ndarray],
    reference_predictions: list[np.ndarray],
) -> float:
    per_seed = [
        metric_value("Spearman", truth, method)
        - metric_value("Spearman", truth, reference)
        for method, reference in zip(
            method_predictions, reference_predictions, strict=True
        )
    ]
    return float(np.mean(per_seed))


def analyze(
    bootstrap_replicates: int = BOOTSTRAP_REPLICATES,
    permutation_replicates: int = PERMUTATION_REPLICATES,
) -> dict[str, object]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    score_rows = []
    contrast_rows = []
    effects_by_seed = []
    task_metadata = {}

    for task in EXTERNAL_TASKS:
        frame = _continuous_labels(task)
        mask = frame["continuous"].notna().to_numpy()
        truth_all = frame["continuous"].to_numpy(dtype=float)
        truth = truth_all[mask]
        task_metadata[task] = {
            "continuous_label": str(frame["continuous_name"].iloc[0]),
            "retained_external": int(len(frame)),
            "continuous_available": int(mask.sum()),
            "continuous_missing": int((~mask).sum()),
            "continuous_coverage": float(mask.mean()),
            "binary_positive_rate_in_continuous_subset": float(
                frame.loc[mask, "binary_label"].mean()
            ),
            "continuous_min": float(np.min(truth)),
            "continuous_max": float(np.max(truth)),
            "continuous_mean": float(np.mean(truth)),
        }

        for base in ("extra_trees", "catboost"):
            runs = _load_runs(base, task)
            n_external = len(runs[0]["y"])
            if n_external != len(frame):
                raise RuntimeError(
                    f"{task}/{base}: reconstructed labels ({len(frame)}) "
                    f"do not align with saved predictions ({n_external})"
                )
            scaffolds = runs[0]["scaffold"].astype(str)[mask]

            for method in METHODS:
                scores = [
                    metric_value(
                        "Spearman", truth, run[method][mask]
                    )
                    for run in runs
                ]
                score_rows.append(
                    {
                        "task": task,
                        "base": base,
                        "continuous_label": str(
                            frame["continuous_name"].iloc[0]
                        ),
                        "method": method,
                        "n": int(mask.sum()),
                        "n_scaffolds": int(len(set(scaffolds))),
                        "mean_spearman": float(np.mean(scores)),
                        "sd_across_splits": float(np.std(scores, ddof=1)),
                        "positive_splits": int(sum(value > 0 for value in scores)),
                    }
                )

            for contrast_index, (method, reference) in enumerate(CONTRASTS):
                method_predictions = [run[method][mask] for run in runs]
                reference_predictions = [run[reference][mask] for run in runs]
                per_seed = [
                    metric_value("Spearman", truth, method_value)
                    - metric_value("Spearman", truth, reference_value)
                    for method_value, reference_value in zip(
                        method_predictions, reference_predictions, strict=True
                    )
                ]
                observed = float(np.mean(per_seed))
                base_index = ("extra_trees", "catboost").index(base)
                task_index = EXTERNAL_TASKS.index(task)
                seed_offset = (
                    16000
                    + 1000 * base_index
                    + 100 * task_index
                    + contrast_index
                )
                bootstrap = _bootstrap_delta(
                    "Spearman",
                    truth,
                    method_predictions,
                    reference_predictions,
                    scaffolds,
                    bootstrap_replicates,
                    seed_offset,
                )
                permutation_p, _ = _permutation_delta(
                    "Spearman",
                    truth,
                    method_predictions,
                    reference_predictions,
                    scaffolds,
                    observed,
                    permutation_replicates,
                    seed_offset + 500,
                )
                contrast_rows.append(
                    {
                        "task": task,
                        "base": base,
                        "method": method,
                        "reference": reference,
                        "continuous_label": str(
                            frame["continuous_name"].iloc[0]
                        ),
                        "n": int(mask.sum()),
                        "n_scaffolds": int(len(set(scaffolds))),
                        "effect_spearman": observed,
                        "ci_low": float(np.quantile(bootstrap, 0.025)),
                        "ci_high": float(np.quantile(bootstrap, 0.975)),
                        "permutation_p": permutation_p,
                        "positive_splits": int(
                            sum(value > 0 for value in per_seed)
                        ),
                    }
                )
                for split_seed, value in zip(SPLIT_SEEDS, per_seed, strict=True):
                    effects_by_seed.append(
                        {
                            "task": task,
                            "base": base,
                            "method": method,
                            "reference": reference,
                            "split_seed": split_seed,
                            "effect_spearman": value,
                        }
                    )

    scores = pd.DataFrame(score_rows)
    contrasts = pd.DataFrame(contrast_rows)
    contrasts["holm_p"] = _holm(contrasts["permutation_p"].tolist())

    scores.to_csv(
        OUTPUT_ROOT / "transfer_scores.csv",
        index=False,
        encoding="utf-8-sig",
    )
    contrasts.to_csv(
        OUTPUT_ROOT / "comparisons.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pd.DataFrame(effects_by_seed).to_csv(
        OUTPUT_ROOT / "effects_by_seed.csv",
        index=False,
        encoding="utf-8-sig",
    )
    audit = {
        "status": "passed",
        "analysis_type": "exploratory_continuous_label_ranking_transfer",
        "runs": 2 * len(EXTERNAL_TASKS) * len(SPLIT_SEEDS),
        "bootstrap_replicates": bootstrap_replicates,
        "permutation_replicates": permutation_replicates,
        "multiplicity": "Holm across all 12 pre-specified exploratory contrasts",
        "tasks": task_metadata,
        "interpretation_limit": (
            "Binary-trained model outputs were ranked against continuous "
            "labels. This is not an independently trained regression cohort."
        ),
        "checks": [
            "reconstructed continuous-label rows align with saved external predictions",
            "canonical non-isomeric overlap with TDC is removed",
            "paired scaffold bootstrap and scaffold permutation are used",
            "the B3DB continuous subset is reported with coverage and class enrichment",
        ],
    }
    write_json(OUTPUT_ROOT / "audit.json", audit)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", type=int, default=BOOTSTRAP_REPLICATES)
    parser.add_argument(
        "--permutations", type=int, default=PERMUTATION_REPLICATES
    )
    args = parser.parse_args()
    audit = analyze(args.bootstrap, args.permutations)
    print(
        pd.read_csv(OUTPUT_ROOT / "comparisons.csv")
        .sort_values("permutation_p")
        .to_string(index=False)
    )
    print(audit["interpretation_limit"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
