from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem import rdFingerprintGenerator
from rdkit.Chem.Scaffolds import MurckoScaffold

from src.build_features import _fixed_count_to_array, _reference_runtime
from src.config import MAP_SEEDS, RESULTS_ROOT
from src.data import write_json
from src.external_data import (
    CACHE_ROOT as EXTERNAL_CACHE_ROOT,
    EXTERNAL_ROOT,
    PREPARED_ROOT,
    _tdc_canonical_set,
    canonical_smiles,
)
from src.modeling import (
    branch_predictions,
    fit_base_predictions,
    latent_features,
    predictions_from_delta,
    score,
    select_gate,
)


RDLogger.DisableLog("rdApp.*")
TASK = "herg_pic50"
MODEL_METRIC = "Spearman"
OUTPUT_ROOT = RESULTS_ROOT / "external_regression"
SPLIT_SEED = 20261125


def _sha256(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _scaffold(text: str) -> str | None:
    molecule = Chem.MolFromSmiles(str(text))
    if molecule is None:
        return None
    return (
        MurckoScaffold.MurckoScaffoldSmiles(
            mol=molecule, includeChirality=False
        )
        or "<ACYCLIC_EMPTY>"
    )


def _scaffold_partition(
    frame: pd.DataFrame, seed: int, train_fraction: float = 0.875
) -> tuple[pd.DataFrame, pd.DataFrame]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for index, scaffold in enumerate(frame["scaffold"].astype(str)):
        grouped[scaffold].append(index)
    keys = sorted(grouped)
    random.Random(seed).shuffle(keys)
    target = int(len(frame) * train_fraction)
    train_indices: list[int] = []
    valid_indices: list[int] = []
    for key in keys:
        destination = (
            train_indices
            if len(train_indices) + len(grouped[key]) <= target
            else valid_indices
        )
        destination.extend(grouped[key])
    if not train_indices or not valid_indices:
        raise RuntimeError("External scaffold split produced an empty subset")
    train = frame.iloc[train_indices].reset_index(drop=True)
    valid = frame.iloc[valid_indices].reset_index(drop=True)
    if set(train["scaffold"]) & set(valid["scaffold"]):
        raise RuntimeError("External train and validation scaffolds overlap")
    return train, valid


def prepare_regression_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    PREPARED_ROOT.mkdir(parents=True, exist_ok=True)
    source = EXTERNAL_ROOT / "hERG_Dataset.csv"
    frame = pd.read_csv(source)
    frame["canonical_smiles"] = frame["SMILES"].map(canonical_smiles)
    frame["scaffold"] = frame["SMILES"].map(_scaffold)
    before = len(frame)
    frame = frame.dropna(subset=["canonical_smiles", "scaffold", "PIC50"])
    frame = frame.drop_duplicates("canonical_smiles", keep="first").copy()
    after_deduplication = len(frame)
    tdc_overlap = frame["canonical_smiles"].isin(_tdc_canonical_set("herg"))
    removed_tdc = int(tdc_overlap.sum())
    frame = frame[~tdc_overlap].copy()
    frame["Drug"] = frame["SMILES"].astype(str)
    frame["Y"] = frame["PIC50"].astype(float)

    dev = frame[frame["USED_AS"].eq("Dev-set")].reset_index(drop=True)
    test_before = frame[frame["USED_AS"].eq("Test-set")].reset_index(drop=True)
    dev_scaffolds = set(dev["scaffold"])
    test_leak = test_before["scaffold"].isin(dev_scaffolds)
    test = test_before[~test_leak].reset_index(drop=True)
    if not test["scaffold"].is_unique:
        # Multiple source-test molecules can share a scaffold; this is allowed.
        pass
    if set(dev["canonical_smiles"]) & set(test["canonical_smiles"]):
        raise RuntimeError("External regression train/test canonical overlap")
    if dev_scaffolds & set(test["scaffold"]):
        raise RuntimeError("External regression train/test scaffold overlap")

    train, valid = _scaffold_partition(dev, SPLIT_SEED)
    columns = ["Drug", "Y", "canonical_smiles", "scaffold", "SourceID"]
    for name, split in (("train", train), ("valid", valid), ("test", test)):
        split[columns].to_csv(
            PREPARED_ROOT / f"{TASK}_{name}.csv",
            index=False,
            encoding="utf-8-sig",
        )

    audit = {
        "status": "passed",
        "source": "Zenodo 5807719 / ToxTree continuous hERG test collection",
        "source_path": str(source.relative_to(EXTERNAL_ROOT.parents[1])),
        "source_sha256": _sha256(source),
        "target": "PIC50",
        "split_protocol": (
            "source-defined Dev-set/Test-set; TDC canonical overlap removed; "
            "test scaffolds shared with the external Dev-set removed; Dev-set "
            "split 87.5/12.5 by Bemis-Murcko scaffold"
        ),
        "split_seed": SPLIT_SEED,
        "source_rows": before,
        "removed_invalid_or_duplicate": before - after_deduplication,
        "removed_tdc_canonical_overlap": removed_tdc,
        "external_dev": int(len(dev)),
        "removed_test_scaffold_leakage": int(test_leak.sum()),
        "external_test": int(len(test)),
        "train": int(len(train)),
        "valid": int(len(valid)),
        "train_scaffolds": int(train["scaffold"].nunique()),
        "valid_scaffolds": int(valid["scaffold"].nunique()),
        "test_scaffolds": int(test["scaffold"].nunique()),
        "canonical_overlap_train_valid": 0,
        "scaffold_overlap_train_valid": 0,
        "canonical_overlap_train_test": 0,
        "scaffold_overlap_train_test": 0,
    }
    write_json(PREPARED_ROOT / f"{TASK}_audit.json", audit)
    return train, valid, test


def _morgan_features(smiles: list[str], n_bits: int = 512) -> np.ndarray:
    generator = rdFingerprintGenerator.GetMorganGenerator(
        radius=2, fpSize=n_bits
    )
    output = np.zeros((len(smiles), n_bits), dtype=np.float32)
    for index, text in enumerate(smiles):
        molecule = Chem.MolFromSmiles(text)
        if molecule is None:
            raise ValueError(f"Invalid SMILES: {text}")
        values = np.zeros(n_bits, dtype=np.uint8)
        Chem.DataStructs.ConvertToNumpyArray(
            generator.GetFingerprint(molecule), values
        )
        output[index] = values
    return output


def _maplight_chunk(smiles: list[str]) -> np.ndarray:
    reference = _reference_runtime()
    reference.count_to_array = _fixed_count_to_array
    with np.errstate(over="ignore", invalid="ignore"):
        features = reference.get_fingerprints(pd.Series(smiles)).astype(
            np.float32
        )
    features[~np.isfinite(features)] = np.nan
    return features


def _feature_matrix(
    smiles: list[str], base: str, workers: int
) -> np.ndarray:
    EXTERNAL_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    order_hash = hashlib.sha256("\n".join(smiles).encode()).hexdigest()
    path = EXTERNAL_CACHE_ROOT / f"{TASK}_{base}.npy"
    metadata_path = path.with_suffix(".json")
    if path.exists() and metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("order_hash") == order_hash:
            return np.load(path, mmap_mode="r")

    started = time.time()
    if base == "extra_trees":
        matrix = _morgan_features(smiles)
    elif base == "catboost":
        chunks = [smiles[start : start + 64] for start in range(0, len(smiles), 64)]
        with ProcessPoolExecutor(max_workers=workers) as pool:
            parts = list(pool.map(_maplight_chunk, chunks))
        matrix = np.vstack(parts).astype(np.float32, copy=False)
    else:
        raise ValueError(f"Unsupported base: {base}")
    np.save(path, matrix, allow_pickle=False)
    write_json(
        metadata_path,
        {
            "shape": list(matrix.shape),
            "dtype": str(matrix.dtype),
            "order_hash": order_hash,
            "base": base,
            "elapsed_seconds": time.time() - started,
        },
    )
    return matrix


def _path(base: str, seed: int):
    return OUTPUT_ROOT / base / f"{TASK}_seed_{seed}.npz"


def run_job(
    base: str,
    model_seed: int,
    workers: int,
    threads: int,
    overwrite: bool = False,
) -> dict[str, object]:
    destination = _path(base, model_seed)
    if destination.exists() and not overwrite:
        return json.loads(
            destination.with_suffix(".json").read_text(encoding="utf-8")
        )

    started = time.time()
    train, valid, test = prepare_regression_frames()
    combined = pd.concat([train, valid, test], ignore_index=True)
    matrix = _feature_matrix(
        combined["Drug"].astype(str).tolist(), base, workers
    )
    train_x = np.asarray(matrix[: len(train)], dtype=np.float32)
    valid_x = np.asarray(
        matrix[len(train) : len(train) + len(valid)], dtype=np.float32
    )
    test_x = np.asarray(matrix[len(train) + len(valid) :], dtype=np.float32)
    train_y = train["Y"].to_numpy(dtype=float)
    valid_y = valid["Y"].to_numpy(dtype=float)
    test_y = test["Y"].to_numpy(dtype=float)

    base_output = fit_base_predictions(
        base=base,
        task=TASK,
        kind="regression",
        train_x=train_x,
        train_y=train_y,
        valid_x=valid_x,
        test_x=test_x,
        groups=train["scaffold"].astype(str).to_numpy(),
        seed=model_seed,
        threads=threads,
    )
    train_latent, valid_latent, test_latent = latent_features(
        train_x, valid_x, test_x, seed=model_seed
    )
    branches, diagnostics = branch_predictions(
        kind="regression",
        train_latent=train_latent,
        valid_latent=valid_latent,
        test_latent=test_latent,
        train_y=train_y,
        oof_base=base_output["oof"],
    )

    arrays: dict[str, np.ndarray] = {
        "y_valid": valid_y,
        "y_test": test_y,
        "test_scaffold": np.asarray(
            test["scaffold"].astype(str).tolist(), dtype=str
        ),
        "base_valid": base_output["valid"],
        "base_test": base_output["test"],
        "base_oof": base_output["oof"],
    }
    scores: dict[str, dict[str, float]] = {
        "base": {
            "valid_spearman": score(
                "Spearman", valid_y, base_output["valid"]
            ),
            "test_spearman": score("Spearman", test_y, base_output["test"]),
            "test_mae": score("MAE", test_y, base_output["test"]),
        }
    }
    for family in ("qrc", "real_orthogonal", "random_fourier"):
        gate, _ = select_gate(
            "regression",
            MODEL_METRIC,
            valid_y,
            base_output["valid"],
            branches[family]["valid_delta"],
        )
        valid_ungated = predictions_from_delta(
            "regression",
            base_output["valid"],
            branches[family]["valid_delta"],
            1.0,
        )
        test_ungated = predictions_from_delta(
            "regression",
            base_output["test"],
            branches[family]["test_delta"],
            1.0,
        )
        valid_gated = predictions_from_delta(
            "regression",
            base_output["valid"],
            branches[family]["valid_delta"],
            gate,
        )
        test_gated = predictions_from_delta(
            "regression",
            base_output["test"],
            branches[family]["test_delta"],
            gate,
        )
        arrays[f"{family}_valid_ungated"] = valid_ungated
        arrays[f"{family}_test_ungated"] = test_ungated
        arrays[f"{family}_valid_gated"] = valid_gated
        arrays[f"{family}_test_gated"] = test_gated
        arrays[f"{family}_gate"] = np.asarray([gate])
        scores[family] = {
            "gate": gate,
            "valid_spearman": score(
                "Spearman", valid_y, valid_gated
            ),
            "test_spearman_ungated": score(
                "Spearman", test_y, test_ungated
            ),
            "test_spearman_gated": score(
                "Spearman", test_y, test_gated
            ),
            "test_mae_ungated": score("MAE", test_y, test_ungated),
            "test_mae_gated": score("MAE", test_y, test_gated),
        }

    destination.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(destination, **arrays)
    metadata = {
        "status": "completed",
        "base": base,
        "external_task": TASK,
        "target": "PIC50",
        "model_seed": model_seed,
        "metric": MODEL_METRIC,
        "n_train": int(len(train)),
        "n_valid": int(len(valid)),
        "n_test": int(len(test)),
        "map_seeds": list(MAP_SEEDS),
        "scores": scores,
        "map_diagnostics": diagnostics,
        "elapsed_seconds": time.time() - started,
    }
    write_json(destination.with_suffix(".json"), metadata)
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bases",
        nargs="+",
        choices=("extra_trees", "catboost"),
        default=("extra_trees", "catboost"),
    )
    parser.add_argument("--seeds", nargs="+", type=int, default=(1,))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    prepare_regression_frames()
    for base in args.bases:
        for seed in args.seeds:
            metadata = run_job(
                base,
                seed,
                workers=args.workers,
                threads=args.threads,
                overwrite=args.overwrite,
            )
            print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
