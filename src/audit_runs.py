from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from src.config import (
    BASES,
    FAMILIES,
    GATE_WEIGHTS,
    RESULTS_ROOT,
    SPLIT_SEEDS,
    TASK_BY_NAME,
)
from src.data import load_task_frames, write_json
from src.modeling import score
from src.run_benchmark import run_path


def audit_runs() -> dict[str, object]:
    expected = [
        (base, task, seed)
        for base in BASES
        for task in TASK_BY_NAME
        for seed in SPLIT_SEEDS
    ]
    missing = [item for item in expected if not run_path(*item).exists()]
    if missing:
        raise RuntimeError(f"Missing run files: {missing[:10]} ({len(missing)} total)")

    references: dict[tuple[str, int], tuple[np.ndarray, np.ndarray]] = {}
    failures = []
    checked = 0
    for base, task, seed in expected:
        path = run_path(base, task, seed)
        metadata_path = path.with_suffix(".json")
        if not metadata_path.exists():
            failures.append(f"{base}/{task}/{seed}: missing metadata")
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        with np.load(path, allow_pickle=False) as values:
            arrays = {name: np.asarray(values[name]) for name in values.files}
        spec = TASK_BY_NAME[task]
        n_train = len(arrays["y_train"])
        n_valid = len(arrays["y_valid"])
        n_test = len(arrays["y_test"])
        if not (n_train + n_valid == metadata["n_train"] + metadata["n_valid"]):
            failures.append(f"{base}/{task}/{seed}: split size mismatch")
        if n_test != metadata["n_test"]:
            failures.append(f"{base}/{task}/{seed}: test size mismatch")
        official_test = load_task_frames(task).test
        if not np.array_equal(arrays["y_test"], official_test["Y"].to_numpy(dtype=float)):
            failures.append(f"{base}/{task}/{seed}: test labels do not align")
        if not np.array_equal(
            arrays["test_source_row"], np.arange(len(official_test), dtype=np.int64)
        ):
            failures.append(f"{base}/{task}/{seed}: test row order changed")

        key = (task, seed)
        split_signature = (
            arrays["train_source_row"],
            arrays["valid_source_row"],
        )
        if key not in references:
            references[key] = split_signature
        elif not (
            np.array_equal(references[key][0], split_signature[0])
            and np.array_equal(references[key][1], split_signature[1])
        ):
            failures.append(f"{base}/{task}/{seed}: base models use different splits")

        prediction_names = [
            "base_valid",
            "base_test",
            "base_oof",
            "test_pred_qrc_ungated",
            "test_pred_qrc_gated",
            "test_pred_real_orthogonal_ungated",
            "test_pred_real_orthogonal_gated",
            "test_pred_random_fourier_ungated",
            "test_pred_random_fourier_gated",
            "test_pred_qrc_plus_orth",
            "valid_pred_qrc_plus_orth",
        ]
        for name in prediction_names:
            if not np.isfinite(arrays[name]).all():
                failures.append(f"{base}/{task}/{seed}: {name} is not finite")
        if spec.binary:
            probability_names = [
                "base_valid",
                "base_test",
                "test_pred_qrc_ungated",
                "test_pred_qrc_gated",
                "test_pred_real_orthogonal_ungated",
                "test_pred_real_orthogonal_gated",
                "test_pred_random_fourier_ungated",
                "test_pred_random_fourier_gated",
                "test_pred_qrc_plus_orth",
            ]
            for name in probability_names:
                values = arrays[name]
                if np.any((values < 0) | (values > 1)):
                    failures.append(f"{base}/{task}/{seed}: {name} outside [0, 1]")
        for family in FAMILIES:
            if arrays[f"test_delta_maps_{family}"].shape != (n_test, 5):
                failures.append(f"{base}/{task}/{seed}: wrong map shape for {family}")
            weight = float(metadata["gate_weights"][family])
            if weight not in GATE_WEIGHTS:
                failures.append(f"{base}/{task}/{seed}: invalid gate weight {weight}")
        for key in ("combination_qrc", "combination_orthogonal"):
            if float(metadata["gate_weights"].get(key, -1)) not in GATE_WEIGHTS:
                failures.append(f"{base}/{task}/{seed}: invalid {key}")
        recomputed = score(spec.metric, arrays["y_test"], arrays["base_test"])
        if not np.isclose(
            recomputed,
            metadata["base_test_score"],
            rtol=0,
            atol=1e-10,
        ):
            failures.append(f"{base}/{task}/{seed}: base metric cannot be reproduced")
        checked += 1

    if failures:
        raise RuntimeError("Run audit failed:\n" + "\n".join(failures[:30]))
    result = {
        "status": "passed",
        "checked_runs": checked,
        "expected_runs": len(expected),
        "bases": list(BASES),
        "tasks": len(TASK_BY_NAME),
        "split_seeds": list(SPLIT_SEEDS),
        "families": list(FAMILIES),
        "official_test_rows": sum(
            len(load_task_frames(task).test) for task in TASK_BY_NAME
        ),
        "checks": [
            "all run files present",
            "official test labels and row order preserved",
            "one split shared by all bases",
            "finite predictions",
            "classification probabilities bounded",
            "five random maps per family",
            "gate weights from the fixed grid",
            "base metrics independently recomputed",
        ],
    }
    write_json(RESULTS_ROOT / "audit" / "runs_audit.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(audit_runs(), ensure_ascii=False, indent=2))

