from __future__ import annotations

import json

import numpy as np

from src.config import RESULTS_ROOT, SPLIT_SEEDS, TASK_BY_NAME
from src.data import write_json
from src.run_finite_shot import SENSITIVITY_TASKS
from src.run_tuned_qrc import OUTPUT_ROOT


def audit() -> dict[str, object]:
    expected = 2 * len(SENSITIVITY_TASKS) * len(SPLIT_SEEDS)
    paths = sorted(OUTPUT_ROOT.glob("*/*/split_*.npz"))
    if len(paths) != expected:
        raise RuntimeError(f"Expected {expected} tuned runs, found {len(paths)}")
    failures = []
    for path in paths:
        metadata = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        spec = TASK_BY_NAME[metadata["task"]]
        with np.load(path, allow_pickle=False) as values:
            arrays = {name: np.asarray(values[name]) for name in values.files}
        y = arrays["y_test"]
        if set(np.unique(y).astype(int)) != {0, 1} if spec.binary else False:
            failures.append(f"{path}: invalid test labels")
        for name in ("qrc_test", "orth_test", "base_test"):
            prediction = arrays[name]
            if not np.isfinite(prediction).all():
                failures.append(f"{path}: non-finite {name}")
            if spec.binary and np.any((prediction < 0) | (prediction > 1)):
                failures.append(f"{path}: {name} outside [0, 1]")
    if failures:
        raise RuntimeError("Tuned-QRC audit failed:\n" + "\n".join(failures[:30]))
    result = {
        "status": "passed",
        "runs": len(paths),
        "tasks": list(SENSITIVITY_TASKS),
        "split_seeds": list(SPLIT_SEEDS),
        "qrc_parameter_configs": 5,
        "orthogonal_candidate_groups": 5,
        "maps_per_candidate": 5,
    }
    write_json(RESULTS_ROOT / "audit" / "tuned_qrc_audit.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))

