from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.config import RESULTS_ROOT, SPLIT_SEEDS
from src.fast_metrics import metric_value
from src.report import _bootstrap_delta, _holm, _permutation_delta
from src.run_external_validation import EXTERNAL_TASKS, OUTPUT_ROOT


REPORT_ROOT = RESULTS_ROOT / "external_validation"


def _run_path(base: str, task: str, seed: int):
    return OUTPUT_ROOT / base / task / f"split_{seed}.npz"


def _methods():
    return [
        ("qrc_ungated", "orth_ungated"),
        ("qrc_gated", "orth_gated"),
        ("qrc_plus_orth", "orth_gated"),
        ("qrc_ungated", "base"),
        ("qrc_plus_orth", "base"),
    ]


def build_report() -> None:
    rows = []
    effects = []
    for base in ("extra_trees", "catboost"):
        for task in EXTERNAL_TASKS:
            paths = [_run_path(base, task, seed) for seed in SPLIT_SEEDS]
            arrays = [np.load(path, allow_pickle=False) for path in paths]
            y = arrays[0]["y"]
            scaffold = arrays[0]["scaffold"].astype(str)
            for method, reference in _methods():
                method_predictions = [values[method] for values in arrays]
                reference_predictions = [values[reference] for values in arrays]
                per_seed = [
                    metric_value("AUROC", y, method) - metric_value("AUROC", y, reference)
                    for method, reference in zip(method_predictions, reference_predictions)
                ]
                observed = float(np.mean(per_seed))
                p_value, _ = _permutation_delta(
                    "AUROC",
                    y,
                    method_predictions,
                    reference_predictions,
                    scaffold,
                    observed,
                    999,
                    8100 + EXTERNAL_TASKS.index(task) + 10 * int(base == "catboost"),
                )
                bootstrap = _bootstrap_delta(
                    "AUROC",
                    y,
                    method_predictions,
                    reference_predictions,
                    scaffold,
                    1000,
                    8200 + EXTERNAL_TASKS.index(task),
                )
                rows.append(
                    {
                        "base": base,
                        "task": task,
                        "method": method,
                        "reference": reference,
                        "n_external": len(y),
                        "effect": observed,
                        "ci_low": float(np.quantile(bootstrap, 0.025)),
                        "ci_high": float(np.quantile(bootstrap, 0.975)),
                        "positive_splits": int(sum(value > 0 for value in per_seed)),
                        "permutation_p": p_value,
                    }
                )
                for seed, method_value in zip(SPLIT_SEEDS, per_seed):
                    effects.append(
                        {
                            "base": base,
                            "task": task,
                            "method": method,
                            "reference": reference,
                            "seed": seed,
                            "effect": method_value,
                        }
                    )
    frame = pd.DataFrame(rows)
    frame["holm_p"] = np.nan
    for (base, method, reference), index in frame.groupby(
        ["base", "method", "reference"]
    ).groups.items():
        frame.loc[index, "holm_p"] = _holm(frame.loc[index, "permutation_p"].tolist())
    frame.to_csv(
        REPORT_ROOT / "summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pd.DataFrame(effects).to_csv(
        REPORT_ROOT / "effects_by_seed.csv",
        index=False,
        encoding="utf-8-sig",
    )
    print(frame.to_string(index=False))


if __name__ == "__main__":
    build_report()

