from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from src.config import (
    BASES,
    BOOTSTRAP_REPLICATES,
    EQUIVALENCE_ABSOLUTE,
    EQUIVALENCE_MAE_RELATIVE,
    PERMUTATION_REPLICATES,
    PRIMARY_FAMILY,
    PRIMARY_MATCHED,
    RESULTS_ROOT,
    TASK_BY_NAME,
)
from src.fast_metrics import (
    bootstrap_effect_distribution,
    metric_value as fast_metric_value,
    permutation_effect_distribution,
)


REPORT_ROOT = RESULTS_ROOT / "report"
RUN_ROOT = RESULTS_ROOT / "runs"


@dataclass(frozen=True)
class MethodPair:
    label: str
    method: str
    reference: str


PAIRS = (
    MethodPair("qrc_vs_matched", "qrc_ungated", "real_orthogonal_ungated"),
    MethodPair("qrc_vs_fourier", "qrc_ungated", "random_fourier_ungated"),
    MethodPair("qrc_vs_base", "qrc_ungated", "base"),
    MethodPair("gated_qrc_vs_matched", "qrc_gated", "real_orthogonal_gated"),
    MethodPair("gated_qrc_vs_base", "qrc_gated", "base"),
)


def metric_value(metric: str, truth: np.ndarray, prediction: np.ndarray) -> float:
    return fast_metric_value(metric, truth, prediction)


def better(metric: str, method: float, reference: float) -> float:
    return reference - method if metric == "MAE" else method - reference


def _prediction_name(method: str) -> str:
    return "base_test" if method == "base" else f"test_pred_{method}"


def load_runs() -> list[tuple[Path, dict[str, np.ndarray], dict[str, object]]]:
    runs = []
    for path in sorted(RUN_ROOT.glob("*/*/split_*.npz")):
        metadata_path = path.with_suffix(".json")
        if not metadata_path.exists():
            continue
        with np.load(path, allow_pickle=False) as values:
            arrays = {name: np.asarray(values[name]) for name in values.files}
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        runs.append((path, arrays, metadata))
    return runs


def _holm(values: list[float]) -> list[float]:
    count = len(values)
    order = np.argsort(values)
    adjusted = np.empty(count, dtype=float)
    running = 0.0
    for rank, index in enumerate(order):
        candidate = (count - rank) * values[index]
        running = max(running, candidate)
        adjusted[index] = min(1.0, running)
    return adjusted.tolist()


def _cluster_indices(clusters: np.ndarray) -> dict[str, np.ndarray]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for index, cluster in enumerate(clusters):
        grouped[str(cluster)].append(index)
    return {key: np.asarray(value, dtype=np.int64) for key, value in grouped.items()}


def _bootstrap_delta(
    metric: str,
    truth: np.ndarray,
    method_predictions: list[np.ndarray],
    reference_predictions: list[np.ndarray],
    clusters: np.ndarray,
    replicates: int,
    seed: int,
) -> np.ndarray:
    grouped = _cluster_indices(clusters)
    keys = np.asarray(sorted(grouped), dtype=object)
    rng = np.random.default_rng(seed)
    sampled_lists = []
    for _ in range(replicates):
        for _attempt in range(100):
            sampled = rng.choice(keys, size=len(keys), replace=True)
            indices = np.concatenate([grouped[str(key)] for key in sampled])
            sampled_truth = truth[indices]
            if metric not in {"AUROC", "AUPRC"} or len(np.unique(sampled_truth)) == 2:
                break
        else:
            raise RuntimeError("Cluster bootstrap could not preserve both classes")
        sampled_lists.append(indices)
    maximum_length = max(len(indices) for indices in sampled_lists)
    sampled_rows = np.full((replicates, maximum_length), -1, dtype=np.int64)
    sampled_lengths = np.empty(replicates, dtype=np.int64)
    for replicate, indices in enumerate(sampled_lists):
        sampled_rows[replicate, : len(indices)] = indices
        sampled_lengths[replicate] = len(indices)
    metric_codes = {"AUROC": 0, "AUPRC": 1, "Spearman": 2, "MAE": 3}
    return bootstrap_effect_distribution(
        metric_codes[metric],
        np.ascontiguousarray(truth, dtype=np.float64),
        np.ascontiguousarray(np.column_stack(method_predictions), dtype=np.float64),
        np.ascontiguousarray(np.column_stack(reference_predictions), dtype=np.float64),
        sampled_rows,
        sampled_lengths,
    )


