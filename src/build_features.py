from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem import DataStructs
from rdkit.Chem.Scaffolds import MurckoScaffold

from src.config import CACHE_ROOT, OFFICIAL_DATA_ROOT, PROJECT_ROOT, TASK_BY_NAME
from src.data import sha256, write_json


RDLogger.DisableLog("rdApp.*")
REFERENCE_PATH = PROJECT_ROOT / "third_party" / "maplight_reference.py"
_REFERENCE = None


def _load_reference():
    specification = importlib.util.spec_from_file_location(
        "maplight_reference_runtime", REFERENCE_PATH
    )
    if specification is None or specification.loader is None:
        raise ImportError(f"Cannot load {REFERENCE_PATH}")
    module = importlib.util.module_from_spec(specification)
    sys.modules["maplight_reference_runtime"] = module
    specification.loader.exec_module(module)
    return module


def _reference_runtime():
    global _REFERENCE
    if _REFERENCE is None:
        _REFERENCE = _load_reference()
        _REFERENCE.count_to_array = _fixed_count_to_array
    return _REFERENCE


def _fixed_count_to_array(fingerprint) -> np.ndarray:
    values = np.zeros(0, dtype=np.int32)
    DataStructs.ConvertToNumpyArray(fingerprint, values)
    return values


def official_unique_smiles() -> list[str]:
    seen = set()
    ordered = []
    for task in TASK_BY_NAME:
        for filename in ("train_val.csv", "test.csv"):
            frame = pd.read_csv(OFFICIAL_DATA_ROOT / task / filename)
            for smiles in frame["Drug"].astype(str):
                if smiles not in seen:
                    seen.add(smiles)
                    ordered.append(smiles)
    return ordered


def molecule_group(text: str) -> list[str]:
    molecule = Chem.MolFromSmiles(text)
    if molecule is None:
        raise ValueError(f"Invalid SMILES: {text}")
    canonical = Chem.MolToSmiles(molecule, isomericSmiles=False)
    scaffold = MurckoScaffold.MurckoScaffoldSmiles(
        mol=molecule, includeChirality=False
    )
    return [canonical, scaffold or "<ACYCLIC_EMPTY>"]


def feature_chunk(item: tuple[int, list[str]]) -> tuple[int, np.ndarray, int]:
    start, smiles = item
    reference = _reference_runtime()
    molecules = pd.Series(smiles)
    with np.errstate(over="ignore", invalid="ignore"):
        features = reference.get_fingerprints(molecules).astype(np.float32)
    invalid = ~np.isfinite(features)
    features[invalid] = np.nan
    return start, features, int(invalid.sum())


def build_feature_cache(workers: int, force: bool = False) -> dict[str, object]:
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    smiles_path = CACHE_ROOT / "smiles.json"
    groups_path = CACHE_ROOT / "molecule_groups.json"
    feature_path = CACHE_ROOT / "maplight.npy"
    metadata_path = CACHE_ROOT / "maplight_complete.json"

    if smiles_path.exists():
        smiles = json.loads(smiles_path.read_text(encoding="utf-8"))
    else:
        smiles = official_unique_smiles()
        write_json(smiles_path, smiles)

    official = official_unique_smiles()
    missing = sorted(set(official) - set(smiles))
    if missing:
        raise RuntimeError(
            f"{len(missing)} official TDC molecules are absent from smiles.json"
        )

    if not groups_path.exists():
        groups = [molecule_group(text) for text in smiles]
        write_json(groups_path, groups)
    groups = json.loads(groups_path.read_text(encoding="utf-8"))
    if len(groups) != len(smiles):
        raise RuntimeError("Molecule metadata is not aligned with smiles.json")

    if metadata_path.exists() and feature_path.exists() and not force:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if (
            metadata.get("count_dtype") == "int32"
            and metadata.get("sha256") == sha256(feature_path)
        ):
            return metadata

    reference = _reference_runtime()
    dimension = 1024 + 1024 + 315 + len(reference.get_chosen_descriptors())
    temporary = feature_path.with_suffix(".npy.tmp")
    output = np.lib.format.open_memmap(
        temporary,
        mode="w+",
        dtype=np.float32,
        shape=(len(smiles), dimension),
    )
    chunks = [
        (start, smiles[start : start + 64])
        for start in range(0, len(smiles), 64)
    ]
    started = time.time()
    processed = 0
    nonfinite = 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for start, features, bad_count in pool.map(feature_chunk, chunks):
            output[start : start + len(features)] = features
            processed += len(features)
            nonfinite += bad_count
            if processed % 2048 < 64 or processed == len(smiles):
                print(f"features {processed}/{len(smiles)}", flush=True)
    output.flush()
    del output
    temporary.replace(feature_path)
    metadata = {
        "shape": [len(smiles), dimension],
        "count_dtype": "int32",
        "nonfinite_replaced_with_nan": nonfinite,
        "sha256": sha256(feature_path),
        "elapsed_seconds": time.time() - started,
        "descriptors": reference.get_chosen_descriptors(),
        "source": "TDC ADMET Group, Harvard Dataverse file 4426004",
        "smiles_order_sha256": hashlib.sha256(
            "\n".join(smiles).encode()
        ).hexdigest(),
    }
    write_json(metadata_path, metadata)
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    metadata = build_feature_cache(args.workers, args.force)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

