from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, log_loss, roc_auc_score

from src.config import RESULTS_ROOT, SPLIT_SEEDS
from src.data import write_json
from src.report import _bootstrap_delta
from src.run_external_validation import EXTERNAL_TASKS


OUTPUT_ROOT = RESULTS_ROOT / "external_diagnostics"
METHODS = {
    "base": "base",
    "qrc_gated": "qrc_gated",
    "orthogonal_gated": "orth_gated",
}
CONTRASTS = (
    ("qrc_gated", "base"),
    ("orthogonal_gated", "base"),
    ("qrc_gated", "orthogonal_gated"),
)
METRICS = ("AUROC", "AUPRC", "Brier", "LogLoss")
BOOTSTRAP_REPLICATES = 1000
CALIBRATION_BINS = 5


def _metric(metric: str, truth: np.ndarray, prediction: np.ndarray) -> float:
    prediction = np.asarray(prediction, dtype=float)
    if metric == "AUROC":
        return float(roc_auc_score(truth, prediction))
    if metric == "AUPRC":
        return float(average_precision_score(truth, prediction))
    if metric == "Brier":
        return float(np.mean((prediction - truth) ** 2))
    if metric == "LogLoss":
        return float(log_loss(truth, np.clip(prediction, 1e-7, 1 - 1e-7)))
    raise ValueError(metric)


def _better(metric: str, method: float, reference: float) -> float:
    return method - reference if metric in {"AUROC", "AUPRC"} else reference - method


def _calibration_curve(
    truth: np.ndarray,
    prediction: np.ndarray,
    bins: int,
) -> list[dict[str, float]]:
    order = np.argsort(prediction)
    rows = []
    for indices in np.array_split(order, bins):
        if len(indices) == 0:
            continue
        rows.append(
            {
                "mean_prediction": float(np.mean(prediction[indices])),
                "observed_rate": float(np.mean(truth[indices])),
                "n": float(len(indices)),
            }
        )
    return rows


def _calibration_slope(truth: np.ndarray, prediction: np.ndarray) -> tuple[float, float]:
    clipped = np.clip(prediction, 1e-6, 1 - 1e-6)
    logit = np.log(clipped / (1 - clipped)).reshape(-1, 1)
    model = LogisticRegression(
        penalty=None,
        solver="lbfgs",
        max_iter=1000,
    ).fit(logit, truth)
    return float(model.intercept_[0]), float(model.coef_[0, 0])