def _permutation_delta(
    metric: str,
    truth: np.ndarray,
    method_predictions: list[np.ndarray],
    reference_predictions: list[np.ndarray],
    clusters: np.ndarray,
    observed: float,
    replicates: int,
    seed: int,
) -> tuple[float, np.ndarray]:
    grouped = _cluster_indices(clusters)
    keys = np.asarray(sorted(grouped), dtype=object)
    rng = np.random.default_rng(seed)
    key_index = {str(key): index for index, key in enumerate(keys)}
    cluster_codes = np.asarray([key_index[str(value)] for value in clusters])
    cluster_flips = rng.random((replicates, len(keys))) < 0.5
    row_flips = cluster_flips[:, cluster_codes]
    metric_codes = {"AUROC": 0, "AUPRC": 1, "Spearman": 2, "MAE": 3}
    distribution = permutation_effect_distribution(
        metric_codes[metric],
        np.ascontiguousarray(truth, dtype=np.float64),
        np.ascontiguousarray(np.column_stack(method_predictions), dtype=np.float64),
        np.ascontiguousarray(np.column_stack(reference_predictions), dtype=np.float64),
        row_flips,
    )
    p_value = (1.0 + np.sum(np.abs(distribution) >= abs(observed) - 1e-12)) / (
        replicates + 1.0
    )
    return float(p_value), distribution


def _equivalence_margin(metric: str, base_scores: list[float]) -> float:
    if metric == "MAE":
        return float(EQUIVALENCE_MAE_RELATIVE * np.mean(base_scores))
    return float(EQUIVALENCE_ABSOLUTE[metric])


