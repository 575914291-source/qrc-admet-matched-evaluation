from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

from src.config import MAP_SEEDS, RESULTS_ROOT, SPLIT_SEEDS, TASK_BY_NAME
from src.data import load_task_frames, make_split, write_json
from src.modeling import (
    _fit_branch_delta,
    latent_features,
    predictions_from_delta,
    score,
    select_gate,
)
from src.reservoir import qrc_readouts, quadratic_features, real_orthogonal_readouts
from src.run_benchmark import _task_matrix, log, run_path
from src.run_finite_shot import SENSITIVITY_TASKS


QRC_CONFIGS = (
    {"name": "baseline", "field_x": 0.4, "field_z": 0.7, "coupling": 0.25, "time": 0.5},
    {"name": "weak", "field_x": 0.2, "field_z": 0.4, "coupling": 0.15, "time": 0.5},
    {"name": "strong", "field_x": 0.8, "field_z": 1.0, "coupling": 0.35, "time": 0.5},
    {"name": "short", "field_x": 0.4, "field_z": 0.7, "coupling": 0.25, "time": 0.25},
    {"name": "long", "field_x": 0.4, "field_z": 0.7, "coupling": 0.25, "time": 1.0},
)
ORTH_GROUPS = tuple(tuple(range(20261201 + 5 * group, 20261206 + 5 * group)) for group in range(5))
OUTPUT_ROOT = RESULTS_ROOT / "tuned_qrc"


def output_path(base: str, task: str, split_seed: int):
    return OUTPUT_ROOT / base / task / f"split_{split_seed}.npz"


