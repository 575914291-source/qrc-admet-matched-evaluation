from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

from src.config import (
    BASES,
    GATE_WEIGHTS,
    RESULTS_ROOT,
    SPLIT_SEEDS,
    TASK_BY_NAME,
)
from src.data import write_json
from src.modeling import predictions_from_delta, score
from src.run_benchmark import log, run_path


def _validation_objective(
    kind: str,
    metric: str,
    truth: np.ndarray,
    base: np.ndarray,
    qrc: np.ndarray,
    orth: np.ndarray,
) -> tuple[float, float, float]:
    sign = -1.0 if metric == "MAE" else 1.0
    best: tuple[float, float, float] | None = None
    best_value = -np.inf
    for orth_weight in GATE_WEIGHTS:
        for qrc_weight in GATE_WEIGHTS:
            prediction = predictions_from_delta(
                kind,
                base,
                qrc_weight * qrc + orth_weight * orth,
                1.0,
            )
            value = sign * score(metric, truth, prediction)
            # Ties prefer the smaller total correction, then less QRC.
            key = (
                value,
                -(qrc_weight + orth_weight),
                -qrc_weight,
                -orth_weight,
            )
            if best is None or key > (
                best_value,
                -(best[0] + best[1]),
                -best[0],
                -best[1],
            ):
                best_value = value
                best = (qrc_weight, orth_weight, value)
    if best is None:
        raise RuntimeError("No combination weight selected")
    return best


def augment_job(payload: tuple[str, str, int]) -> dict[str, object]:
    base_name, task, split_seed = payload
    path = run_path(base_name, task, split_seed)
    metadata_path = path.with_suffix(".json")
    if not path.exists() or not metadata_path.exists():
        raise FileNotFoundError(path)
    with np.load(path, allow_pickle=False) as values:
        arrays = {name: np.asarray(values[name]) for name in values.files}
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    spec = TASK_BY_NAME[task]
    qrc_weight, orth_weight, _ = _validation_objective(
        spec.kind,
        spec.metric,
        arrays["y_valid"],
        arrays["base_valid"],
        arrays["valid_delta_qrc"],
        arrays["valid_delta_real_orthogonal"],
    )
    combined_valid_delta = (
        qrc_weight * arrays["valid_delta_qrc"]
        + orth_weight * arrays["valid_delta_real_orthogonal"]
    )
    combined_test_delta = (
        qrc_weight * arrays["test_delta_qrc"]
        + orth_weight * arrays["test_delta_real_orthogonal"]
    )
    valid_prediction = predictions_from_delta(
        spec.kind, arrays["base_valid"], combined_valid_delta, 1.0
    )
    test_prediction = predictions_from_delta(
        spec.kind, arrays["base_test"], combined_test_delta, 1.0
    )
    arrays["valid_pred_qrc_plus_orth"] = valid_prediction
    arrays["test_pred_qrc_plus_orth"] = test_prediction
    metadata.setdefault("gate_weights", {})["combination_qrc"] = qrc_weight
    metadata["gate_weights"]["combination_orthogonal"] = orth_weight
    metadata.setdefault("method_scores", {})["qrc_plus_orth"] = {
        "valid": score(spec.metric, arrays["y_valid"], valid_prediction),
        "test": score(spec.metric, arrays["y_test"], test_prediction),
    }
    metadata["combination_note"] = (
        "Joint QRC + real-orthogonal gate selected on validation over a 5x5 grid; "
        "ties prefer the smaller total correction."
    )
    np.savez_compressed(path, **arrays)
    write_json(metadata_path, metadata)
    return {
        "base": base_name,
        "task": task,
        "split_seed": split_seed,
        "qrc_weight": qrc_weight,
        "orth_weight": orth_weight,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    jobs = [
        (base, task, seed)
        for base in BASES
        for task in TASK_BY_NAME
        for seed in SPLIT_SEEDS
        if run_path(base, task, seed).exists()
    ]
    started = time.time()
    completed = 0
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(augment_job, job): job for job in jobs}
        for future in as_completed(futures):
            result = future.result()
            completed += 1
            log(
                f"{completed}/{len(jobs)} combined {result['base']} {result['task']} "
                f"seed={result['split_seed']} w_qrc={result['qrc_weight']} "
                f"w_orth={result['orth_weight']}"
            )
    log(f"completed {len(jobs)} joint-gate jobs in {time.time() - started:.1f}s")
    write_json(
        RESULTS_ROOT / "combination" / "manifest.json",
        {
            "runs": len(jobs),
            "qrc_weights": list(GATE_WEIGHTS),
            "orthogonal_weights": list(GATE_WEIGHTS),
            "selection": "validation; ties prefer smaller total correction then less QRC",
        },
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

