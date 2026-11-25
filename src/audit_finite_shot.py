from __future__ import annotations

import json

import numpy as np

from src.config import GATE_WEIGHTS, RESULTS_ROOT, TASK_BY_NAME
from src.data import write_json
from src.run_finite_shot import OUTPUT_ROOT, SENSITIVITY_TASKS, SHOT_BUDGETS


def audit() -> dict[str, object]:
    expected = 2 * len(SENSITIVITY_TASKS) * 5
    paths = sorted(OUTPUT_ROOT.glob("*/*/split_*.json"))
    if len(paths) != expected:
        raise RuntimeError(f"Expected {expected} finite-shot files, found {len(paths)}")
    failures = []
    rows = 0
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        task = payload["task"]
        spec = TASK_BY_NAME[task]
        if len(payload["results"]) != len(SHOT_BUDGETS):
            failures.append(f"{path}: wrong shot-result count")
            continue
        observed_budgets = set()
        for result in payload["results"]:
            rows += 1
            observed_budgets.add(int(result["shots"]))
            if result["metric"] != spec.metric or result["kind"] != spec.kind:
                failures.append(f"{path}: metric/kind mismatch")
            if float(result["gate_qrc"]) not in GATE_WEIGHTS:
                failures.append(f"{path}: invalid gate")
            for key in (
                "valid_score",
                "test_score",
                "ideal_qrc_gated_score",
                "orth_gated_score",
                "base_score",
                "finite_minus_orth_gated",
                "finite_minus_base",
                "finite_minus_ideal_qrc_gated",
            ):
                if not np.isfinite(result[key]):
                    failures.append(f"{path}: non-finite {key}")
        if observed_budgets != set(SHOT_BUDGETS):
            failures.append(f"{path}: wrong shot budgets")
    if failures:
        raise RuntimeError("Finite-shot audit failed:\n" + "\n".join(failures[:30]))
    summary = {
        "status": "passed",
        "files": len(paths),
        "shot_results": rows,
        "tasks": list(SENSITIVITY_TASKS),
        "shot_budgets": list(SHOT_BUDGETS),
        "model": "independent binomial sampling per Pauli expectation",
        "hardware_noise_included": False,
    }
    write_json(RESULTS_ROOT / "audit" / "finite_shot_audit.json", summary)
    return summary


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))

