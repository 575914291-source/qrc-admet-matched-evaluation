from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from src.config import MAP_SEEDS, RESULTS_ROOT, SPLIT_SEEDS, TASK_BY_NAME
from src.data import load_task_frames, make_split, write_json
from src.modeling import latent_features
from src.reservoir import (
    qrc_readouts,
    quadratic_features,
    random_fourier_features,
    real_orthogonal_readouts,
)
from src.run_benchmark import _task_matrix


OUTPUT_ROOT = RESULTS_ROOT / "capacity_diagnostics"


def _spectral_metrics(matrix: np.ndarray) -> tuple[float, float]:
    values = np.asarray(matrix, dtype=np.float64)
    values = values - np.mean(values, axis=0, keepdims=True)
    singular = np.linalg.svd(values, compute_uv=False)
    if singular.size == 0 or not np.isfinite(singular).all():
        return float("nan"), float("nan")
    positive = singular[singular > 1e-12]
    if positive.size == 0:
        return 0.0, float("inf")
    probabilities = positive / positive.sum()
    effective_rank = float(
        np.exp(-np.sum(probabilities * np.log(probabilities)))
    )
    condition = (
        float(positive[0] / positive[-1])
        if positive.size > 1
        else float("inf")
    )
    return effective_rank, condition


def _center_gram(matrix: np.ndarray) -> np.ndarray:
    values = np.asarray(matrix, dtype=np.float64)
    gram = values @ values.T
    row_mean = gram.mean(axis=0, keepdims=True)
    column_mean = gram.mean(axis=1, keepdims=True)
    return gram - row_mean - column_mean + gram.mean()


def _linear_cka(left: np.ndarray, right: np.ndarray) -> float:
    left_gram = _center_gram(left)
    right_gram = _center_gram(right)
    numerator = float(np.sum(left_gram * right_gram))
    denominator = float(
        np.sqrt(
            np.sum(left_gram * left_gram)
            * np.sum(right_gram * right_gram)
        )
    )
    if denominator <= 1e-12:
        return float("nan")
    return numerator / denominator


def _family_features(
    train_latent: np.ndarray,
    test_latent: np.ndarray,
) -> dict[str, list[tuple[np.ndarray, np.ndarray]]]:
    result: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {
        "qrc": [],
        "real_orthogonal": [],
        "random_fourier": [],
    }
    for seed in MAP_SEEDS:
        for family, readout in (
            ("qrc", qrc_readouts(seed)),
            ("real_orthogonal", real_orthogonal_readouts(seed)),
        ):
            result[family].append(
                (
                    quadratic_features(train_latent, readout),
                    quadratic_features(test_latent, readout),
                )
            )
        result["random_fourier"].append(
            (
                random_fourier_features(train_latent, seed),
                random_fourier_features(test_latent, seed),
            )
        )
    return result


def _collect() -> tuple[pd.DataFrame, pd.DataFrame]:
    feature_rows = []
    cka_rows = []
    for base in ("extra_trees", "catboost"):
        for task_index, task in enumerate(TASK_BY_NAME, start=1):
            print(f"[{task_index}/22] {base} {task}", flush=True)
            frames = load_task_frames(task)
            for split_seed in SPLIT_SEEDS:
                train, valid, test = make_split(frames, split_seed)
                train_x = _task_matrix(base, train)
                test_x = _task_matrix(base, test)
                train_latent, _, test_latent = latent_features(
                    train_x,
                    _task_matrix(base, valid),
                    test_x,
                    seed=split_seed,
                )
                family_values = _family_features(train_latent, test_latent)
                standardized_test = {}
                for family, maps in family_values.items():
                    test_maps = []
                    for map_index, (train_features, test_features) in enumerate(
                        maps
                    ):
                        scaler = StandardScaler().fit(train_features)
                        train_scaled = scaler.transform(train_features)
                        test_scaled = scaler.transform(test_features)
                        train_rank, train_condition = _spectral_metrics(
                            train_scaled
                        )
                        test_rank, test_condition = _spectral_metrics(
                            test_scaled
                        )
                        feature_rows.append(
                            {
                                "base": base,
                                "task": task,
                                "split_seed": split_seed,
                                "family": family,
                                "map_index": map_index,
                                "map_seed": MAP_SEEDS[map_index],
                                "train_effective_rank": train_rank,
                                "train_condition_number": train_condition,
                                "test_effective_rank": test_rank,
                                "test_condition_number": test_condition,
                                "n_train": int(len(train_scaled)),
                                "n_test": int(len(test_scaled)),
                            }
                        )
                        test_maps.append(test_scaled)
                    mean_features = np.mean(test_maps, axis=0)
                    standardized_test[family] = mean_features
                for left, right in (
                    ("qrc", "real_orthogonal"),
                    ("qrc", "random_fourier"),
                    ("real_orthogonal", "random_fourier"),
                ):
                    cka_rows.append(
                        {
                            "base": base,
                            "task": task,
                            "split_seed": split_seed,
                            "left": left,
                            "right": right,
                            "linear_cka": _linear_cka(
                                standardized_test[left],
                                standardized_test[right],
                            ),
                        }
                    )
    return pd.DataFrame(feature_rows), pd.DataFrame(cka_rows)