def build_report(
    bootstrap_replicates: int = BOOTSTRAP_REPLICATES,
    permutation_replicates: int = PERMUTATION_REPLICATES,
) -> None:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    runs = load_runs()
    if not runs:
        raise RuntimeError("No completed runs found")

    by_key: dict[tuple[str, str, int], tuple[dict[str, np.ndarray], dict[str, object]]] = {}
    for _path, arrays, metadata in runs:
        by_key[
            (str(metadata["base"]), str(metadata["task"]), int(metadata["split_seed"]))
        ] = (arrays, metadata)

    metric_rows = []
    gate_rows = []
    map_rows = []
    matched_map_rows = []
    methods = (
        "base",
        "qrc_ungated",
        "real_orthogonal_ungated",
        "random_fourier_ungated",
        "qrc_gated",
        "real_orthogonal_gated",
        "random_fourier_gated",
        "qrc_plus_orth",
    )
    for (base, task, split_seed), (arrays, metadata) in sorted(by_key.items()):
        metric = str(metadata["metric"])
        truth = arrays["y_test"]
        for method in methods:
            array_name = _prediction_name(method)
            value = metric_value(metric, truth, arrays[array_name])
            metric_rows.append(
                {
                    "base": base,
                    "task": task,
                    "metric": metric,
                    "split_seed": split_seed,
                    "method": method,
                    "score": value,
                }
            )
        for family, weight in metadata["gate_weights"].items():
            gate_rows.append(
                {
                    "base": base,
                    "task": task,
                    "metric": metric,
                    "split_seed": split_seed,
                    "family": family,
                    "weight": float(weight),
                }
            )
        base_prediction = arrays["base_test"]
        if str(metadata["kind"]) == "classification":
            from scipy.special import expit

            base_logit = np.log(
                np.clip(base_prediction, 1e-7, 1 - 1e-7)
            ) - np.log(np.clip(1 - base_prediction, 1e-7, 1 - 1e-7))
        for family in ("qrc", "real_orthogonal", "random_fourier"):
            delta_maps = arrays[f"test_delta_maps_{family}"]
            for map_index, seed in enumerate(metadata["map_seeds"]):
                delta = delta_maps[:, map_index]
                if str(metadata["kind"]) == "classification":
                    from scipy.special import expit

                    base_logit = np.log(np.clip(base_prediction, 1e-7, 1 - 1e-7)) - np.log(
                        np.clip(1 - base_prediction, 1e-7, 1 - 1e-7)
                    )
                    prediction = expit(base_logit + delta)
                else:
                    prediction = base_prediction + delta
                map_rows.append(
                    {
                        "base": base,
                        "task": task,
                        "metric": metric,
                        "split_seed": split_seed,
                        "family": family,
                        "map_seed": int(seed),
                        "gain_vs_base": better(
                            metric,
                            metric_value(metric, truth, prediction),
                            metric_value(metric, truth, base_prediction),
                        ),
                    }
                )
        for map_index, map_seed in enumerate(metadata["map_seeds"]):
            qrc_delta = arrays["test_delta_maps_qrc"][:, map_index]
            orth_delta = arrays["test_delta_maps_real_orthogonal"][:, map_index]
            if str(metadata["kind"]) == "classification":
                qrc_prediction = expit(base_logit + qrc_delta)
                orth_prediction = expit(base_logit + orth_delta)
            else:
                qrc_prediction = base_prediction + qrc_delta
                orth_prediction = base_prediction + orth_delta
            matched_map_rows.append(
                {
                    "base": base,
                    "task": task,
                    "metric": metric,
                    "split_seed": split_seed,
                    "map_seed": int(map_seed),
                    "qrc_minus_orth": better(
                        metric,
                        metric_value(metric, truth, qrc_prediction),
                        metric_value(metric, truth, orth_prediction),
                    ),
                }
            )

    metrics = pd.DataFrame(metric_rows)
    gates = pd.DataFrame(gate_rows)
    maps = pd.DataFrame(map_rows)
    metrics.to_csv(REPORT_ROOT / "metrics_by_seed.csv", index=False, encoding="utf-8-sig")
    gates.to_csv(REPORT_ROOT / "gate_weights.csv", index=False, encoding="utf-8-sig")
    maps.to_csv(REPORT_ROOT / "map_sensitivity.csv", index=False, encoding="utf-8-sig")
    matched_maps = pd.DataFrame(matched_map_rows)
    matched_maps.to_csv(
        REPORT_ROOT / "matched_map_effects.csv",
        index=False,
        encoding="utf-8-sig",
    )
    matched_map_summary = (
        matched_maps.groupby(["base", "task", "metric", "map_seed"], as_index=False)
        .agg(
            mean_effect_across_splits=("qrc_minus_orth", "mean"),
            sd_across_splits=("qrc_minus_orth", "std"),
            positive_splits=("qrc_minus_orth", lambda x: (x > 0).sum()),
        )
    )
    matched_map_summary.to_csv(
        REPORT_ROOT / "matched_map_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    endpoint = (
        metrics.groupby(["base", "task", "metric", "method"], as_index=False)
        .agg(mean_score=("score", "mean"), sd_score=("score", "std"))
    )
    endpoint_for_pivot = endpoint.copy()
    endpoint_for_pivot["method"] = endpoint_for_pivot["method"].replace(
        {"base": "classical_base"}
    )
    pivot = (
        endpoint_for_pivot.set_index(["base", "task", "metric", "method"])["mean_score"]
        .unstack("method")
        .reset_index()
    )
    pivot.to_csv(REPORT_ROOT / "endpoint_summary.csv", index=False, encoding="utf-8-sig")

    summary_rows = []
    effect_records = []
    comparisons = [
        MethodPair("qrc_vs_matched", "qrc_ungated", "real_orthogonal_ungated"),
        MethodPair("qrc_vs_fourier", "qrc_ungated", "random_fourier_ungated"),
        MethodPair("qrc_vs_base", "qrc_ungated", "base"),
        MethodPair("gated_qrc_vs_matched", "qrc_gated", "real_orthogonal_gated"),
        MethodPair("gated_qrc_vs_base", "qrc_gated", "base"),
        MethodPair("augmented_qrc_vs_matched", "qrc_plus_orth", "real_orthogonal_gated"),
        MethodPair("augmented_qrc_vs_base", "qrc_plus_orth", "base"),
    ]
    for base in BASES:
        for pair in comparisons:
            tasks = sorted({key[1] for key in by_key if key[0] == base})
            pair_results = []
            for task_index, task in enumerate(tasks):
                metadata_item = next(value for key, value in by_key.items() if key[0] == base and key[1] == task)
                metric = str(metadata_item[1]["metric"])
                seeds = sorted(key[2] for key in by_key if key[0] == base and key[1] == task)
                truth = metadata_item[0]["y_test"]
                clusters = metadata_item[0]["test_scaffold"].astype(str)
                method_predictions = [
                    by_key[(base, task, seed)][0][_prediction_name(pair.method)]
                    for seed in seeds
                ]
                reference_predictions = [
                    by_key[(base, task, seed)][0][_prediction_name(pair.reference)]
                    for seed in seeds
                ]
                per_seed_effects = [
                    better(
                        metric,
                        metric_value(metric, by_key[(base, task, seed)][0]["y_test"], method),
                        metric_value(metric, by_key[(base, task, seed)][0]["y_test"], reference),
                    )
                    for seed, method, reference in zip(
                        seeds, method_predictions, reference_predictions, strict=True
                    )
                ]
                observed = float(np.mean(per_seed_effects))
                bootstrap = _bootstrap_delta(
                    metric,
                    truth,
                    method_predictions,
                    reference_predictions,
                    clusters,
                    bootstrap_replicates,
                    7000 + task_index + 100 * BASES.index(base),
                )
                p_value, permutation = _permutation_delta(
                    metric,
                    truth,
                    method_predictions,
                    reference_predictions,
                    clusters,
                    observed,
                    permutation_replicates,
                    9000 + task_index + 100 * BASES.index(base),
                )
                base_scores = [
                    metric_value(metric, by_key[(base, task, seed)][0]["y_test"], by_key[(base, task, seed)][0]["base_test"])
                    for seed in seeds
                ]
                margin = _equivalence_margin(metric, base_scores)
                equivalence_lower = float((1 + np.sum(bootstrap <= -margin)) / (len(bootstrap) + 1))
                equivalence_upper = float((1 + np.sum(bootstrap >= margin)) / (len(bootstrap) + 1))
                pair_results.append(
                    {
                        "base": base,
                        "comparison": pair.label,
                        "task": task,
                        "metric": metric,
                        "n_seeds": len(seeds),
                        "effect_better_positive": observed,
                        "ci_low": float(np.quantile(bootstrap, 0.025)),
                        "ci_high": float(np.quantile(bootstrap, 0.975)),
                        "permutation_p": p_value,
                        "equivalence_margin": margin,
                        "equivalence_p": max(equivalence_lower, equivalence_upper),
                        "positive_seeds": int(sum(value > 0 for value in per_seed_effects)),
                    }
                )
                effect_records.append(
                    {
                        "base": base,
                        "comparison": pair.label,
                        "task": task,
                        "metric": metric,
                        "seed_effect": per_seed_effects,
                        "bootstrap": bootstrap,
                        "permutation": permutation,
                    }
                )
            adjusted = _holm([item["permutation_p"] for item in pair_results])
            adjusted_equivalence = _holm([item["equivalence_p"] for item in pair_results])
            for item, holm, holm_eq in zip(
                pair_results, adjusted, adjusted_equivalence, strict=True
            ):
                item["holm_p"] = holm
                item["holm_equivalence_p"] = holm_eq
                summary_rows.append(item)

    summaries = pd.DataFrame(summary_rows)
    summaries.to_csv(REPORT_ROOT / "comparisons.csv", index=False, encoding="utf-8-sig")

    # Compact maps summary used in the manuscript.
    map_summary = (
        maps.groupby(["base", "task", "metric", "family"], as_index=False)
        .agg(
            mean_gain_across_splits=("gain_vs_base", "mean"),
            min_gain=("gain_vs_base", "min"),
            max_gain=("gain_vs_base", "max"),
            sd_across_map_and_split=("gain_vs_base", "std"),
        )
    )
    map_summary.to_csv(REPORT_ROOT / "map_summary.csv", index=False, encoding="utf-8-sig")

    fig, axes = plt.subplots(
        nrows=2,
        ncols=2,
        figsize=(10.5, 8.5),
        sharex="col",
        constrained_layout=True,
    )
    selected = summaries[
        summaries.comparison.isin(["qrc_vs_matched", "gated_qrc_vs_matched", "qrc_vs_base", "gated_qrc_vs_base"])
    ]
    for column, base in enumerate(BASES):
        for row, comparison in enumerate(["qrc_vs_matched", "qrc_vs_base"]):
            axis = axes[row, column]
            subset = selected[
                (selected.base == base) & (selected.comparison == comparison)
            ].sort_values("task")
            positions = np.arange(len(subset))
            axis.errorbar(
                subset.effect_better_positive,
                positions,
                xerr=np.vstack(
                    [
                        subset.effect_better_positive - subset.ci_low,
                        subset.ci_high - subset.effect_better_positive,
                    ]
                ),
                fmt="o",
                markersize=3.5,
                color="#2b6cb0" if comparison == "qrc_vs_matched" else "#9a3412",
            )
            axis.axvline(0, color="black", linewidth=0.8, alpha=0.6)
            axis.set_yticks(positions)
            axis.set_yticklabels(subset.task, fontsize=7)
            axis.invert_yaxis()
            axis.set_title(f"{base}: {comparison}", fontsize=10)
            axis.grid(axis="x", alpha=0.2)
    fig.suptitle("Direction-normalised endpoint effects (positive favours QRC)", fontsize=12)
    fig.savefig(REPORT_ROOT / "forest.png", dpi=300)
    fig.savefig(REPORT_ROOT / "forest.pdf")
    plt.close(fig)

    readme = {
        "runs": len(runs),
        "bases": sorted({key[0] for key in by_key}),
        "tasks": sorted({key[1] for key in by_key}),
        "split_seeds": sorted({key[2] for key in by_key}),
        "bootstrap_replicates": bootstrap_replicates,
        "permutation_replicates": permutation_replicates,
        "equivalence_margins": {
            "absolute": EQUIVALENCE_ABSOLUTE,
            "MAE_relative": EQUIVALENCE_MAE_RELATIVE,
        },
    }
    (REPORT_ROOT / "report_manifest.json").write_text(
        pd.Series(readme).to_json(indent=2, force_ascii=False) + "\n",
        encoding="utf-8",
    )

