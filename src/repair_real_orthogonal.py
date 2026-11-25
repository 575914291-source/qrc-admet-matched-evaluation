from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

from src.config import BASES, SPLIT_SEEDS, TASK_BY_NAME
from src.data import load_task_frames, make_split, write_json
from src.modeling import (
    branch_predictions,
    latent_features,
    predictions_from_delta,
    score,
    select_gate,
)
from src.run_benchmark import _task_matrix, log, run_path


def repair_job(payload: tuple[str, str, int]) -> dict[str, object]:
    base, task, split_seed = payload
    path = run_path(base, task, split_seed)
    metadata_path = path.with_suffix(".json")
    if not path.exists() or not metadata_path.exists():
        raise FileNotFoundError(path)

    with np.load(path, allow_pickle=False) as values:
        arrays = {name: np.asarray(values[name]) for name in values.files}
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    spec = TASK_BY_NAME[task]
    frames = load_task_frames(task)
    train, valid, test = make_split(frames, split_seed)
    train_x = _task_matrix(base, train)
    valid_x = _task_matrix(base, valid)
    test_x = _task_matrix(base, test)
    train_latent, valid_latent, test_latent = latent_features(
        train_x, valid_x, test_x, seed=split_seed
    )
    branches, diagnostics = branch_predictions(
        kind=spec.kind,
        train_latent=train_latent,
        valid_latent=valid_latent,
        test_latent=test_latent,
        train_y=arrays["y_train"],
        oof_base=arrays["base_oof"],
    )
    family = "real_orthogonal"
    branch = branches[family]
    alpha, objective = select_gate(
        spec.kind,
        spec.metric,
        arrays["y_valid"],
        arrays["base_valid"],
        branch["valid_delta"],
    )
    arrays[f"valid_delta_maps_{family}"] = branch["valid_delta_maps"]
    arrays[f"test_delta_maps_{family}"] = branch["test_delta_maps"]
    arrays[f"valid_delta_{family}"] = branch["valid_delta"]
    arrays[f"test_delta_{family}"] = branch["test_delta"]
    for state, weight in (("ungated", 1.0), ("gated", alpha)):
        valid_prediction = predictions_from_delta(
            spec.kind, arrays["base_valid"], branch["valid_delta"], weight
        )
        test_prediction = predictions_from_delta(
            spec.kind, arrays["base_test"], branch["test_delta"], weight
        )
        arrays[f"valid_pred_{family}_{state}"] = valid_prediction
        arrays[f"test_pred_{family}_{state}"] = test_prediction
        metadata["method_scores"][f"{family}_{state}"] = {
            "valid": score(spec.metric, arrays["y_valid"], valid_prediction),
            "test": score(spec.metric, arrays["y_test"], test_prediction),
        }
    metadata["gate_weights"][family] = alpha
    metadata["method_scores"][f"{family}_gate_validation_objective"] = objective
    metadata["map_diagnostics"][family] = diagnostics[family]
    metadata["repair"] = "real-orthogonal readout multiplication repaired 2026-11-25"
    np.savez_compressed(path, **arrays)
    write_json(metadata_path, metadata)
    return {
        "base": base,
        "task": task,
        "split_seed": split_seed,
        "gate": alpha,
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
        futures = {pool.submit(repair_job, job): job for job in jobs}
        for future in as_completed(futures):
            result = future.result()
            completed += 1
            log(
                f"{completed}/{len(jobs)} repaired {result['base']} "
                f"{result['task']} seed={result['split_seed']} gate={result['gate']}"
            )
    log(f"repaired {len(jobs)} runs in {time.time() - started:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())

