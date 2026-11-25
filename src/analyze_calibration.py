from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from src.config import MAP_SEEDS, RESULTS_ROOT, SPLIT_SEEDS, TASK_BY_NAME
from src.data import load_task_frames, make_split, write_json
from src.fast_metrics import (
    metric_value,
    permutation_effect_distribution,
)
from src.modeling import LogisticOffsetHead
from src.reservoir import (
    qrc_readouts,
    quadratic_features,
    random_fourier_features,
    real_orthogonal_readouts,
)
from src.run_benchmark import _task_matrix


OUTPUT_ROOT = RESULTS_ROOT / "calibration"
CALIBRATION_TASKS = ("herg", "bbb_martins", "solubility_aqsoldb")
SCENARIOS = ("qrc_signal", "classical_signal", "null")
FAMILIES = ("qrc", "real_orthogonal", "random_fourier")
REPLICATES_PER_SPLIT = 10
MAX_TRAIN = 700
MAX_TEST = 900
PERMUTATIONS = 199


def _subset_indices(size: int, maximum: int, seed: int) -> np.ndarray:
    if size <= maximum:
        return np.arange(size)
    return np.sort(
        np.random.default_rng(seed).choice(size, size=maximum, replace=False)
    )


def _map_features(
    train_latent: np.ndarray,
    test_latent: np.ndarray,
) -> dict[str, list[tuple[np.ndarray, np.ndarray]]]:
    maps: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {
        family: [] for family in FAMILIES
    }
    for seed in MAP_SEEDS:
        for family, readout in (
            ("qrc", qrc_readouts(seed)),
            ("real_orthogonal", real_orthogonal_readouts(seed)),
        ):
            maps[family].append(
                (
                    quadratic_features(train_latent, readout),
                    quadratic_features(test_latent, readout),
                )
            )
        maps["random_fourier"].append(
            (
                random_fourier_features(train_latent, seed),
                random_fourier_features(test_latent, seed),
            )
        )
    return maps


def _scaled_features(
    features: dict[str, list[tuple[np.ndarray, np.ndarray]]],
    train_indices: np.ndarray,
    test_indices: np.ndarray,
) -> dict[str, list[tuple[np.ndarray, np.ndarray]]]:
    result = {}
    for family, family_maps in features.items():
        result[family] = []
        for train_values, test_values in family_maps:
            scaler = StandardScaler().fit(train_values[train_indices])
            result[family].append(
                (
                    scaler.transform(train_values[train_indices]),
                    scaler.transform(test_values[test_indices]),
                )
            )
    return result


def _synthetic_target(
    scenario: str,
    source_family: str,
    family_features: dict[str, list[tuple[np.ndarray, np.ndarray]]],
    classification: bool,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, float]:
    train_features = np.mean(
        [item[0] for item in family_features[source_family]], axis=0
    )
    test_features = np.mean(
        [item[1] for item in family_features[source_family]], axis=0
    )
    if scenario == "null":
        if classification:
            train_truth = rng.integers(
                0, 2, size=len(train_features), dtype=np.int64
            ).astype(float)
            test_truth = rng.integers(
                0, 2, size=len(test_features), dtype=np.int64
            ).astype(float)
        else:
            train_truth = rng.normal(size=len(train_features))
            test_truth = rng.normal(size=len(test_features))
        return train_truth, test_truth, float("nan")
    coefficients = rng.normal(size=train_features.shape[1])
    coefficients /= max(np.linalg.norm(coefficients), 1e-12)
    train_signal = train_features @ coefficients
    test_signal = test_features @ coefficients
    noise_scale = float(rng.choice([0.35, 0.60, 0.90]))
    train_center = float(train_signal.mean())
    train_scale = float(train_signal.std())
    train_scale = max(train_scale, 1e-12)
    train_score = (train_signal - train_center) / train_scale
    test_score = (test_signal - train_center) / train_scale
    if scenario != "null":
        train_score = train_score + rng.normal(
            scale=noise_scale, size=len(train_score)
        )
        test_score = test_score + rng.normal(
            scale=noise_scale, size=len(test_score)
        )
    if classification:
        train_truth = (train_score > 0.0).astype(float)
        test_truth = (test_score > 0.0).astype(float)
    else:
        train_truth = train_score
        test_truth = test_score
    return train_truth, test_truth, 1.0 / max(noise_scale, 1e-12)


def _fit_and_predict(
    kind: str,
    feature_maps: list[tuple[np.ndarray, np.ndarray]],
    train_truth: np.ndarray,
) -> np.ndarray:
    predictions = []
    for train_features, test_features in feature_maps:
        if kind == "classification":
            head = LogisticOffsetHead(l2=1.0)
            head.fit(train_features, train_truth, np.zeros_like(train_truth))
            predictions.append(head.predict_delta(test_features))
        else:
            head = Ridge(alpha=10.0, fit_intercept=True)
            head.fit(train_features, train_truth)
            predictions.append(head.predict(test_features))
    return np.mean(predictions, axis=0)


