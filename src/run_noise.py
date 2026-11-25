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
from src.reservoir import depolarized_qrc_features, qrc_readouts
from src.run_benchmark import _task_matrix, log, run_path
from src.run_finite_shot import SENSITIVITY_TASKS


NOISE_LEVELS = (0.001, 0.005, 0.010)
SHOTS = 4096
OUTPUT_ROOT = RESULTS_ROOT / "noise"


def output_path(base: str, task: str, split_seed: int):
    return OUTPUT_ROOT / base / task / f"split_{split_seed}.json"


def run_job(payload: tuple[str, str, int]) -> dict[str, object]:
    base, task, split_seed = payload
    destination = output_path(base, task, split_seed)
    if destination.exists():
        return json.loads(destination.read_text(encoding="utf-8"))
    spec = TASK_BY_NAME[task]
    train, valid, test = make_split(load_task_frames(task), split_seed)
    train_x = _task_matrix(base, train)
    valid_x = _task_matrix(base, valid)
    test_x = _task_matrix(base, test)
    train_latent, valid_latent, test_latent = latent_features(
        train_x, valid_x, test_x, seed=split_seed
    )
    source = run_path(base, task, split_seed)
    with np.load(source, allow_pickle=False) as values:
        saved = {name: np.asarray(values[name]) for name in values.files}
    metadata = json.loads(source.with_suffix(".json").read_text(encoding="utf-8"))
    offset = (
        np.log(np.clip(saved["base_oof"], 1e-7, 1 - 1e-7))
        - np.log(np.clip(1 - saved["base_oof"], 1e-7, 1 - 1e-7))
        if spec.binary
        else saved["base_oof"]
    )
    results = []
    for noise_index, probability in enumerate(NOISE_LEVELS):
        valid_deltas = []
        test_deltas = []
        for map_index, map_seed in enumerate(MAP_SEEDS):
            readout = qrc_readouts(map_seed)
            sampling_seed = (
                20300000
                + split_seed * 1000
                + map_index * 50
                + noise_index * 10
                + (0 if base == "extra_trees" else 5)
            )
            train_features = depolarized_qrc_features(
                train_latent, readout, probability, SHOTS, sampling_seed
            )
            valid_features = depolarized_qrc_features(
                valid_latent, readout, probability, SHOTS, sampling_seed + 1
            )
            test_features = depolarized_qrc_features(
                test_latent, readout, probability, SHOTS, sampling_seed + 2
            )
            valid_delta, test_delta = _fit_branch_delta(
                spec.kind,
                train_features,
                valid_features,
                test_features,
                saved["y_train"],
                offset,
            )
            valid_deltas.append(valid_delta)
            test_deltas.append(test_delta)
        valid_delta = np.column_stack(valid_deltas).mean(axis=1)
        test_delta = np.column_stack(test_deltas).mean(axis=1)
        gate, _ = select_gate(
            spec.kind,
            spec.metric,
            saved["y_valid"],
            saved["base_valid"],
            valid_delta,
        )
        valid_prediction = predictions_from_delta(
            spec.kind, saved["base_valid"], valid_delta, gate
        )
        test_prediction = predictions_from_delta(
            spec.kind, saved["base_test"], test_delta, gate
        )
        direction = -1.0 if spec.metric == "MAE" else 1.0
        result = {
            "base": base,
            "task": task,
            "metric": spec.metric,
            "split_seed": split_seed,
            "depolarizing_probability": probability,
            "shots": SHOTS,
            "gate_qrc": gate,
            "valid_score": score(spec.metric, saved["y_valid"], valid_prediction),
            "test_score": score(spec.metric, saved["y_test"], test_prediction),
            "orth_gated_score": metadata["method_scores"]["real_orthogonal_gated"][
                "test"
            ],
            "base_score": metadata["base_test_score"],
        }
        result["noisy_qrc_minus_orth_gated"] = direction * (
            result["test_score"] - result["orth_gated_score"]
        )
        result["noisy_qrc_minus_base"] = direction * (
            result["test_score"] - result["base_score"]
        )
        results.append(result)
    payload_result = {
        "base": base,
        "task": task,
        "split_seed": split_seed,
        "results": results,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    write_json(destination, payload_result)
    return payload_result


def summarize() -> None:
    rows = []
    for path in sorted(OUTPUT_ROOT.glob("*/*/split_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows.extend(payload["results"])
    if not rows:
        raise RuntimeError("No noise results")
    import pandas as pd

    frame = pd.DataFrame(rows)
    endpoint = (
        frame.groupby(
            ["base", "task", "metric", "depolarizing_probability"], as_index=False
        )
        .agg(
            qrc_gate_mean=("gate_qrc", "mean"),
            score_mean=("test_score", "mean"),
            noisy_minus_orth=("noisy_qrc_minus_orth_gated", "mean"),
            noisy_minus_base=("noisy_qrc_minus_base", "mean"),
            positive_splits_vs_orth=("noisy_qrc_minus_orth_gated", lambda x: (x > 0).sum()),
            negative_splits_vs_orth=("noisy_qrc_minus_orth_gated", lambda x: (x < 0).sum()),
        )
    )
    counts = (
        endpoint.groupby(["base", "depolarizing_probability"], as_index=False)
        .agg(
            endpoints=("task", "nunique"),
            qrc_better_than_orth=("noisy_minus_orth", lambda x: (x > 0).sum()),
            qrc_worse_than_orth=("noisy_minus_orth", lambda x: (x < 0).sum()),
            qrc_better_than_base=("noisy_minus_base", lambda x: (x > 0).sum()),
            qrc_worse_than_base=("noisy_minus_base", lambda x: (x < 0).sum()),
        )
    )
    endpoint.to_csv(OUTPUT_ROOT / "endpoint_results.csv", index=False, encoding="utf-8-sig")
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
                payload = future.result()
                completed += 1
                log(
                    f"{completed}/{len(jobs)} noise {payload['base']} "
                    f"{payload['task']} seed={payload['split_seed']}"
                )
        log(f"noise jobs finished in {time.time() - start:.1f}s")
    summarize()
    return 0


if __name__ == "__main__":
    sys.exit(main())

