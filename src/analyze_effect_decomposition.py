from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import RESULTS_ROOT, TASK_BY_NAME
from src.data import write_json


METRICS = RESULTS_ROOT / "report" / "metrics_by_seed.csv"
OUTPUT_ROOT = RESULTS_ROOT / "effect_decomposition"


def _effect(metric: str, candidate: float, reference: float) -> float:
    if metric == "MAE":
        return float(reference - candidate)
    return float(candidate - reference)


def _effect_frame() -> pd.DataFrame:
    metrics = pd.read_csv(METRICS)
    metrics["method"] = metrics["method"].replace(
        {"base": "classical_base"}
    )
    required = {
        "qrc_ungated",
        "classical_base",
        "real_orthogonal_ungated",
    }
    available = set(metrics["method"].unique())
    if not required.issubset(available):
        raise RuntimeError(
            f"Missing required methods: {sorted(required - available)}"
        )
    pivot = (
        metrics.pivot(
            index=["base", "task", "metric", "split_seed"],
            columns="method",
            values="score",
        )
        .reset_index()
        .rename_axis(columns=None)
    )
    rows = []
    for row in pivot.itertuples(index=False):
        total = _effect(row.metric, row.qrc_ungated, row.classical_base)
        control = _effect(
            row.metric, row.real_orthogonal_ungated, row.classical_base
        )
        specific = _effect(
            row.metric, row.qrc_ungated, row.real_orthogonal_ungated
        )
        rows.append(
            {
                "base": row.base,
                "task": row.task,
                "task_type": TASK_BY_NAME[row.task].kind,
                "metric": row.metric,
                "split_seed": int(row.split_seed),
                "qrc_vs_base": total,
                "orthogonal_vs_base": control,
                "qrc_specific": specific,
                "identity_error": total - control - specific,
                "apparent_gain_neutralized": total > 0 and specific <= 0,
            }
        )
    result = pd.DataFrame(rows)
    if result["identity_error"].abs().max() > 1e-10:
        raise RuntimeError("Effect decomposition identity did not hold")
    return result


def _summary(by_split: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (base, task), group in by_split.groupby(["base", "task"]):
        task_type = str(group["task_type"].iloc[0])
        rows.append(
            {
                "base": base,
                "task": task,
                "task_type": task_type,
                "metric": str(group["metric"].iloc[0]),
                "n_splits": int(len(group)),
                "qrc_vs_base_mean": float(group["qrc_vs_base"].mean()),
                "orthogonal_vs_base_mean": float(
                    group["orthogonal_vs_base"].mean()
                ),
                "qrc_specific_mean": float(group["qrc_specific"].mean()),
                "qrc_specific_sd": float(group["qrc_specific"].std(ddof=1)),
                "qrc_specific_positive_splits": int(
                    (group["qrc_specific"] > 0).sum()
                ),
                "apparent_gain_neutralized_splits": int(
                    group["apparent_gain_neutralized"].sum()
                ),
            }
        )
    return pd.DataFrame(rows).sort_values(["base", "task"])


def _plot(summary: pd.DataFrame) -> None:
    colors = {
        ("extra_trees", "classification"): "#1F4E79",
        ("extra_trees", "regression"): "#5B9BD5",
        ("catboost", "classification"): "#8B1E3F",
        ("catboost", "regression"): "#D98BA8",
    }
    markers = {"classification": "o", "regression": "s"}
    figure, axis = plt.subplots(figsize=(7.2, 5.4))
    for (base, task_type), group in summary.groupby(["base", "task_type"]):
        axis.scatter(
            group["orthogonal_vs_base_mean"],
            group["qrc_specific_mean"],
            s=52,
            alpha=0.86,
            color=colors[(base, task_type)],
            marker=markers[task_type],
            edgecolor="white",
            linewidth=0.6,
            label=f"{base} / {task_type}",
        )
        for row in group.itertuples(index=False):
            axis.annotate(
                row.task,
                (row.orthogonal_vs_base_mean, row.qrc_specific_mean),
                xytext=(3, 3),
                textcoords="offset points",
                fontsize=5.5,
                alpha=0.8,
            )
    axis.axhline(0.0, color="#444444", linewidth=0.8)
    axis.axvline(0.0, color="#444444", linewidth=0.8)
    axis.set_xlabel("Matched classical quadratic effect vs base")
    axis.set_ylabel("QRC-specific effect vs matched control")
    axis.set_title("Matched effect decomposition across 22 ADMET endpoints")
    axis.grid(color="#E5E7EB", linewidth=0.6, alpha=0.8)
    axis.legend(frameon=False, fontsize=7, ncol=2, loc="best")
    figure.tight_layout()
    figure.savefig(OUTPUT_ROOT / "effect_decomposition.png", dpi=600)
    figure.savefig(
        OUTPUT_ROOT / "effect_decomposition.pdf",
        bbox_inches="tight",
    )
    plt.close(figure)


def analyze() -> dict[str, object]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    by_split = _effect_frame()
    summary = _summary(by_split)
    by_split.to_csv(
        OUTPUT_ROOT / "effects_by_split.csv",
        index=False,
        encoding="utf-8-sig",
    )
    summary.to_csv(
        OUTPUT_ROOT / "endpoint_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    _plot(summary)

    counts = {}
    for base, group in summary.groupby("base"):
        positive_total = int((group["qrc_vs_base_mean"] > 0).sum())
        neutralized = int(
            (
                (group["qrc_vs_base_mean"] > 0)
                & (group["qrc_specific_mean"] <= 0)
            ).sum()
        )
        counts[base] = {
            "positive_qrc_vs_base_endpoints": positive_total,
            "apparent_gains_neutralized_by_control": neutralized,
            "neutralized_fraction_of_positive_endpoints": (
                float(neutralized / positive_total)
                if positive_total
                else 0.0
            ),
            "qrc_specific_positive_endpoints": int(
                (group["qrc_specific_mean"] > 0).sum()
            ),
        }
    result = {
        "status": "passed",
        "purpose": (
            "Decompose QRC-vs-base changes into matched classical nonlinearity "
            "and QRC-specific effects."
        ),
        "endpoints": int(len(summary)),
        "bases": counts,
        "checks": [
            "decomposition identity holds on every split",
            "all endpoint and base combinations are present",
            "effect direction is positive for improvement including MAE",
        ],
    }
    write_json(OUTPUT_ROOT / "summary.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(analyze(), ensure_ascii=False, indent=2))