def _permutation_p(
    metric: str,
    truth: np.ndarray,
    qrc: np.ndarray,
    orth: np.ndarray,
    rng: np.random.Generator,
) -> float:
    metric_codes = {"AUROC": 0, "Spearman": 2}
    flips = rng.random((PERMUTATIONS, len(truth))) < 0.5
    distribution = permutation_effect_distribution(
        metric_codes[metric],
        np.ascontiguousarray(truth, dtype=np.float64),
        np.ascontiguousarray(qrc.reshape(-1, 1), dtype=np.float64),
        np.ascontiguousarray(orth.reshape(-1, 1), dtype=np.float64),
        flips,
    )
    observed = metric_value(metric, truth, qrc) - metric_value(
        metric, truth, orth
    )
    return float(
        (1 + np.sum(np.abs(distribution) >= abs(observed) - 1e-12))
        / (PERMUTATIONS + 1)
    )


def _collect() -> pd.DataFrame:
    rows = []
    for base in ("extra_trees", "catboost"):
        for task in CALIBRATION_TASKS:
            spec = TASK_BY_NAME[task]
            frames = load_task_frames(task)
            for split_seed in SPLIT_SEEDS:
                train, valid, test = make_split(frames, split_seed)
                train_x = _task_matrix(base, train)
                valid_x = _task_matrix(base, valid)
                test_x = _task_matrix(base, test)
                train_latent, valid_latent, test_latent = _latent(
                    train_x, valid_x, test_x, split_seed
                )
                raw_features = _map_features(train_latent, test_latent)
                train_indices = _subset_indices(
                    len(train_latent),
                    MAX_TRAIN,
                    split_seed * 1000 + 1,
                )
                test_indices = _subset_indices(
                    len(test_latent),
                    MAX_TEST,
                    split_seed * 1000 + 2,
                )
                scaled = _scaled_features(
                    raw_features, train_indices, test_indices
                )
                for replicate in range(REPLICATES_PER_SPLIT):
                    for scenario in SCENARIOS:
                        rng = np.random.default_rng(
                            split_seed * 100000
                            + replicate * 10
                            + SCENARIOS.index(scenario)
                        )
                        source_family = (
                            "qrc"
                            if scenario == "qrc_signal"
                            else (
                                "real_orthogonal"
                                if scenario == "classical_signal"
                                else "qrc"
                            )
                        )
                        train_truth, test_truth, snr = _synthetic_target(
                            scenario,
                            source_family,
                            scaled,
                            spec.binary,
                            rng,
                        )
                        predictions = {
                            family: _fit_and_predict(
                                spec.kind,
                                scaled[family],
                                train_truth,
                            )
                            for family in FAMILIES
                        }
                        metric = "AUROC" if spec.binary else "Spearman"
                        scores = {
                            family: metric_value(metric, test_truth, prediction)
                            for family, prediction in predictions.items()
                        }
                        expected = (
                            "qrc"
                            if scenario == "qrc_signal"
                            else (
                                "real_orthogonal"
                                if scenario == "classical_signal"
                                else "none"
                            )
                        )
                        rows.append(
                            {
                                "base": base,
                                "task": task,
                                "split_seed": split_seed,
                                "replicate": replicate,
                                "scenario": scenario,
                                "metric": metric,
                                "snr": snr,
                                "expected_source": expected,
                                "qrc_score": scores["qrc"],
                                "orthogonal_score": scores["real_orthogonal"],
                                "fourier_score": scores["random_fourier"],
                                "qrc_minus_orthogonal": (
                                    scores["qrc"] - scores["real_orthogonal"]
                                ),
                                "expected_family_wins": (
                                    scores[expected]
                                    > max(
                                        score
                                        for family, score in scores.items()
                                        if family != expected
                                    )
                                    if expected != "none"
                                    else np.nan
                                ),
                                "null_permutation_p": (
                                    _permutation_p(
                                        metric,
                                        test_truth,
                                        predictions["qrc"],
                                        predictions["real_orthogonal"],
                                        rng,
                                    )
                                    if scenario == "null"
                                    else np.nan
                                ),
                            }
                        )
    return pd.DataFrame(rows)


