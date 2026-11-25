from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold

from src.config import MAP_SEEDS, RESULTS_ROOT, SPLIT_SEEDS, TASK_BY_NAME
from src.data import SMILES_TO_SCAFFOLD, load_task_frames, make_split, write_json
from src.external_data import external_features, load_external, prepare_external_frames
from src.modeling import (
    branch_predictions,
    fit_base_predictions,
    latent_features,
    predictions_from_delta,
    score,
    select_gate,
)
from src.run_benchmark import _task_matrix, log
from src.run_low_data import _combined_gate


EXTERNAL_TASKS = ("herg", "bbb_martins")
OUTPUT_ROOT = RESULTS_ROOT / "external_validation"


def output_path(base: str, task: str, split_seed: int):
    return OUTPUT_ROOT / base / task / f"split_{split_seed}.npz"


def scaffold(text: str) -> str:
    try:
        molecule = Chem.MolFromSmiles(str(text))
        if molecule is None:
            return "<INVALID_MOLECULE>"
        return (
            MurckoScaffold.MurckoScaffoldSmiles(
                mol=molecule, includeChirality=False
            )
            or "<ACYCLIC_EMPTY>"
        )
    except Exception:
        return "<INVALID_SCAFFOLD>"


def run_job(payload: tuple[str, str, int]) -> dict[str, object]:
    base, task, split_seed = payload
    destination = output_path(base, task, split_seed)
    if destination.exists():
        metadata = json.loads(destination.with_suffix(".json").read_text(encoding="utf-8"))
        return metadata
    spec = TASK_BY_NAME[task]
    train, valid, _ = make_split(load_task_frames(task), split_seed)
    external = load_external(task)
    train_x = _task_matrix(base, train)
    valid_x = _task_matrix(base, valid)
    external_x = external_features(task, base)
    base_output = fit_base_predictions(
        base=base,
        task=task,
        kind=spec.kind,
        train_x=train_x,
        train_y=train["Y"].to_numpy(dtype=float),
        valid_x=valid_x,
        test_x=external_x,
        groups=np.asarray(
            [
                SMILES_TO_SCAFFOLD[smiles]
                for smiles in train["Drug"].astype(str)
            ]
        ),
        seed=split_seed,
        threads=4,
    )
    train_latent, valid_latent, test_latent = latent_features(
        train_x, valid_x, external_x, seed=split_seed
    )
    branches, _ = branch_predictions(
        kind=spec.kind,
        train_latent=train_latent,
        valid_latent=valid_latent,
        test_latent=test_latent,
        train_y=train["Y"].to_numpy(dtype=float),
        oof_base=base_output["oof"],
    )
    external_y = external["Y"].to_numpy(dtype=float)
    valid_y = valid["Y"].to_numpy(dtype=float)
    qrc_weight, orth_weight = _combined_gate(
        spec.kind,
        spec.metric,
        valid_y,
        base_output["valid"],
        branches["qrc"]["valid_delta"],
        branches["real_orthogonal"]["valid_delta"],
    )
    predictions = {
        "base": base_output["test"],
        "qrc_ungated": predictions_from_delta(
            spec.kind, base_output["test"], branches["qrc"]["test_delta"], 1.0
        ),
        "orth_ungated": predictions_from_delta(
            spec.kind,
            base_output["test"],
            branches["real_orthogonal"]["test_delta"],
            1.0,
        ),
        "qrc_plus_orth": predictions_from_delta(
            spec.kind,
            base_output["test"],
            qrc_weight * branches["qrc"]["test_delta"]
            + orth_weight * branches["real_orthogonal"]["test_delta"],
            1.0,
        ),
    }
    for family, prefix in (
        ("qrc", "qrc"),
        ("real_orthogonal", "orth"),
    ):
        gate, _ = select_gate(
            spec.kind,
            spec.metric,
            valid_y,
            base_output["valid"],
            branches[family]["valid_delta"],
        )
        predictions[f"{prefix}_gated"] = predictions_from_delta(
            spec.kind,
            base_output["test"],
            branches[family]["test_delta"],
            gate,
        )
        predictions[f"{prefix}_gate_weight"] = np.asarray([gate])
    arrays = {
        "y": external_y,
        "scaffold": np.asarray([scaffold(value) for value in external["Drug"]]),
        **{name: value for name, value in predictions.items()},
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(destination, **arrays)
    metadata = {
        "base": base,
        "task": task,
        "metric": spec.metric,
        "split_seed": split_seed,
        "n_tdc_train": int(len(train)),
        "n_tdc_valid": int(len(valid)),
        "n_external": int(len(external)),
        "external_source": str(external["source"].iloc[0]),
        "qrc_gate": float(predictions["qrc_gate_weight"][0]),
        "orth_gate": float(predictions["orth_gate_weight"][0]),
        "joint_qrc_weight": float(qrc_weight),
        "joint_orth_weight": float(orth_weight),
        "scores": {
            name: score(spec.metric, external_y, value)
            for name, value in predictions.items()
            if not name.endswith("_weight")
        },
    }
    write_json(destination.with_suffix(".json"), metadata)
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    prepare_external_frames()
    for base in ("extra_trees", "catboost"):
        for task in EXTERNAL_TASKS:
            external_features(task, base)
    jobs = [
        (base, task, seed)
        for base in ("extra_trees", "catboost")
        for task in EXTERNAL_TASKS
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
                f"{completed}/{len(jobs)} external {result['base']} "
                f"{result['task']} seed={result['split_seed']}"
            )
    log(f"external jobs finished in {time.time() - start:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())

