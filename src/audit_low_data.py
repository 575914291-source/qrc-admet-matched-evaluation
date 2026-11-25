from __future__ import annotations

import json

import numpy as np

from src.config import GATE_WEIGHTS, RESULTS_ROOT, TASK_BY_NAME
from src.data import write_json
from src.run_low_data import FRACTIONS, OUTPUT_ROOT, PANEL


def audit() -> dict[str, object]:
    expected_files = 2 * len(PANEL) * 5
    paths = sorted(OUTPUT_ROOT.glob("*/*/split_*.json"))
    if len(paths) != expected_files:
        raise RuntimeError(
            f"Expected {expected_files} low-data files, found {len(paths)}"
        )
    failures = []
    result_count = 0
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        spec = TASK_BY_NAME[payload["task"]]
        if len(payload["results"]) != len(FRACTIONS):
            failures.append(f"{path}: wrong fraction count")
            continue
        seen = []
        for result in payload["results"]:
            result_count += 1
            seen.append(float(result["target_fraction"]))
            if not 0 < result["n_train"] <= result["full_train_n"]:
                failures.append(f"{path}: invalid training size")
            if result["metric"] != spec.metric:
                failures.append(f"{path}: metric mismatch")
            for key in (
                "qrc_ungated",
                "real_orthogonal_ungated",
                "random_fourier_ungated",
                "qrc_gated",
                "real_orthogonal_gated",
                "random_fourier_gated",
                "qrc_plus_orth",
                "qrc_minus_orth_ungated",
                "qrc_minus_orth_gated",
            ):
                if not np.isfinite(result[key]):
                    failures.append(f"{path}: non-finite {key}")
            if float(result["gate_qrc"]) not in GATE_WEIGHTS:
                failures.append(f"{path}: invalid QRC gate")
            direction = -1.0 if spec.metric == "MAE" else 1.0
            expected = direction * (
                result["qrc_ungated"] - result["real_orthogonal_ungated"]
            )
            if not np.isclose(expected, result["qrc_minus_orth_ungated"], atol=1e-10):
                failures.append(f"{path}: QRC-minus-orth cannot be reproduced")
        if sorted(seen) != sorted(FRACTIONS):
            failures.append(f"{path}: wrong target fractions")
    if failures:
        raise RuntimeError("Low-data audit failed:\n" + "\n".join(failures[:30]))
    summary = {
        "status": "passed",
        "files": len(paths),
        "fraction_results": result_count,
        "tasks": list(PANEL),
        "fractions": list(FRACTIONS),
        "minimum_subset": 96,
    }
    write_json(RESULTS_ROOT / "audit" / "low_data_audit.json", summary)
    return summary


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))

