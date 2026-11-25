from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from random import Random

import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem import rdFingerprintGenerator

from src.config import (
    CACHE_ROOT,
    DATA_ROOT,
    OFFICIAL_DATA_ROOT,
    PROJECT_ROOT,
    RESULTS_ROOT,
    TASK_BY_NAME,
)


RDLogger.DisableLog("rdApp.*")
SPLITS = ("train_val", "test")


@dataclass(frozen=True)
class TaskFrames:
    task: str
    train_val: pd.DataFrame
    test: pd.DataFrame


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def load_cache_metadata() -> tuple[list[str], list[list[str]]]:
    smiles = json.loads((CACHE_ROOT / "smiles.json").read_text(encoding="utf-8"))
    groups = json.loads(
        (CACHE_ROOT / "molecule_groups.json").read_text(encoding="utf-8")
    )
    if len(smiles) != len(groups):
        raise ValueError("SMILES and molecule metadata caches are not aligned")
    return smiles, groups


SMILES, MOLECULE_GROUPS = load_cache_metadata()
SMILES_TO_INDEX = {smiles: index for index, smiles in enumerate(SMILES)}
SMILES_TO_CANONICAL = {
    smiles: values[0] for smiles, values in zip(SMILES, MOLECULE_GROUPS, strict=True)
}
SMILES_TO_SCAFFOLD = {
    smiles: values[1] for smiles, values in zip(SMILES, MOLECULE_GROUPS, strict=True)
}


def load_task_frames(task: str) -> TaskFrames:
    if task not in TASK_BY_NAME:
        raise KeyError(f"Unknown ADMET endpoint: {task}")
    frames = {}
    for split in SPLITS:
        path = OFFICIAL_DATA_ROOT / task / f"{split}.csv"
        frame = pd.read_csv(path, dtype={"Drug_ID": str})
        if not {"Drug_ID", "Drug", "Y"}.issubset(frame.columns):
            raise ValueError(f"{path} lacks required columns")
        frame = frame.copy()
        frame["_source_split"] = split
        frame["_source_row"] = np.arange(len(frame), dtype=np.int64)
        frames[split] = frame.reset_index(drop=True)
    return TaskFrames(task=task, **frames)