def _summaries(
    features: pd.DataFrame,
    cka: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    feature_summary = (
        features.groupby(["base", "family"], as_index=False)
        .agg(
            train_effective_rank_mean=("train_effective_rank", "mean"),
            train_effective_rank_sd=("train_effective_rank", "std"),
            train_condition_mean=("train_condition_number", "mean"),
            test_effective_rank_mean=("test_effective_rank", "mean"),
            test_effective_rank_sd=("test_effective_rank", "std"),
            test_condition_mean=("test_condition_number", "mean"),
        )
    )
    cka_summary = (
        cka.groupby(["base", "left", "right"], as_index=False)
        .agg(
            mean_cka=("linear_cka", "mean"),
            sd_cka=("linear_cka", "std"),
            min_cka=("linear_cka", "min"),
            max_cka=("linear_cka", "max"),
        )
    )
    return feature_summary, cka_summary


def _plot(
    features: pd.DataFrame,
    feature_summary: pd.DataFrame,
    cka_summary: pd.DataFrame,
) -> None:
    figure, axes = plt.subplots(1, 3, figsize=(10.4, 3.5))
    order = ("qrc", "real_orthogonal", "random_fourier")
    colors = {
        "qrc": "#8B1E3F",
        "real_orthogonal": "#1F4E79",
        "random_fourier": "#5B9BD5",
    }
    for family in order:
        subset = features[features["family"].eq(family)]
        axes[0].scatter(
            np.full(len(subset), order.index(family)),
            subset["test_effective_rank"],
            s=9,
            alpha=0.25,
            color=colors[family],
        )
        axes[1].scatter(
            np.full(len(subset), order.index(family)),
            np.log10(np.clip(subset["test_condition_number"], 1.0, None)),
            s=9,
            alpha=0.25,
            color=colors[family],
        )
    for axis in axes[:2]:
        axis.set_xticks(np.arange(3))
        axis.set_xticklabels(["QRC", "Orthogonal", "Fourier"], rotation=15)
        axis.grid(color="#E5E7EB", linewidth=0.6)
    axes[0].set_ylabel("Test effective rank")
    axes[1].set_ylabel("log10 test condition number")
    cka_plot = cka_summary.copy()
    cka_plot["pair"] = (
        cka_plot["left"].str.replace("_", " ")
        + "\nvs "
        + cka_plot["right"].str.replace("_", " ")
    )
    for base, marker in (("extra_trees", "o"), ("catboost", "s")):
        subset = cka_plot[cka_plot["base"].eq(base)]
        axes[2].scatter(
            np.arange(len(subset)),
            subset["mean_cka"],
            marker=marker,
            color="#4B5563",
            label=base.replace("_", " ").title(),
        )
    axes[2].set_xticks(np.arange(len(cka_plot)))
    axes[2].set_xticklabels(cka_plot["pair"], fontsize=5.5)
    axes[2].set_ylim(0.0, 1.05)
    axes[2].set_ylabel("Linear CKA")
    axes[2].grid(axis="y", color="#E5E7EB", linewidth=0.6)
    axes[2].legend(frameon=False, fontsize=7)
    figure.tight_layout()
    figure.savefig(OUTPUT_ROOT / "capacity_diagnostics.png", dpi=600)
    figure.savefig(
        OUTPUT_ROOT / "capacity_diagnostics.pdf",
        bbox_inches="tight",
    )
    plt.close(figure)


def analyze() -> dict[str, object]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    features, cka = _collect()
    feature_summary, cka_summary = _summaries(features, cka)
    features.to_csv(
        OUTPUT_ROOT / "features_by_run.csv",
        index=False,
        encoding="utf-8-sig",
    )
    cka.to_csv(
        OUTPUT_ROOT / "cka_by_run.csv",
        index=False,
        encoding="utf-8-sig",
    )
    feature_summary.to_csv(
        OUTPUT_ROOT / "feature_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    cka_summary.to_csv(
        OUTPUT_ROOT / "cka_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    _plot(features, feature_summary, cka_summary)
    result = {
        "status": "passed",
        "runs": int(len(features)),
        "tasks": len(TASK_BY_NAME),
        "bases": ["extra_trees", "catboost"],
        "split_seeds": list(SPLIT_SEEDS),
        "maps_per_family": len(MAP_SEEDS),
        "feature_summary": feature_summary.to_dict(orient="records"),
        "cka_summary": cka_summary.to_dict(orient="records"),
        "checks": [
            "all 220 task-base-split combinations processed",
            "effective rank computed after train-only scaling",
            "condition number computed on held-out test features",
            "linear CKA computed between five-map mean features",
        ],
    }
    write_json(OUTPUT_ROOT / "summary.json", result)
    return {
        "status": "passed",
        "runs": len(features),
        "feature_summary": feature_summary.to_dict(orient="records"),
        "cka_summary": cka_summary.to_dict(orient="records"),
    }


if __name__ == "__main__":
    print(json.dumps(analyze(), ensure_ascii=False, indent=2))
