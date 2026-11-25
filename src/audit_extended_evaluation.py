from __future__ import annotations

import json

import pandas as pd

from src.config import RESULTS_ROOT
from src.data import write_json


def _read(path, **kwargs):
    return pd.read_csv(path, encoding="utf-8-sig", **kwargs)


def audit() -> dict[str, object]:
    calibration = _read(
        RESULTS_ROOT / "calibration" / "summary.csv",
        keep_default_na=False,
        na_values=[""],
    )
    decomposition = _read(
        RESULTS_ROOT / "effect_decomposition" / "effects_by_split.csv"
    )
    selection = json.loads(
        (
            RESULTS_ROOT / "map_selection" / "summary.json"
        ).read_text(encoding="utf-8")
    )
    capacity = _read(
        RESULTS_ROOT / "capacity_diagnostics" / "features_by_run.csv"
    )
    cka = _read(
        RESULTS_ROOT / "capacity_diagnostics" / "cka_by_run.csv"
    )
    source_gradient = _read(
        RESULTS_ROOT / "source_gradient" / "summary.csv"
    )

    failures = []
    if len(calibration) != 6:
        failures.append(f"Expected 6 calibration summaries, found {len(calibration)}")
    qrc_signal = calibration[calibration.scenario == "qrc_signal"]
    classical_signal = calibration[
        calibration.scenario == "classical_signal"
    ]
    null = calibration[calibration.scenario == "null"]
    if not (qrc_signal.qrc_minus_orthogonal_mean > 0).all():
        failures.append("Known-QRC calibration does not favour QRC")
    if not (qrc_signal.correct_selection_rate >= 0.90).all():
        failures.append("Known-QRC source recovery is below 90%")
    if not (classical_signal.qrc_minus_orthogonal_mean < 0).all():
        failures.append("Known-classical calibration does not favour control")
    if not (classical_signal.correct_selection_rate >= 0.90).all():
        failures.append("Known-classical source recovery is below 90%")
    if not (null.null_false_positive_rate <= 0.05).all():
        failures.append("Null calibration exceeds 5% false positives")

    if len(decomposition) != 220:
        failures.append(
            f"Expected 220 decomposition rows, found {len(decomposition)}"
        )
    if float(decomposition.identity_error.abs().max()) > 1e-10:
        failures.append("Effect decomposition identity failed")
    if selection.get("status") != "passed" or selection.get("runs") != 220:
        failures.append("Selection-aware analysis is incomplete")
    if len(capacity) != 3300:
        failures.append(f"Expected 3300 capacity rows, found {len(capacity)}")
    if capacity.task.nunique() != 22 or capacity.base.nunique() != 2:
        failures.append("Capacity analysis does not cover 22 tasks and 2 bases")
    if len(cka) != 660:
        failures.append(f"Expected 660 CKA rows, found {len(cka)}")
    if len(source_gradient) != 24:
        failures.append(
            f"Expected 24 source-gradient summaries, found {len(source_gradient)}"
        )
    if failures:
        raise RuntimeError(
            "Extended evaluation audit failed:\n" + "\n".join(failures)
        )
    result = {
        "status": "passed",
        "calibration_datasets": int(
            calibration["n"].astype(int).sum()
        ),
        "effect_decomposition_splits": int(len(decomposition)),
        "selection_aware_runs": int(selection["runs"]),
        "capacity_records": int(len(capacity)),
        "cka_records": int(len(cka)),
        "source_gradient_summaries": int(len(source_gradient)),
        "checks": [
            "known QRC and classical signals are recovered",
            "null false-positive rates are at or below 5%",
            "effect decomposition identity holds on all splits",
            "selection-aware analysis covers all 220 runs",
            "capacity diagnostics cover 22 tasks, 2 bases, 5 splits and 5 maps",
            "external source-gradient analysis covers all quartiles",
        ],
    }
    write_json(
        RESULTS_ROOT / "audit" / "extended_evaluation_audit.json",
        result,
    )
    return result


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
