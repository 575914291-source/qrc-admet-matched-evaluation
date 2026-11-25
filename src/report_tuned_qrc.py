from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.config import RESULTS_ROOT, SPLIT_SEEDS
from src.fast_metrics import metric_value
from src.report import _bootstrap_delta, _holm, _permutation_delta
from src.run_finite_shot import SENSITIVITY_TASKS
from src.run_tuned_qrc import OUTPUT_ROOT


def build_report() -> None:
    rows = []
    selection_rows = []
    for base in ("extra_trees", "catboost"):
        for task_index, task in enumerate(SENSITIVITY_TASKS):
            paths = [
                OUTPUT_ROOT / base / task / f"split_{seed}.npz"
                for seed in SPLIT_SEEDS
            ]
            arrays = [np.load(path, allow_pickle=False) for path in paths]
            metadata = [
                json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
                for path in paths
            ]
            y = arrays[0]["y_test"]
            scaffold = arrays[0]["scaffold"].astype(str)
            for method, reference in (
                ("qrc_test", "orth_test"),
                ("qrc_test", "base_test"),
            ):
                method_predictions = [values[method] for values in arrays]
                reference_predictions = [values[reference] for values in arrays]
                metric_name = metadata[0]["metric"]
                signs = -1.0 if metric_name == "MAE" else 1.0
                per_seed = [
                    signs
                    * (
                        metric_value(metric_name, y, method_prediction)
                        - metric_value(metric_name, y, reference_prediction)
                    )
                    for method_prediction, reference_prediction in zip(
                        method_predictions, reference_predictions
                    )
                ]
                observed = float(np.mean(per_seed))
                bootstrap = _bootstrap_delta(
                    metric_name,
                    y,
                    method_predictions,
                    reference_predictions,
                    scaffold,
                    1000,
                    9100 + task_index + 20 * int(base == "catboost"),
                )
                p_value, _ = _permutation_delta(
                    metric_name,
                    y,
                    method_predictions,
                    reference_predictions,
                    scaffold,
                    observed,
                    1999,
                    9200 + task_index + 20 * int(base == "catboost"),
                )
                rows.append(
                    {
                        "base": base,
                        "task": task,
                        "metric": metric_name,
                        "method": method,
                        "reference": reference,
                        "effect": observed,
                        "ci_low": float(np.quantile(bootstrap, 0.025)),
                        "ci_high": float(np.quantile(bootstrap, 0.975)),
                        "positive_splits": int(sum(value > 0 for value in per_seed)),
                        "permutation_p": p_value,
                    }
                )
            for item in metadata:
                selection_rows.append(
                    {
                        "base": base,
                        "task": task,
                        "seed": item["split_seed"],
                        "qrc_candidate": item["qrc_candidate"],
                        "orth_candidate": item["orth_candidate"],
                    }
                )
    frame = pd.DataFrame(rows)
    frame["holm_p"] = np.nan
    for index in frame.groupby(["base", "method", "reference"]).groups.values():
        frame.loc[index, "holm_p"] = _holm(
            frame.loc[index, "permutation_p"].tolist()
        )
    frame.to_csv(OUTPUT_ROOT / "comparisons.csv", index=False, encoding="utf-8-sig")
    selection = pd.DataFrame(selection_rows)
    selection.to_csv(OUTPUT_ROOT / "selections.csv", index=False, encoding="utf-8-sig")
    counts = (
        selection.groupby(["base", "qrc_candidate"]).size().rename("count").reset_index()
    )
    counts.to_csv(OUTPUT_ROOT / "selection_frequency.csv", index=False, encoding="utf-8-sig")
    print(frame.to_string(index=False))
    print(selection.groupby(["base", "qrc_candidate"]).size())


if __name__ == "__main__":
    build_report()

