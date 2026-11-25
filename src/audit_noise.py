from __future__ import annotations

import json

import numpy as np

from src.config import GATE_WEIGHTS, RESULTS_ROOT, TASK_BY_NAME
from src.data import write_json
from src.run_finite_shot import SENSITIVITY_TASKS
from src.run_noise import NOISE_LEVELS, OUTPUT_ROOT, SHOTS


def audit() -> dict[str, object]:
    expected = 2 * len(SENSITIVITY_TASKS) * 5
    paths = sorted(OUTPUT_ROOT.glob("*/*/split_*.json"))
    if len(paths) != expected:
        raise RuntimeError(f"Expected {expected} noise files, found {len(paths)}")
    failures = []
    rows = 0
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if len(payload["results"]) != len(NOISE_LEVELS):
            failures.append(f"{path}: wrong noise result count")
            continue
        for result in payload["results"]:
            rows += 1
            if result["shots"] != SHOTS:
                failures.append(f"{path}: shot count mismatch")
            if result["depolarizing_probability"] not in NOISE_LEVELS:
                failures.append(f"{path}: noise level mismatch")
            if result["metric"] != TASK_BY_NAME[payload["task"]].metric:
                failures.append(f"{path}: metric mismatch")
            if float(result["gate_qrc"]) not in GATE_WEIGHTS:
                failures.append(f"{path}: invalid gate")
            for key in (
                "valid_score",
                "test_score",
                "orth_gated_score",
                "base_score",
                "noisy_qrc_minus_orth_gated",
                "noisy_qrc_minus_base",
            ):
                if not np.isfinite(result[key]):
                    failures.append(f"{path}: non-finite {key}")
    if failures:
        raise RuntimeError("Noise audit failed:\n" + "\n".join(failures[:30]))
    summary = {
        "status": "passed",
        "files": len(paths),
        "noise_results": rows,
        "tasks": list(SENSITIVITY_TASKS),
        "noise_levels": list(NOISE_LEVELS),
        "shots": SHOTS,
        "noise_model": "independent single-qubit depolarizing; Z scaled by lambda, ZZ by lambda^2",
    }
    write_json(RESULTS_ROOT / "audit" / "noise_audit.json", summary)
    return summary


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))