def _latent(
    train_x: np.ndarray,
    valid_x: np.ndarray,
    test_x: np.ndarray,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    from src.modeling import latent_features

    return latent_features(train_x, valid_x, test_x, seed=seed)


def _summarize(rows: pd.DataFrame) -> pd.DataFrame:
    records = []
    for (scenario, base), group in rows.groupby(["scenario", "base"]):
        records.append(
            {
                "scenario": scenario,
                "base": base,
                "n": int(len(group)),
                "qrc_minus_orthogonal_mean": float(
                    group["qrc_minus_orthogonal"].mean()
                ),
                "qrc_minus_orthogonal_sd": float(
                    group["qrc_minus_orthogonal"].std(ddof=1)
                ),
                "correct_selection_rate": (
                    float(group["expected_family_wins"].mean())
                    if scenario != "null"
                    else np.nan
                ),
                "null_false_positive_rate": (
                    float((group["null_permutation_p"] < 0.05).mean())
                    if scenario == "null"
                    else np.nan
                ),
            }
        )
    return pd.DataFrame(records).sort_values(["scenario", "base"])


def _plot(rows: pd.DataFrame) -> None:
    colors = {"extra_trees": "#5B9BD5", "catboost": "#8B1E3F"}
    figure, axes = plt.subplots(1, 2, figsize=(8.2, 3.6))
    for base in ("extra_trees", "catboost"):
        values = [
            rows[
                rows["base"].eq(base)
                & rows["scenario"].eq(scenario)
            ]["qrc_minus_orthogonal"].to_numpy()
            for scenario in SCENARIOS
        ]
        axes[0].boxplot(
            values,
            positions=np.arange(3) + (-0.16 if base == "extra_trees" else 0.16),
            widths=0.25,
            patch_artist=True,
            boxprops={"facecolor": colors[base], "alpha": 0.55},
            medianprops={"color": "#111111"},
            showfliers=False,
        )
    axes[0].axhline(0.0, color="#444444", linewidth=0.8)
    axes[0].set_xticks(np.arange(3))
    axes[0].set_xticklabels(
        ["QRC signal", "Classical signal", "Null"],
        rotation=15,
    )
    axes[0].set_ylabel("QRC minus orthogonal test metric")
    axes[0].set_title("Known-signal recovery")
    axes[0].grid(axis="y", color="#E5E7EB", linewidth=0.6)

    categories = [
        "qrc_signal",
        "classical_signal",
        "null",
    ]
    bars = []
    labels = []
    for base in ("extra_trees", "catboost"):
        subset = rows[rows["base"].eq(base)]
        rates = []
        for scenario in categories:
            group = subset[subset["scenario"].eq(scenario)]
            rate = (
                (group["null_permutation_p"] < 0.05).mean()
                if scenario == "null"
                else group["expected_family_wins"].mean()
            )
            rates.append(float(rate))
        bars.append(rates)
        labels.append(base.replace("_", " ").title())
    width = 0.35
    axis = axes[1]
    for index, (values, label) in enumerate(zip(bars, labels, strict=True)):
        axis.bar(
            np.arange(3) + (index - 0.5) * width,
            values,
            width=width,
            color=list(colors.values())[index],
            label=label,
        )
    axis.axhline(0.05, color="#444444", linestyle="--", linewidth=0.8)
    axis.set_xticks(np.arange(3))
    axis.set_xticklabels(["QRC signal", "Classical signal", "Null"], rotation=15)
    axis.set_ylim(0.0, 1.02)
    axis.set_ylabel("Correct recovery or null false positive rate")
    axis.set_title("Calibration criteria")
    axis.grid(axis="y", color="#E5E7EB", linewidth=0.6)
    axis.legend(frameon=False, fontsize=7)
    figure.tight_layout()
    figure.savefig(OUTPUT_ROOT / "calibration.png", dpi=600)
    figure.savefig(OUTPUT_ROOT / "calibration.pdf", bbox_inches="tight")
    plt.close(figure)


def analyze() -> dict[str, object]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    rows = _collect()
    summary = _summarize(rows)
    rows.to_csv(
        OUTPUT_ROOT / "runs.csv",
        index=False,
        encoding="utf-8-sig",
    )
    summary.to_csv(
        OUTPUT_ROOT / "summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    _plot(rows)
    summary_records = (
        summary.astype(object)
        .where(pd.notna(summary), None)
        .to_dict(orient="records")
    )
    result = {
        "status": "passed",
        "purpose": (
            "Calibrate the feature-stage matched evaluation with known QRC, "
            "known classical, and null synthetic targets."
        ),
        "tasks": list(CALIBRATION_TASKS),
        "bases": ["extra_trees", "catboost"],
        "split_seeds": list(SPLIT_SEEDS),
        "replicates_per_split": REPLICATES_PER_SPLIT,
        "scenarios": list(SCENARIOS),
        "summary": summary_records,
        "notes": [
            "The calibration isolates the 15-dimensional feature stage; "
            "the classical base offset is intentionally omitted.",
            "Classification calibration uses balanced synthetic binary "
            "targets generated from standardized latent scores.",
            "Regression calibration evaluates rank recovery with Spearman "
            "correlation.",
        ],
    }
    write_json(OUTPUT_ROOT / "summary.json", result)
    return {
        "status": "passed",
        "runs": len(rows),
        "summary": summary_records,
    }


if __name__ == "__main__":
    print(json.dumps(analyze(), ensure_ascii=False, indent=2))
