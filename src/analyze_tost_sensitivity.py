from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.config import BASES, RESULTS_ROOT, TASK_BY_NAME
from src.data import write_json
from src.fast_metrics import metric_value
from src.report import _bootstrap_delta, _holm, load_runs


OUTPUT_ROOT = RESULTS_ROOT / "report"
REPLICATES = 1000
MARGIN_FACTORS = (
    ("tight", 0.005, 0.01),
    ("primary", 0.01, 0.02),
    ("wide", 0.02, 0.04),
)


def build_tost_sensitivity() -> dict[str, object]:
    runs = {
        (str(metadata["base"]), str(metadata["task"]), int(metadata["split_seed"])): (
            arrays,
            metadata,
        )
        for _, arrays, metadata in load_runs()
    }
    rows = []
    for base_index, base in enumerate(BASES):
        for task_index, task in enumerate(TASK_BY_NAME):
            seeds = sorted(
                seed for candidate_base, candidate_task, seed in runs
                if candidate_base == base and candidate_task == task
            )
            arrays, metadata = runs[(base, task, seeds[0])]
            metric = str(metadata["metric"])
            truth = arrays["y_test"]
            scaffolds = arrays["test_scaffold"].astype(str)
            method_predictions = [
                runs[(base, task, seed)][0]["test_pred_qrc_ungated"]
                for seed in seeds
            ]
            reference_predictions = [
                runs[(base, task, seed)][0][
                    "test_pred_real_orthogonal_ungated"
                ]
                for seed in seeds
            ]
            bootstrap = _bootstrap_delta(
                metric,
                truth,
                method_predictions,
                reference_predictions,
                scaffolds,
                REPLICATES,
                60000 + 100 * base_index + task_index,
            )
            base_scores = [
                metric_value(
                    metric,
                    runs[(base, task, seed)][0]["y_test"],
                    runs[(base, task, seed)][0]["base_test"],
                )
                for seed in seeds
            ]
            for label, absolute_margin, mae_factor in MARGIN_FACTORS:
                margin = (
                    float(np.mean(base_scores) * mae_factor)
                    if metric == "MAE"
                    else absolute_margin
                )
                p_lower = (1 + np.sum(bootstrap <= -margin)) / (
                    len(bootstrap) + 1
                )
                p_upper = (1 + np.sum(bootstrap >= margin)) / (
                    len(bootstrap) + 1
                )
                rows.append(
                    {
                        "base": base,
                        "task": task,
                        "metric": metric,
                        "margin_label": label,
                        "margin": margin,
                        "equivalence_p": float(max(p_lower, p_upper)),
                    }
                )
    frame = pd.DataFrame(rows)
    frame["holm_equivalence_p"] = np.nan
    for (base, margin_label), index in frame.groupby(
        ["base", "margin_label"]
    ).groups.items():
        frame.loc[index, "holm_equivalence_p"] = _holm(
            frame.loc[index, "equivalence_p"].tolist()
        )
    frame["equivalent"] = frame.holm_equivalence_p < 0.05
    frame.to_csv(
        OUTPUT_ROOT / "tost_sensitivity.csv",
        index=False,
        encoding="utf-8-sig",
    )
    summary = (
        frame.groupby(["base", "margin_label"], as_index=False)
        .agg(
            equivalent_endpoints=("equivalent", "sum"),
            endpoints=("task", "count"),
        )
    )
    summary.to_csv(
        OUTPUT_ROOT / "tost_sensitivity_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    result = {
        "replicates": REPLICATES,
        "margin_definitions": {
            "absolute": {"tight": 0.005, "primary": 0.01, "wide": 0.02},
            "MAE_relative": {"tight": 0.01, "primary": 0.02, "wide": 0.04},
        },
        "summary": summary.to_dict(orient="records"),
    }
    write_json(OUTPUT_ROOT / "tost_sensitivity.json", result)
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    build_tost_sensitivity()
