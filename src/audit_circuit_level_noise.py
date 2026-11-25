from __future__ import annotations

import json

import numpy as np

from src.config import CIRCUIT_TASKS, RESULTS_ROOT
from src.data import write_json


OUTPUT_ROOT = RESULTS_ROOT / "circuit_level_noise"


def audit() -> dict[str, object]:
    failures = []
    paths = [OUTPUT_ROOT / f"{task}.npz" for task in CIRCUIT_TASKS]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise RuntimeError(f"Missing circuit-noise files: {missing}")

    task_records = {}
    for path in paths:
        metadata = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        with np.load(path, allow_pickle=False) as values:
            arrays = {name: np.asarray(values[name]) for name in values.files}
        expected_shape = (5, 32, 15)
        for name in (
            "exact",
            "ideal_circuit",
            "noisy_low",
            "noisy_medium",
            "noisy_high",
        ):
            if arrays[name].shape != expected_shape:
                failures.append(f"{path}: wrong shape for {name}")
            if not np.isfinite(arrays[name]).all():
                failures.append(f"{path}: non-finite values in {name}")
            if np.any(arrays[name] < -1.000001) or np.any(
                arrays[name] > 1.000001
            ):
                failures.append(f"{path}: {name} outside [-1, 1]")
        ideal_rmse = float(
            np.sqrt(
                np.mean(
                    (arrays["ideal_circuit"] - arrays["exact"]) ** 2
                )
            )
        )
        if ideal_rmse > 0.01:
            failures.append(f"{path}: ideal circuit deviates too far from exact")
        task_records[str(metadata["task"])] = {
            "ideal_circuit_rmse": ideal_rmse,
            "states": int(metadata["states"]),
            "maps": int(metadata["maps"]),
            "trotter_reps": int(metadata["trotter_reps"]),
        }

    if failures:
        raise RuntimeError(
            "Circuit-level noise audit failed:\n" + "\n".join(failures[:30])
        )
    result = {
        "status": "passed",
        "files": len(paths),
        "tasks": list(CIRCUIT_TASKS),
        "profiles": ["ideal", "low", "medium", "high"],
        "task_records": task_records,
        "checks": [
            "all exact and circuit feature arrays are finite",
            "all readouts remain bounded in [-1, 1]",
            "ideal Trotterized circuits reproduce matrix readouts",
            "five maps and 32 stratified test states are present per task",
        ],
        "scope": (
            "Density-matrix Aer simulation with depolarizing gate noise and "
            "analytic independent readout flips; no physical hardware."
        ),
    }
    write_json(RESULTS_ROOT / "audit" / "circuit_level_noise_audit.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
