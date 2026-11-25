from __future__ import annotations

import json

import numpy as np

from src.config import RESULTS_ROOT, SPLIT_SEEDS, TASK_BY_NAME
from src.data import write_json
from src.fast_metrics import metric_value
from src.run_external_validation import EXTERNAL_TASKS, output_path


def audit() -> dict[str, object]:
    expected = 2 * len(EXTERNAL_TASKS) * len(SPLIT_SEEDS)
    paths = [
        output_path(base, task, seed)
        for base in ("extra_trees", "catboost")
        for task in EXTERNAL_TASKS
        for seed in SPLIT_SEEDS
    ]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise RuntimeError(f"Missing external run files: {missing}")
    failures = []
    for path in paths:
        metadata = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        with np.load(path, allow_pickle=False) as values:
            arrays = {name: np.asarray(values[name]) for name in values.files}
        spec = TASK_BY_NAME[str(metadata["task"])]
        y = arrays["y"]
        if len(y) != metadata["n_external"]:
            failures.append(f"{path}: wrong sample count")
        if set(np.unique(y).astype(int)) != {0, 1}:
            failures.append(f"{path}: external labels are not binary")
        for name in (
            "base",
            "qrc_ungated",
            "orth_ungated",
            "qrc_gated",
            "orth_gated",
            "qrc_plus_orth",
        ):
            prediction = arrays[name]
            if not np.isfinite(prediction).all():
                failures.append(f"{path}: non-finite {name}")
            if np.any((prediction < 0) | (prediction > 1)):
                failures.append(f"{path}: {name} outside [0, 1]")
            recomputed = metric_value(spec.metric, y, prediction)
            if not np.isclose(recomputed, metadata["scores"][name], atol=1e-10):
                failures.append(f"{path}: cannot reproduce {name} score")
    if failures:
        raise RuntimeError("External audit failed:\n" + "\n".join(failures[:30]))
    result = {
        "status": "passed",
        "runs": len(paths),
        "tasks": list(EXTERNAL_TASKS),
        "split_seeds": list(SPLIT_SEEDS),
        "checks": [
            "external labels are binary",
            "all predictions finite and bounded",
            "all external metrics independently recomputed",
            "canonical overlap audit recorded by external_data",
        ],
    }
    write_json(RESULTS_ROOT / "audit" / "external_audit.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))

