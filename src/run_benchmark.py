from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from src.config import (
    BASES,
    FAMILIES,
    MAP_SEEDS,
    PRIMARY_FAMILY,
    PRIMARY_MATCHED,
    RESULTS_ROOT,
    SPLIT_SEEDS,
    TASK_BY_NAME,
)
from src.data import (
    SMILES_TO_SCAFFOLD,
    feature_indices,
    load_maplight_features,
    load_morgan_features,
    load_task_frames,
    make_split,
    prepare_and_validate_caches,
    write_json,
)
from src.modeling import (
    branch_predictions,
    fit_base_predictions,
    latent_features,
    predictions_from_delta,
    score,
    select_gate,
)


RUN_ROOT = RESULTS_ROOT / "runs"
DIAGNOSTIC_ROOT = RESULTS_ROOT / "diagnostics"


def log(message: str) -> None:
    print(time.strftime("%H:%M:%S"), message, flush=True)


def run_path(base: str, task: str, split_seed: int) -> Path:
    return RUN_ROOT / base / task / f"split_{split_seed}.npz"


def _task_matrix(base: str, frame) -> np.ndarray:
    indices = feature_indices(frame)
    if base == "extra_trees":
        return load_morgan_features(indices)
    if base == "catboost":
        return load_maplight_features(indices)
    raise ValueError(f"Unknown base model: {base}")


def _method_predictions(
    kind: str,
    valid_base: np.ndarray,
    test_base: np.ndarray,
    valid_delta: np.ndarray,
    test_delta: np.ndarray,
    alpha: float,
) -> tuple[np.ndarray, np.ndarray]:
    return (
        predictions_from_delta(kind, valid_base, valid_delta, alpha),
        predictions_from_delta(kind, test_base, test_delta, alpha),
    )


def execute_job(
    base: str,
    task: str,
    split_seed: int,
    threads: int,
    overwrite: bool = False,
) -> dict[str, object]:
    destination = run_path(base, task, split_seed)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not overwrite:
        with np.load(destination, allow_pickle=False) as saved:
            return {
                "status": "cached",
                "base": base,
                "task": task,
                "split_seed": split_seed,
                "test_n": int(len(saved["y_test"])),
            }

    started = time.time()
    spec = TASK_BY_NAME[task]
    frames = load_task_frames(task)
    train, valid, test = make_split(frames, split_seed)
    train_y = train["Y"].to_numpy(dtype=float)
    valid_y = valid["Y"].to_numpy(dtype=float)
    test_y = test["Y"].to_numpy(dtype=float)
    if not (
        np.isfinite(train_y).all()
        and np.isfinite(valid_y).all()
        and np.isfinite(test_y).all()
    ):
        raise RuntimeError(f"{task}/{split_seed}: labels contain missing values")
    if spec.binary:
        for split_name, values in (
            ("train", train_y),
            ("valid", valid_y),
            ("test", test_y),
        ):
            if set(np.unique(values).astype(int)) != {0, 1}:
                raise RuntimeError(f"{task}/{split_seed}: {split_name} is not binary")

    train_x = _task_matrix(base, train)
    valid_x = _task_matrix(base, valid)
    test_x = _task_matrix(base, test)
    inner_groups = np.asarray(
        [SMILES_TO_SCAFFOLD[s] for s in train["Drug"].astype(str)]
    )
    base_output = fit_base_predictions(
        base=base,
        task=task,
        kind=spec.kind,
        train_x=train_x,
        train_y=train_y,
        valid_x=valid_x,
        test_x=test_x,
        groups=inner_groups,
        seed=split_seed,
        threads=threads,
    )
    train_latent, valid_latent, test_latent = latent_features(
        train_x, valid_x, test_x, seed=split_seed
    )
    branches, map_diagnostics = branch_predictions(
        kind=spec.kind,
        train_latent=train_latent,
        valid_latent=valid_latent,
        test_latent=test_latent,
        train_y=train_y,
        oof_base=base_output["oof"],
    )

    arrays: dict[str, np.ndarray] = {
        "y_train": train_y,
        "y_valid": valid_y,
        "y_test": test_y,
        "train_source_row": train["_source_row"].to_numpy(dtype=np.int64),
        "valid_source_row": valid["_source_row"].to_numpy(dtype=np.int64),
        "test_source_row": test["_source_row"].to_numpy(dtype=np.int64),
        "train_source_split": train["_source_split"].to_numpy(dtype="U8"),
        "valid_source_split": valid["_source_split"].to_numpy(dtype="U8"),
        "test_source_split": test["_source_split"].to_numpy(dtype="U8"),
        "test_scaffold": np.asarray(
            [SMILES_TO_SCAFFOLD[s] for s in test["Drug"].astype(str)]
        ),
        "base_oof": base_output["oof"],
        "base_valid": base_output["valid"],
        "base_test": base_output["test"],
    }
    metadata = {
        "base": base,
        "task": task,
        "metric": spec.metric,
        "kind": spec.kind,
        "split_seed": int(split_seed),
        "n_train": int(len(train)),
        "n_valid": int(len(valid)),
        "n_test": int(len(test)),
        "map_seeds": list(MAP_SEEDS),
        "families": list(FAMILIES),
        "base_valid_score": score(spec.metric, valid_y, base_output["valid"]),
        "base_test_score": score(spec.metric, test_y, base_output["test"]),
        "elapsed_seconds_before_write": time.time() - started,
        "map_diagnostics": map_diagnostics,
        "gate_weights": {},
        "method_scores": {},
    }

    for family in FAMILIES:
        alpha, valid_objective = select_gate(
            spec.kind,
            spec.metric,
            valid_y,
            base_output["valid"],
            branches[family]["valid_delta"],
        )
        metadata["gate_weights"][family] = alpha
        arrays[f"valid_delta_maps_{family}"] = branches[family]["valid_delta_maps"]
        arrays[f"test_delta_maps_{family}"] = branches[family]["test_delta_maps"]
        arrays[f"valid_delta_{family}"] = branches[family]["valid_delta"]
        arrays[f"test_delta_{family}"] = branches[family]["test_delta"]
        for state, weight in (("ungated", 1.0), ("gated", alpha)):
            valid_prediction, test_prediction = _method_predictions(
                spec.kind,
                base_output["valid"],
                base_output["test"],
                branches[family]["valid_delta"],
                branches[family]["test_delta"],
                weight,
            )
            arrays[f"valid_pred_{family}_{state}"] = valid_prediction
            arrays[f"test_pred_{family}_{state}"] = test_prediction
            metadata["method_scores"][f"{family}_{state}"] = {
                "valid": score(spec.metric, valid_y, valid_prediction),
                "test": score(spec.metric, test_y, test_prediction),
            }
        metadata["method_scores"][f"{family}_gate_validation_objective"] = (
            valid_objective
        )

    np.savez_compressed(destination, **arrays)
    metadata["elapsed_seconds"] = time.time() - started
    metadata_path = destination.with_suffix(".json")
    write_json(metadata_path, metadata)
    return {
        "status": "completed",
        "base": base,
        "task": task,
        "split_seed": split_seed,
        "test_n": int(len(test_y)),
        "gate_qrc": metadata["gate_weights"]["qrc"],
        "elapsed_seconds": metadata["elapsed_seconds"],
    }


