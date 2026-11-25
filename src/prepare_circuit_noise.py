from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from src.config import CIRCUIT_TASKS, PROJECT_ROOT, RESULTS_ROOT, TASK_BY_NAME
from src.data import make_split, write_json
from src.data import load_task_frames
from src.modeling import latent_features
from src.run_benchmark import _task_matrix


BASE = "catboost"
SPLIT_SEED = 1
PREPARED_ROOT = PROJECT_ROOT / "data" / "circuit_noise" / "prepared"
OUTPUT_ROOT = RESULTS_ROOT / "circuit_level_noise"


def _sample_indices(truth: np.ndarray, kind: str, size: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    if kind == "classification":
        positive = np.flatnonzero(truth >= 0.5)
        negative = np.flatnonzero(truth < 0.5)
        per_class = size // 2
        if len(positive) < per_class or len(negative) < per_class:
            raise RuntimeError("Not enough samples in each external class")
        selected = np.concatenate(
            [
                rng.choice(positive, size=per_class, replace=False),
                rng.choice(negative, size=per_class, replace=False),
            ]
        )
    else:
        selected = rng.choice(
            np.arange(len(truth)), size=size, replace=False
        )
    return np.sort(selected.astype(np.int64))


def prepare(sample_size: int = 32) -> dict[str, object]:
    PREPARED_ROOT.mkdir(parents=True, exist_ok=True)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    tasks = {}
    for task_index, task in enumerate(CIRCUIT_TASKS):
        spec = TASK_BY_NAME[task]
        train, valid, test = make_split(load_task_frames(task), SPLIT_SEED)
        train_x = _task_matrix(BASE, train)
        valid_x = _task_matrix(BASE, valid)
        test_x = _task_matrix(BASE, test)
        _, _, test_latent = latent_features(
            train_x, valid_x, test_x, seed=SPLIT_SEED
        )
        test_y = test["Y"].to_numpy(dtype=float)
        selected = _sample_indices(
            test_y,
            spec.kind,
            sample_size,
            20261201 + task_index,
        )
        destination = PREPARED_ROOT / f"{task}.npz"
        np.savez_compressed(
            destination,
            latent=np.asarray(test_latent[selected], dtype=np.float64),
            y=np.asarray(test_y[selected], dtype=np.float64),
            test_row=selected,
        )
        tasks[task] = {
            "kind": spec.kind,
            "metric": spec.metric,
            "base": BASE,
            "split_seed": SPLIT_SEED,
            "sample_size": int(len(selected)),
            "positive": int((test_y[selected] >= 0.5).sum())
            if spec.kind == "classification"
            else None,
            "path": str(destination.relative_to(PROJECT_ROOT)),
        }
    manifest = {
        "base": BASE,
        "split_seed": SPLIT_SEED,
        "sample_size_per_task": sample_size,
        "tasks": tasks,
    }
    write_json(OUTPUT_ROOT / "prepared_manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-size", type=int, default=32)
    args = parser.parse_args()
    print(json.dumps(prepare(args.sample_size), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