def build_external_diagnostics() -> dict[str, object]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    rows = []
    calibration_rows = []
    calibration_summary_rows = []
    for task_index, task in enumerate(EXTERNAL_TASKS):
        for base in ("extra_trees", "catboost"):
            runs = []
            for seed in SPLIT_SEEDS:
                path = (
                    RESULTS_ROOT
                    / "external_validation"
                    / base
                    / task
                    / f"split_{seed}.npz"
                )
                with np.load(path, allow_pickle=False) as archive:
                    runs.append(
                        {
                            name: np.asarray(archive[name])
                            for name in ("y", "scaffold", "base", "qrc_gated", "orth_gated")
                        }
                    )
            truth = runs[0]["y"].astype(int)
            scaffolds = runs[0]["scaffold"].astype(str)
            for contrast_index, (method, reference) in enumerate(CONTRASTS):
                methods = [run[METHODS[method]] for run in runs]
                references = [run[METHODS[reference]] for run in runs]
                for metric_index, metric in enumerate(METRICS):
                    per_seed = [
                        _better(
                            metric,
                            _metric(metric, truth, method_prediction),
                            _metric(metric, truth, reference_prediction),
                        )
                        for method_prediction, reference_prediction in zip(
                            methods,
                            references,
                            strict=True,
                        )
                    ]
                    if metric in {"AUROC", "AUPRC"}:
                        bootstrap = _bootstrap_delta(
                            metric,
                            truth,
                            methods,
                            references,
                            scaffolds,
                            BOOTSTRAP_REPLICATES,
                            50000
                            + 1000 * task_index
                            + 100 * int(base == "catboost")
                            + 10 * contrast_index
                            + metric_index,
                        )
                        ci_low = float(np.quantile(bootstrap, 0.025))
                        ci_high = float(np.quantile(bootstrap, 0.975))
                    else:
                        ci_low = np.nan
                        ci_high = np.nan
                    rows.append(
                        {
                            "task": task,
                            "base": base,
                            "method": method,
                            "reference": reference,
                            "metric": metric,
                            "n": int(len(truth)),
                            "n_positive": int(truth.sum()),
                            "prevalence": float(truth.mean()),
                            "effect_better_positive": float(np.mean(per_seed)),
                            "effect_seed_min": float(np.min(per_seed)),
                            "effect_seed_max": float(np.max(per_seed)),
                            "positive_seeds": int(sum(value > 0 for value in per_seed)),
                            "ci_low": ci_low,
                            "ci_high": ci_high,
                        }
                    )

            mean_predictions = {
                "qrc_gated": np.mean([run["qrc_gated"] for run in runs], axis=0),
                "orthogonal_gated": np.mean([run["orth_gated"] for run in runs], axis=0),
            }
            for method, prediction in mean_predictions.items():
                intercept, slope = _calibration_slope(truth, prediction)
                calibration_summary_rows.append(
                    {
                        "task": task,
                        "base": base,
                        "method": method,
                        "n": int(len(truth)),
                        "mean_prediction": float(np.mean(prediction)),
                        "observed_rate": float(np.mean(truth)),
                        "auroc": _metric("AUROC", truth, prediction),
                        "auprc": _metric("AUPRC", truth, prediction),
                        "brier": _metric("Brier", truth, prediction),
                        "log_loss": _metric("LogLoss", truth, prediction),
                        "calibration_intercept": intercept,
                        "calibration_slope": slope,
                    }
                )
                for bin_index, row in enumerate(
                    _calibration_curve(truth, prediction, CALIBRATION_BINS)
                ):
                    calibration_rows.append(
                        {
                            "task": task,
                            "base": base,
                            "method": method,
                            "bin": bin_index,
                            **row,
                        }
                    )

    summary = pd.DataFrame(rows)
    summary.to_csv(
        OUTPUT_ROOT / "summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    calibration_metrics = pd.DataFrame(calibration_summary_rows)
    calibration_metrics.to_csv(
        OUTPUT_ROOT / "calibration_metrics.csv",
        index=False,
        encoding="utf-8-sig",
    )
    calibration_curves = pd.DataFrame(calibration_rows)
    calibration_curves.to_csv(
        OUTPUT_ROOT / "calibration_curves.csv",
        index=False,
        encoding="utf-8-sig",
    )
    key_rows = summary[
        summary.metric.isin(["AUROC", "AUPRC", "Brier", "LogLoss"])
    ]
    result = {
        "purpose": (
            "Descriptive external-validation decomposition and calibration audit "
            "using existing binary-model predictions; no refitting or label-based "
            "model selection."
        ),
        "metrics": {
            "AUROC": "method minus reference; positive favors method",
            "AUPRC": "method minus reference; positive favors method",
            "Brier": "reference minus method; positive favors method",
            "LogLoss": "reference minus method; positive favors method",
        },
        "bootstrap": {
            "replicates": BOOTSTRAP_REPLICATES,
            "cluster": "Bemis-Murcko test scaffold",
        },
        "records": key_rows.astype(object)
        .where(pd.notna(key_rows), None)
        .to_dict(orient="records"),
    }
    write_json(OUTPUT_ROOT / "diagnostics.json", result)
    print(summary.to_string(index=False))
    print("\nCalibration metrics:")
    print(calibration_metrics.to_string(index=False))
    return result


if __name__ == "__main__":
    build_external_diagnostics()