def _job_worker(payload: tuple[str, str, int, int, bool]) -> dict[str, object]:
    return execute_job(*payload)


def command_prepare() -> None:
    summary = prepare_and_validate_caches()
    log(
        "cache ready: "
        f"{summary['tasks']} tasks, {summary['unique_smiles']} unique molecules, "
        f"records={summary['records']}"
    )


def command_run(
    tasks: list[str],
    split_seeds: list[int],
    bases: list[str],
    workers: int,
    threads: int,
    overwrite: bool,
) -> None:
    missing = sorted(set(tasks) - set(TASK_BY_NAME))
    if missing:
        raise SystemExit(f"Unknown tasks: {missing}")
    jobs = [
        (base, task, split_seed, threads, overwrite)
        for base in bases
        for task in tasks
        for split_seed in split_seeds
    ]
    log(f"scheduled {len(jobs)} base-model split jobs")
    completed = 0
    started = time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_job_worker, job): job for job in jobs}
        for future in as_completed(futures):
            result = future.result()
            completed += 1
            log(
                f"{completed}/{len(jobs)} {result['status']} "
                f"{result['base']} {result['task']} seed={result['split_seed']} "
                f"test_n={result['test_n']}"
            )
    log(f"finished in {time.time() - started:.1f}s")


def main() -> int:
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("prepare")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--tasks", nargs="+", default=list(TASK_BY_NAME))
    run_parser.add_argument("--split-seeds", nargs="+", type=int, default=list(SPLIT_SEEDS))
    run_parser.add_argument("--bases", nargs="+", choices=BASES, default=list(BASES))
    run_parser.add_argument("--workers", type=int, default=2)
    run_parser.add_argument("--threads", type=int, default=6)
    run_parser.add_argument("--overwrite", action="store_true")
    report_parser = subparsers.add_parser("report")
    report_parser.add_argument("--bootstrap", type=int, default=1000)
    report_parser.add_argument("--permutations", type=int, default=1999)
    args = parser.parse_args()

    if args.command == "prepare":
        command_prepare()
    elif args.command == "run":
        command_run(
            tasks=args.tasks,
            split_seeds=args.split_seeds,
            bases=args.bases,
            workers=args.workers,
            threads=args.threads,
            overwrite=args.overwrite,
        )
    else:
        from src.report import build_report

        build_report(args.bootstrap, args.permutations)
    return 0


if __name__ == "__main__":
    sys.exit(main())