def _fit_ensemble(
    kind: str,
    train_features: list[np.ndarray],
    valid_features: list[np.ndarray],
    test_features: list[np.ndarray],
    train_y: np.ndarray,
    train_offset: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    valid_deltas = []
    test_deltas = []
    for train_feature, valid_feature, test_feature in zip(
        train_features, valid_features, test_features
    ):
        valid_delta, test_delta = _fit_branch_delta(
            kind,
            train_feature,
            valid_feature,
            test_feature,
            train_y,
            train_offset,
        )
        valid_deltas.append(valid_delta)
        test_deltas.append(test_delta)
    return np.column_stack(valid_deltas).mean(axis=1), np.column_stack(test_deltas).mean(axis=1)


def run_job(payload: tuple[str, str, int]) -> dict[str, object]:
    base, task, split_seed = payload
    destination = output_path(base, task, split_seed)
    if destination.exists():
        return json.loads(destination.with_suffix(".json").read_text(encoding="utf-8"))
    spec = TASK_BY_NAME[task]
    train, valid, test = make_split(load_task_frames(task), split_seed)
    source = run_path(base, task, split_seed)
    with np.load(source, allow_pickle=False) as values:
        saved = {name: np.asarray(values[name]) for name in values.files}
    metadata = json.loads(source.with_suffix(".json").read_text(encoding="utf-8"))
    train_x = _task_matrix(base, train)
    valid_x = _task_matrix(base, valid)
    test_x = _task_matrix(base, test)
    train_latent, valid_latent, test_latent = latent_features(
        train_x, valid_x, test_x, seed=split_seed
    )
    offset = (
        np.log(np.clip(saved["base_oof"], 1e-7, 1 - 1e-7))
        - np.log(np.clip(1 - saved["base_oof"], 1e-7, 1 - 1e-7))
        if spec.binary
        else saved["base_oof"]
    )
    train_y = saved["y_train"]
    valid_y = saved["y_valid"]
    test_y = saved["y_test"]
    direction = -1.0 if spec.metric == "MAE" else 1.0

    candidates = []
    for config in QRC_CONFIGS:
        train_features = []
        valid_features = []
        test_features = []
        for seed in MAP_SEEDS:
            readout = qrc_readouts(
                seed,
                field_x=config["field_x"],
                field_z=config["field_z"],
                coupling=config["coupling"],
                evolution_time=config["time"],
            )
            train_features.append(quadratic_features(train_latent, readout))
            valid_features.append(quadratic_features(valid_latent, readout))
            test_features.append(quadratic_features(test_latent, readout))
        valid_delta, test_delta = _fit_ensemble(
            spec.kind,
            train_features,
            valid_features,
            test_features,
            train_y,
            offset,
        )
        gate, valid_objective = select_gate(
            spec.kind, spec.metric, valid_y, saved["base_valid"], valid_delta
        )
        candidates.append(
            {
                "family": "qrc",
                "candidate": config["name"],
                "gate": gate,
                "valid_objective": valid_objective,
                "valid_prediction": predictions_from_delta(
                    spec.kind, saved["base_valid"], valid_delta, gate
                ),
                "test_prediction": predictions_from_delta(
                    spec.kind, saved["base_test"], test_delta, gate
                ),
            }
        )

    for group_index, seeds in enumerate(ORTH_GROUPS):
        train_features = [
            quadratic_features(train_latent, real_orthogonal_readouts(seed))
            for seed in seeds
        ]
        valid_features = [
            quadratic_features(valid_latent, real_orthogonal_readouts(seed))
            for seed in seeds
        ]
        test_features = [
            quadratic_features(test_latent, real_orthogonal_readouts(seed))
            for seed in seeds
        ]
        valid_delta, test_delta = _fit_ensemble(
            spec.kind,
            train_features,
            valid_features,
            test_features,
            train_y,
            offset,
        )
        gate, valid_objective = select_gate(
            spec.kind, spec.metric, valid_y, saved["base_valid"], valid_delta
        )
        candidates.append(
            {
                "family": "real_orthogonal",
                "candidate": f"group_{group_index + 1}",
                "gate": gate,
                "valid_objective": valid_objective,
                "valid_prediction": predictions_from_delta(
                    spec.kind, saved["base_valid"], valid_delta, gate
                ),
                "test_prediction": predictions_from_delta(
                    spec.kind, saved["base_test"], test_delta, gate
                ),
            }
        )

    qrc_candidates = [c for c in candidates if c["family"] == "qrc"]
    orth_candidates = [c for c in candidates if c["family"] == "real_orthogonal"]
    selected_qrc = max(qrc_candidates, key=lambda c: c["valid_objective"])
    selected_orth = max(orth_candidates, key=lambda c: c["valid_objective"])
    qrc_test = score(spec.metric, test_y, selected_qrc["test_prediction"])
    orth_test = score(spec.metric, test_y, selected_orth["test_prediction"])
    base_test = metadata["base_test_score"]
    result = {
        "base": base,
        "task": task,
        "metric": spec.metric,
        "split_seed": split_seed,
        "qrc_candidate": selected_qrc["candidate"],
        "orth_candidate": selected_orth["candidate"],
        "qrc_gate": selected_qrc["gate"],
        "orth_gate": selected_orth["gate"],
        "qrc_validation_objective": selected_qrc["valid_objective"],
        "orth_validation_objective": selected_orth["valid_objective"],
        "qrc_test_score": qrc_test,
        "orth_test_score": orth_test,
        "base_test_score": base_test,
        "qrc_minus_orth": direction * (qrc_test - orth_test),
        "qrc_minus_base": direction * (qrc_test - base_test),
    }
    arrays = {
        "y_valid": valid_y,
        "y_test": test_y,
        "qrc_test": selected_qrc["test_prediction"],
        "orth_test": selected_orth["test_prediction"],
        "base_test": saved["base_test"],
        "scaffold": saved["test_scaffold"],
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(destination, **arrays)
    write_json(
        destination.with_suffix(".json"),
        {
            **result,
            "candidate_scores": [
                {
                    "family": candidate["family"],
                    "candidate": candidate["candidate"],
                    "gate": candidate["gate"],
                    "valid_objective": candidate["valid_objective"],
                    "test_score": score(
                        spec.metric, test_y, candidate["test_prediction"]
                    ),
                }
                for candidate in candidates
            ],
        },
    )
    return result


def summarize() -> None:
    rows = []
    for path in sorted(OUTPUT_ROOT.glob("*/*/split_*.json")):
        rows.append(json.loads(path.read_text(encoding="utf-8")))
    if not rows:
        raise RuntimeError("No tuned-QRC results")
    import pandas as pd

    frame = pd.DataFrame(rows)
    frame.to_csv(OUTPUT_ROOT / "metrics_by_seed.csv", index=False, encoding="utf-8-sig")
    aggregate = (
        frame.groupby(["base", "task", "metric"], as_index=False)
        .agg(
            qrc_test=("qrc_test_score", "mean"),
            orth_test=("orth_test_score", "mean"),
            qrc_minus_orth=("qrc_minus_orth", "mean"),
            qrc_minus_base=("qrc_minus_base", "mean"),
            qrc_gate=("qrc_gate", "mean"),
            orth_gate=("orth_gate", "mean"),
        )
    )
    aggregate.to_csv(OUTPUT_ROOT / "endpoint_summary.csv", index=False, encoding="utf-8-sig")
    counts = (
        aggregate.groupby("base", as_index=False)
        .agg(
            endpoints=("task", "nunique"),
            qrc_better_than_orth=("qrc_minus_orth", lambda x: (x > 0).sum()),
            qrc_worse_than_orth=("qrc_minus_orth", lambda x: (x < 0).sum()),
            qrc_better_than_base=("qrc_minus_base", lambda x: (x > 0).sum()),
            qrc_worse_than_base=("qrc_minus_base", lambda x: (x < 0).sum()),
        )
    )
    counts.to_csv(OUTPUT_ROOT / "direction_counts.csv", index=False, encoding="utf-8-sig")
    print(counts.to_string(index=False))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args()
    if not args.summarize_only:
        jobs = [
            (base, task, seed)
            for base in ("extra_trees", "catboost")
            for task in SENSITIVITY_TASKS
            for seed in SPLIT_SEEDS
        ]
        start = time.time()
        completed = 0
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(run_job, job): job for job in jobs}
            for future in as_completed(futures):
                result = future.result()
                completed += 1
                log(
                    f"{completed}/{len(jobs)} tuned {result['base']} "
                    f"{result['task']} seed={result['split_seed']}"
                )
        log(f"tuned-QRC jobs finished in {time.time() - start:.1f}s")
    summarize()
    return 0


if __name__ == "__main__":
    sys.exit(main())

