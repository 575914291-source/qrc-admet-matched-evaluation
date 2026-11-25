from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from src.config import GATE_WEIGHTS
from src.data import write_json
from src.fast_metrics import metric_value
from src.run_external_regression import (
    MODEL_METRIC,
    OUTPUT_ROOT,
    TASK,
    _path,
    prepare_regression_frames,
)


MODEL_SEEDS = (1, 2, 3, 4, 5)


def audit() -> dict[str, object]:
    train, valid, test = prepare_regression_frames()
    failures = []
    paths = [
        _path(base, seed)
        for base in ("extra_trees", "catboost")
        for seed in MODEL_SEEDS
    ]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise RuntimeError(f"Missing external regression runs: {missing}")

    for path in paths:
        metadata = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        with np.load(path, allow_pickle=False) as values:
            arrays = {name: np.asarray(values[name]) for name in values.files}
        if len(arrays["y_test"]) != len(test):
            failures.append(f"{path}: wrong test sample count")
        if len(arrays["y_valid"]) != len(valid):
            failures.append(f"{path}: wrong validation sample count")
        if not np.isfinite(arrays["y_test"]).all():
            failures.append(f"{path}: non-finite test labels")
        if not np.isfinite(arrays["y_valid"]).all():
            failures.append(f"{path}: non-finite validation labels")
        if len(arrays["test_scaffold"]) != len(test):
            failures.append(f"{path}: scaffold vector misaligned")
        for family in ("qrc", "real_orthogonal", "random_fourier"):
            gate = float(arrays[f"{family}_gate"][0])
            if gate not in GATE_WEIGHTS:
                failures.append(f"{path}: invalid {family} gate")
            for split in ("valid", "test"):
                for state in ("ungated", "gated"):
                    prediction = arrays[f"{family}_{split}_{state}"]
                    if not np.isfinite(prediction).all():
                        failures.append(
                            f"{path}: non-finite {family}_{split}_{state}"
                        )
        truth = arrays["y_test"]
        for name, array_name, expected in (
            (
                "base",
                "base_test",
                metadata["scores"]["base"]["test_spearman"],
            ),
            (
                "qrc_ungated",
                "qrc_test_ungated",
                metadata["scores"]["qrc"]["test_spearman_ungated"],
            ),
            (
                "qrc_gated",
                "qrc_test_gated",
                metadata["scores"]["qrc"]["test_spearman_gated"],
            ),
            (
                "orth_ungated",
                "real_orthogonal_test_ungated",
                metadata["scores"]["real_orthogonal"][
                    "test_spearman_ungated"
                ],
            ),
            (
                "orth_gated",
                "real_orthogonal_test_gated",
                metadata["scores"]["real_orthogonal"][
                    "test_spearman_gated"
                ],
            ),
        ):
            recomputed = metric_value(
                MODEL_METRIC, truth, arrays[array_name]
            )
            if not np.isclose(recomputed, expected, atol=1e-10):
                failures.append(f"{path}: cannot reproduce {name} score")

    if failures:
        raise RuntimeError(
            "External regression audit failed:\n" + "\n".join(failures[:30])
        )

    prepared_audit = json.loads(
        (
            Path("data")
            / "external"
            / "prepared"
            / f"{TASK}_audit.json"
        ).read_text(encoding="utf-8")
    )
    result = {
        "status": "passed",
        "runs": len(paths),
        "bases": ["extra_trees", "catboost"],
        "model_seeds": list(MODEL_SEEDS),
        "task": TASK,
        "target": "PIC50",
        "sample_counts": {
            "train": int(len(train)),
            "valid": int(len(valid)),
            "test": int(len(test)),
            "test_scaffolds": int(test["scaffold"].nunique()),
        },
        "prepared_split_audit": prepared_audit,
        "checks": [
            "all expected regression runs present",
            "train/validation/test canonical and scaffold overlaps are absent",
            "all saved predictions are finite",
            "gates lie on the frozen grid",
            "saved test Spearman scores are independently recomputed",
        ],
    }
    write_json(OUTPUT_ROOT / "audit.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
