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
from src.reservoir import qrc_readouts, shot_sampled_qrc_features
from src.run_benchmark import _task_matrix, log, run_path


SHOT_BUDGETS = (1024, 4096, 16384)
SENSITIVITY_TASKS = (
    "bbb_martins",
    "herg",
    "caco2_wang",
    "ld50_zhu",
    "ppbr_az",
    "dili",
    "cyp2d6_veith",
    "vdss_lombardo",
)
OUTPUT_ROOT = RESULTS_ROOT / "finite_shot"


def output_path(base: str, task: str, split_seed: int):
    return OUTPUT_ROOT / base / task / f"split_{split_seed}.json"


def run_job(payload: tuple[str, str, int]) -> dict[str, object]:
    base, task, split_seed = payload
    destination = output_path(base, task, split_seed)
    if destination.exists():
        return json.loads(destination.read_text(encoding="utf-8"))

    source = run_path(base, task, split_seed)
    with np.load(source, allow_pickle=False) as values:
        saved = {name: np.asarray(values[name]) for name in values.files}
    metadata = json.loads(source.with_suffix(".json").read_text(encoding="utf-8"))
    spec = TASK_BY_NAME[task]
    frames = load_task_frames(task)
    train, valid, test = make_split(frames, split_seed)
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

    results = []
    for shot_index, shots in enumerate(SHOT_BUDGETS):
        valid_deltas = []
        test_deltas = []
        for map_index, map_seed in enumerate(MAP_SEEDS):
            readout = qrc_readouts(map_seed)
            sampling_seed = (
                20261200
                + split_seed * 1000
                + map_index * 50
                + shot_index * 10
                + (0 if base == "extra_trees" else 5)
            )
            train_features = shot_sampled_qrc_features(
                train_latent, readout, shots, sampling_seed
            )
            valid_features = shot_sampled_qrc_features(
                valid_latent, readout, shots, sampling_seed + 1
            )
            test_features = shot_sampled_qrc_features(
                test_latent, readout, shots, sampling_seed + 2
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
        result = {
            "base": base,
            "task": task,
            "metric": spec.metric,
            "kind": spec.kind,
            "split_seed": split_seed,
            "shots": shots,
            "gate_qrc": gate,
            "valid_score": score(spec.metric, saved["y_valid"], valid_prediction),
            "test_score": score(spec.metric, saved["y_test"], test_prediction),
            "ideal_qrc_gated_score": metadata["method_scores"]["qrc_gated"]["test"],
            "orth_gated_score": metadata["method_scores"]["real_orthogonal_gated"][
                "test"
            ],
            "base_score": metadata["base_test_score"],
        }
        direction = -1.0 if spec.metric == "MAE" else 1.0
        result["finite_minus_orth_gated"] = direction * (
            result["test_score"] - result["orth_gated_score"]
        )
        result["finite_minus_base"] = direction * (
            result["test_score"] - result["base_score"]
        )
        result["finite_minus_ideal_qrc_gated"] = direction * (
            result["test_score"] - result["ideal_qrc_gated_score"]
        )
        results.append(result)

    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "base": base,
        "task": task,
        "split_seed": split_seed,
        "results": results,
    }
    write_json(destination, payload)
    return payload


def summarize() -> None:
    rows = []
    for path in sorted(OUTPUT_ROOT.glob("*/*/split_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows.extend(payload["results"])
    if not rows:
        raise RuntimeError("No finite-shot results found")
    import pandas as pd

    frame = pd.DataFrame(rows)
    aggregate = (
        frame.groupby(["base", "task", "metric", "shots"], as_index=False)
        .agg(
            qrc_gate_mean=("gate_qrc", "mean"),
            qrc_gate_zero_fraction=("gate_qrc", lambda x: (x == 0).mean()),
            score_mean=("test_score", "mean"),
            finite_minus_orth_gated=("finite_minus_orth_gated", "mean"),
            finite_minus_base=("finite_minus_base", "mean"),
            finite_minus_ideal_qrc_gated=(
                "finite_minus_ideal_qrc_gated",
                "mean",
            ),
            positive_splits_vs_orth=("finite_minus_orth_gated", lambda x: (x > 0).sum()),
            negative_splits_vs_orth=("finite_minus_orth_gated", lambda x: (x < 0).sum()),
        )
    )
    counts = (
        aggregate.groupby(["base", "shots"], as_index=False)
        .agg(
            endpoints=("task", "nunique"),
            qrc_better_than_orth=("finite_minus_orth_gated", lambda x: (x > 0).sum()),
            qrc_worse_than_orth=("finite_minus_orth_gated", lambda x: (x < 0).sum()),
            qrc_better_than_base=("finite_minus_base", lambda x: (x > 0).sum()),
            qrc_worse_than_base=("finite_minus_base", lambda x: (x < 0).sum()),
            mean_gate=("qrc_gate_mean", "mean"),
        )
    )
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    aggregate.to_csv(
        OUTPUT_ROOT / "endpoint_results.csv",
        index=False,
        encoding="utf-8-sig",
    )
    counts.to_csv(
        OUTPUT_ROOT / "direction_counts.csv",
        index=False,
        encoding="utf-8-sig",
    )
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
        started = time.time()
        completed = 0
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(run_job, job): job for job in jobs}
            for future in as_completed(futures):
                payload = future.result()
                completed += 1
                log(
                    f"{completed}/{len(jobs)} finite-shot "
                    f"{payload['base']} {payload['task']} seed={payload['split_seed']}"
                )
        log(f"finite-shot jobs finished in {time.time() - started:.1f}s")
    summarize()
    return 0


if __name__ == "__main__":
    sys.exit(main())

