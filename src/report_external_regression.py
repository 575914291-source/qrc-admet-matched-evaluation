from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.data import write_json
from src.fast_metrics import metric_value
from src.report import _bootstrap_delta, _holm, _permutation_delta
from src.run_external_regression import (
    MODEL_METRIC,
    OUTPUT_ROOT,
    TASK,
    _path,
)


MODEL_SEEDS = (1, 2, 3, 4, 5)
CONTRASTS = (
    ("qrc", "real_orthogonal", "ungated"),
    ("qrc", "base", "ungated"),
    ("random_fourier", "real_orthogonal", "ungated"),
)
METRICS = ("Spearman", "MAE")


def _prediction_name(method: str, state: str) -> str:
    if method == "base":
        return "base_test"
    return f"{method}_test_{state}"


def build_report(
    bootstrap_replicates: int = 1000,
    permutation_replicates: int = 1999,
) -> pd.DataFrame:
    score_rows = []
    comparison_rows = []
    effect_rows = []
    gate_rows = []
    for base_index, base in enumerate(("extra_trees", "catboost")):
        runs = []
        for seed in MODEL_SEEDS:
            path = _path(base, seed)
            metadata = json.loads(
                path.with_suffix(".json").read_text(encoding="utf-8")
            )
            with np.load(path, allow_pickle=False) as values:
                arrays = {
                    name: np.asarray(values[name]) for name in values.files
                }
            runs.append((seed, arrays, metadata))
        truth = runs[0][1]["y_test"]
        scaffolds = runs[0][1]["test_scaffold"].astype(str)

        methods = (
            ("base", "base_test"),
            ("qrc_ungated", "qrc_test_ungated"),
            ("qrc_gated", "qrc_test_gated"),
            ("orth_ungated", "real_orthogonal_test_ungated"),
            ("orth_gated", "real_orthogonal_test_gated"),
            (
                "fourier_ungated",
                "random_fourier_test_ungated",
            ),
            (
                "fourier_gated",
                "random_fourier_test_gated",
            ),
        )
        for method, array_name in methods:
            for metric in METRICS:
                scores = [
                    metric_value(metric, truth, arrays[array_name])
                    for _, arrays, _ in runs
                ]
                score_rows.append(
                    {
                        "base": base,
                        "task": TASK,
                        "metric": metric,
                        "method": method,
                        "mean_score": float(np.mean(scores)),
                        "sd_across_seeds": float(np.std(scores, ddof=1)),
                    }
                )
        for _, arrays, metadata in runs:
            for family in ("qrc", "real_orthogonal", "random_fourier"):
                gate_rows.append(
                    {
                        "base": base,
                        "model_seed": int(metadata["model_seed"]),
                        "family": family,
                        "gate": float(arrays[f"{family}_gate"][0]),
                    }
                )

        for metric_index, metric in enumerate(METRICS):
            sign = 1.0 if metric == "Spearman" else -1.0
            for contrast_index, (method, reference, state) in enumerate(CONTRASTS):
                method_predictions = [
                    arrays[_prediction_name(method, state)]
                    for _, arrays, _ in runs
                ]
                reference_predictions = [
                    arrays[_prediction_name(reference, state)]
                    for _, arrays, _ in runs
                ]
                per_seed = [
                    sign
                    * (
                        metric_value(metric, truth, method_value)
                        - metric_value(metric, truth, reference_value)
                    )
                    for method_value, reference_value in zip(
                        method_predictions,
                        reference_predictions,
                        strict=True,
                    )
                ]
                observed = float(np.mean(per_seed))
                seed_offset = (
                    30000
                    + 1000 * base_index
                    + 100 * metric_index
                    + 10 * contrast_index
                )
                bootstrap = _bootstrap_delta(
                    metric,
                    truth,
                    method_predictions,
                    reference_predictions,
                    scaffolds,
                    bootstrap_replicates,
                    seed_offset,
                )
                permutation_p, _ = _permutation_delta(
                    metric,
                    truth,
                    method_predictions,
                    reference_predictions,
                    scaffolds,
                    observed,
                    permutation_replicates,
                    seed_offset + 5,
                )
                comparison_rows.append(
                    {
                        "base": base,
                        "task": TASK,
                        "metric": metric,
                        "method": method,
                        "reference": reference,
                        "state": state,
                        "n_test": int(len(truth)),
                        "n_scaffolds": int(len(set(scaffolds))),
                        "effect_better_positive": observed,
                        "ci_low": float(np.quantile(bootstrap, 0.025)),
                        "ci_high": float(np.quantile(bootstrap, 0.975)),
                        "permutation_p": permutation_p,
                        "positive_seeds": int(
                            sum(value > 0 for value in per_seed)
                        ),
                    }
                )
                for model_seed, value in zip(
                    MODEL_SEEDS, per_seed, strict=True
                ):
                    effect_rows.append(
                        {
                            "base": base,
                            "task": TASK,
                            "metric": metric,
                            "method": method,
                            "reference": reference,
                            "state": state,
                            "model_seed": model_seed,
                            "effect_better_positive": value,
                        }
                    )

    scores = pd.DataFrame(score_rows)
    comparisons = pd.DataFrame(comparison_rows)
    comparisons["holm_p"] = _holm(
        comparisons["permutation_p"].tolist()
    )
    scores.to_csv(
        OUTPUT_ROOT / "scores.csv",
        index=False,
        encoding="utf-8-sig",
    )
    comparisons.to_csv(
        OUTPUT_ROOT / "comparisons.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pd.DataFrame(effect_rows).to_csv(
        OUTPUT_ROOT / "effects_by_seed.csv",
        index=False,
        encoding="utf-8-sig",
    )
    gates = pd.DataFrame(gate_rows)
    gates.to_csv(
        OUTPUT_ROOT / "gate_weights.csv",
        index=False,
        encoding="utf-8-sig",
    )
    write_json(
        OUTPUT_ROOT / "report_manifest.json",
        {
            "task": TASK,
            "target": "PIC50",
            "primary_metric": MODEL_METRIC,
            "secondary_metric": "MAE",
            "bootstrap_replicates": bootstrap_replicates,
            "permutation_replicates": permutation_replicates,
            "multiplicity": (
                "Holm across all 12 exploratory metric/base/contrast tests"
            ),
            "gate_zero_counts": {
                base: int(
                    (
                        gates[
                            (gates.base == base)
                            & (gates.family == "qrc")
                        ].gate
                        == 0
                    ).sum()
                )
                for base in ("extra_trees", "catboost")
            },
        },
    )
    return comparisons


if __name__ == "__main__":
    frame = build_report()
    print(
        frame.sort_values("permutation_p")
        .to_string(index=False)
    )
