from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import RESULTS_ROOT, SPLIT_SEEDS, TASK_BY_NAME
from src.data import write_json
from src.modeling import predictions_from_delta, score
from src.run_benchmark import run_path


OUTPUT_ROOT = RESULTS_ROOT / "map_selection"


def _orientation(metric: str) -> float:
    return -1.0 if metric == "MAE" else 1.0


def _selection_rows() -> pd.DataFrame:
    rows = []
    for base in ("extra_trees", "catboost"):
        for task in TASK_BY_NAME:
            spec = TASK_BY_NAME[task]
            for seed in SPLIT_SEEDS:
                path = run_path(base, task, seed)
                with np.load(path, allow_pickle=False) as archive:
                    values = {
                        name: np.asarray(archive[name])
                        for name in archive.files
                    }
                truth = values["y_test"]
                direction = _orientation(spec.metric)
                selected = {}
                for family in (
                    "qrc",
                    "real_orthogonal",
                    "random_fourier",
                ):
                    valid_scores = []
                    test_scores = []
                    for map_index in range(
                        values[f"valid_delta_maps_{family}"].shape[1]
                    ):
                        valid_prediction = predictions_from_delta(
                            spec.kind,
                            values["base_valid"],
                            values[f"valid_delta_maps_{family}"][:, map_index],
                            1.0,
                        )
                        test_prediction = predictions_from_delta(
                            spec.kind,
                            values["base_test"],
                            values[f"test_delta_maps_{family}"][:, map_index],
                            1.0,
                        )
                        valid_scores.append(
                            score(spec.metric, values["y_valid"], valid_prediction)
                        )
                        test_scores.append(
                            score(spec.metric, truth, test_prediction)
                        )
                    chosen = int(np.argmax(direction * np.asarray(valid_scores)))
                    mean_prediction = predictions_from_delta(
                        spec.kind,
                        values["base_test"],
                        values[f"test_delta_{family}"],
                        1.0,
                    )
                    mean_score = score(spec.metric, truth, mean_prediction)
                    selected[family] = {
                        "selected_map_index": chosen,
                        "selected_test": test_scores[chosen],
                        "mean_test": mean_score,
                        "oracle_test": max(
                            test_scores,
                            key=lambda value: direction * value,
                        ),
                    }
                rows.append(
                    {
                        "base": base,
                        "task": task,
                        "metric": spec.metric,
                        "split_seed": seed,
                        **{
                            f"{family}_{key}": value
                            for family, family_values in selected.items()
                            for key, value in family_values.items()
                        },
                        "qrc_selected_minus_orth_selected": (
                            direction
                            * (
                                selected["qrc"]["selected_test"]
                                - selected["real_orthogonal"]["selected_test"]
                            )
                        ),
                        "qrc_selected_minus_qrc_mean": (
                            direction
                            * (
                                selected["qrc"]["selected_test"]
                                - selected["qrc"]["mean_test"]
                            )
                        ),
                        "orth_selected_minus_orth_mean": (
                            direction
                            * (
                                selected["real_orthogonal"]["selected_test"]
                                - selected["real_orthogonal"]["mean_test"]
                            )
                        ),
                    }
                )
    return pd.DataFrame(rows)


def _summary(rows: pd.DataFrame) -> pd.DataFrame:
    records = []
    for (base, task), group in rows.groupby(["base", "task"]):
        records.append(
            {
                "base": base,
                "task": task,
                "metric": str(group["metric"].iloc[0]),
                "n_splits": int(len(group)),
                "qrc_selected_minus_mean": float(
                    group["qrc_selected_minus_qrc_mean"].mean()
                ),
                "qrc_selection_positive_splits": int(
                    (group["qrc_selected_minus_qrc_mean"] > 0).sum()
                ),
                "orth_selected_minus_mean": float(
                    group["orth_selected_minus_orth_mean"].mean()
                ),
                "orth_selection_positive_splits": int(
                    (group["orth_selected_minus_orth_mean"] > 0).sum()
                ),
                "qrc_selected_vs_orth_selected": float(
                    group["qrc_selected_minus_orth_selected"].mean()
                ),
                "qrc_selected_vs_orth_positive_splits": int(
                    (group["qrc_selected_minus_orth_selected"] > 0).sum()
                ),
            }
        )
    return pd.DataFrame(records).sort_values(["base", "task"])


def _plot(summary: pd.DataFrame) -> None:
    pivot = summary.pivot(
        index="task",
        columns="base",
        values="qrc_selected_vs_orth_selected",
    )
    order = pivot.mean(axis=1).sort_values().index
    pivot = pivot.loc[order]
    figure, axis = plt.subplots(figsize=(7.2, 6.1))
    y = np.arange(len(pivot))
    height = 0.36
    axis.barh(
        y - height / 2,
        pivot["extra_trees"],
        height,
        color="#5B9BD5",
        label="ExtraTrees",
    )
    axis.barh(
        y + height / 2,
        pivot["catboost"],
        height,
        color="#8B1E3F",
        label="CatBoost",
    )
    axis.axvline(0.0, color="#444444", linewidth=0.8)
    axis.set_yticks(y)
    axis.set_yticklabels(pivot.index, fontsize=7)
    axis.set_xlabel("Validation-selected QRC minus selected orthogonal effect")
    axis.set_title("Selection-aware test comparison across five maps")
    axis.grid(axis="x", color="#E5E7EB", linewidth=0.6)
    axis.legend(frameon=False, fontsize=8)
    figure.tight_layout()
    figure.savefig(OUTPUT_ROOT / "map_selection.png", dpi=600)
    figure.savefig(OUTPUT_ROOT / "map_selection.pdf", bbox_inches="tight")
    plt.close(figure)


def analyze() -> dict[str, object]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    rows = _selection_rows()
    summary = _summary(rows)
    rows.to_csv(
        OUTPUT_ROOT / "selection_by_split.csv",
        index=False,
        encoding="utf-8-sig",
    )
    summary.to_csv(
        OUTPUT_ROOT / "endpoint_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    _plot(summary)
    result = {
        "status": "passed",
        "runs": int(len(rows)),
        "maps_per_family": 5,
        "method": (
            "Select the best map on validation data, evaluate the selected "
            "map on the fixed test set, and compare it with the five-map mean "
            "and with selection-matched orthogonal control."
        ),
        "endpoint_counts": {
            base: {
                "qrc_selected_better_than_orth": int(
                    (
                        summary.loc[summary["base"].eq(base), "qrc_selected_vs_orth_selected"]
                        > 0
                    ).sum()
                ),
                "qrc_selected_better_than_qrc_mean": int(
                    (
                        summary.loc[summary["base"].eq(base), "qrc_selected_minus_mean"]
                        > 0
                    ).sum()
                ),
            }
            for base in ("extra_trees", "catboost")
        },
    }
    write_json(OUTPUT_ROOT / "summary.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(analyze(), ensure_ascii=False, indent=2))