def _create_scaffold_split(
    frame: pd.DataFrame,
    seed: int,
    train_fraction: float = 0.875,
    valid_fraction: float = 0.125,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Replicate PyTDC's scaffold split used by ADMET_Group seeds."""
    random = Random(seed)
    scaffold_to_indices: dict[str, set[int]] = defaultdict(set)
    for index, smiles in enumerate(frame["Drug"].astype(str)):
        scaffold = SMILES_TO_SCAFFOLD[smiles]
        scaffold_to_indices[scaffold].add(index)

    train_size = int(len(frame) * train_fraction)
    valid_size = int(len(frame) * valid_fraction)
    big: list[set[int]] = []
    small: list[set[int]] = []
    for indices in scaffold_to_indices.values():
        if len(indices) > valid_size / 2:
            big.append(indices)
        else:
            small.append(indices)
    random.shuffle(big)
    random.shuffle(small)

    train_indices: list[int] = []
    valid_indices: list[int] = []
    for indices in big + small:
        if len(train_indices) + len(indices) <= train_size:
            train_indices.extend(indices)
        else:
            valid_indices.extend(indices)

    if not train_indices or not valid_indices:
        raise RuntimeError("Scaffold split produced an empty train or validation set")
    return (
        frame.iloc[train_indices].reset_index(drop=True),
        frame.iloc[valid_indices].reset_index(drop=True),
    )


def make_split(frames: TaskFrames, seed: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train, valid = _create_scaffold_split(frames.train_val, seed=seed)
    test = frames.test.copy().reset_index(drop=True)

    train_scaffolds = {SMILES_TO_SCAFFOLD[s] for s in train["Drug"]}
    valid_scaffolds = {SMILES_TO_SCAFFOLD[s] for s in valid["Drug"]}
    test_scaffolds = {SMILES_TO_SCAFFOLD[s] for s in test["Drug"]}
    if train_scaffolds & valid_scaffolds:
        raise RuntimeError("Train and validation scaffolds overlap")
    if test_scaffolds & (train_scaffolds | valid_scaffolds):
        raise RuntimeError("Official test shares a scaffold with train or validation")

    train_canonical = {SMILES_TO_CANONICAL[s] for s in train["Drug"]}
    valid_canonical = {SMILES_TO_CANONICAL[s] for s in valid["Drug"]}
    test_canonical = {SMILES_TO_CANONICAL[s] for s in test["Drug"]}
    if train_canonical & valid_canonical:
        raise RuntimeError("Train and validation canonical molecules overlap")
    if test_canonical & (train_canonical | valid_canonical):
        raise RuntimeError("Official test shares a canonical molecule with train or validation")
    return train, valid, test


def feature_indices(frame: pd.DataFrame) -> np.ndarray:
    try:
        return np.asarray(
            [SMILES_TO_INDEX[s] for s in frame["Drug"].astype(str)], dtype=np.int64
        )
    except KeyError as error:
        raise KeyError(f"SMILES missing from the shared feature cache: {error}") from error


def load_maplight_features(indices: np.ndarray) -> np.ndarray:
    matrix = np.load(CACHE_ROOT / "maplight.npy", mmap_mode="r")
    return np.asarray(matrix[indices], dtype=np.float32)


def _morgan_chunk(smiles: list[str], n_bits: int) -> np.ndarray:
    generator = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=n_bits)
    result = np.zeros((len(smiles), n_bits), dtype=np.uint8)
    for row, text in enumerate(smiles):
        molecule = Chem.MolFromSmiles(text)
        if molecule is None:
            raise ValueError(f"Invalid SMILES: {text}")
        fingerprint = generator.GetFingerprint(molecule)
        values = np.zeros(n_bits, dtype=np.uint8)
        Chem.DataStructs.ConvertToNumpyArray(fingerprint, values)
        result[row] = values
    return result


def prepare_morgan_cache(n_bits: int = 512) -> Path:
    destination = CACHE_ROOT / f"morgan_{n_bits}.npy"
    metadata_path = CACHE_ROOT / f"morgan_{n_bits}_complete.json"
    if destination.exists() and metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("sha256") == sha256(destination):
            return destination

    values = np.empty((len(SMILES), n_bits), dtype=np.uint8)
    for start in range(0, len(SMILES), 256):
        values[start : start + 256] = _morgan_chunk(
            SMILES[start : start + 256], n_bits=n_bits
        )
    np.save(destination, values, allow_pickle=False)
    write_json(
        metadata_path,
        {
            "shape": list(values.shape),
            "dtype": str(values.dtype),
            "radius": 2,
            "sha256": sha256(destination),
        },
    )
    return destination


def load_morgan_features(indices: np.ndarray, n_bits: int = 512) -> np.ndarray:
    path = CACHE_ROOT / f"morgan_{n_bits}.npy"
    if not path.exists():
        prepare_morgan_cache(n_bits)
    matrix = np.load(path, mmap_mode="r")
    return np.asarray(matrix[indices], dtype=np.float32)


def prepare_and_validate_caches() -> dict[str, object]:
    maplight_path = CACHE_ROOT / "maplight.npy"
    maplight_meta_path = CACHE_ROOT / "maplight_complete.json"
    maplight_meta = json.loads(maplight_meta_path.read_text(encoding="utf-8"))
    actual_hash = sha256(maplight_path)
    if actual_hash.lower() != str(maplight_meta["sha256"]).lower():
        raise RuntimeError("MapLight feature cache checksum mismatch")
    if maplight_meta.get("count_dtype") != "int32":
        raise RuntimeError("MapLight cache was not generated with corrected count dtype")
    maplight = np.load(maplight_path, mmap_mode="r")
    if maplight.shape != (len(SMILES), 2563):
        raise RuntimeError("Unexpected MapLight cache shape")

    order_hash = hashlib.sha256("\n".join(SMILES).encode()).hexdigest()
    source_manifest_path = CACHE_ROOT / "source_manifest.json"
    source_manifest = (
        json.loads(source_manifest_path.read_text(encoding="utf-8"))
        if source_manifest_path.exists()
        else {}
    )
    expected_order_hash = (
        source_manifest.get("smiles_order_sha256")
        or maplight_meta.get("smiles_order_sha256")
    )
    if expected_order_hash and order_hash != expected_order_hash:
        raise RuntimeError("SMILES cache order hash does not match the data audit")

    morgan_path = prepare_morgan_cache(512)
    task_rows = {}
    for task in TASK_BY_NAME:
        frames = load_task_frames(task)
        task_rows[task] = {
            split: int(len(getattr(frames, split))) for split in SPLITS
        }
    summary = {
        "tasks": len(TASK_BY_NAME),
        "records": {
            split: sum(values[split] for values in task_rows.values())
            for split in SPLITS
        },
        "unique_smiles": len(SMILES),
        "maplight_sha256": actual_hash,
        "morgan_sha256": sha256(morgan_path),
        "task_rows": task_rows,
    }
    archive_path = (
        DATA_ROOT / "archives" / "admet_group_4426004.zip"
    )
    archive_hash = sha256(archive_path) if archive_path.exists() else None
    source_manifest.update(
        {
            "source": "TDC ADMET Group / Harvard Dataverse file 4426004",
            "archive_path": str(archive_path.relative_to(PROJECT_ROOT)),
            "archive_sha256": archive_hash,
            "records": summary["records"],
            "tasks": summary["tasks"],
            "unique_smiles": summary["unique_smiles"],
            "smiles_order_sha256": order_hash,
            "maplight_sha256": actual_hash,
            "morgan_sha256": summary["morgan_sha256"],
            "task_rows": task_rows,
        }
    )
    write_json(source_manifest_path, source_manifest)
    write_json(RESULTS_ROOT / "data_summary.json", summary)
    return summary


if __name__ == "__main__":
    print(json.dumps(prepare_and_validate_caches(), ensure_ascii=False, indent=2))

