from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem import rdFingerprintGenerator

from src.build_features import _fixed_count_to_array, _reference_runtime
from src.config import PROJECT_ROOT
from src.data import load_task_frames, write_json


RDLogger.DisableLog("rdApp.*")
EXTERNAL_ROOT = PROJECT_ROOT / "data" / "external"
PREPARED_ROOT = EXTERNAL_ROOT / "prepared"
CACHE_ROOT = EXTERNAL_ROOT / "cache"


def canonical_smiles(text: str) -> str | None:
    molecule = Chem.MolFromSmiles(str(text))
    if molecule is None:
        return None
    return Chem.MolToSmiles(molecule, isomericSmiles=False)


def _tdc_canonical_set(task: str) -> set[str]:
    frames = load_task_frames(task)
    values = pd.concat([frames.train_val, frames.test])["Drug"]
    return {canonical_smiles(text) for text in values} - {None}


def _deduplicate(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["canonical_smiles"] = frame["Drug"].map(canonical_smiles)
    frame = frame.dropna(subset=["canonical_smiles"]).drop_duplicates(
        "canonical_smiles", keep="first"
    )
    return frame.reset_index(drop=True)


def prepare_external_frames() -> dict[str, object]:
    PREPARED_ROOT.mkdir(parents=True, exist_ok=True)
    audits = {}

    herg = pd.read_csv(EXTERNAL_ROOT / "hERG_Dataset.csv")
    herg = herg[herg["USED_AS"].eq("Test-set")].copy()
    herg["Drug"] = herg["SMILES"].astype(str)
    herg["Y"] = (herg["PIC50"].astype(float) >= 4.5).astype(int)
    herg["source"] = "ToxTree hERG external test, PubChem/literature"
    herg = _deduplicate(herg)
    herg_overlap = _tdc_canonical_set("herg")
    before = len(herg)
    herg = herg[~herg["canonical_smiles"].isin(herg_overlap)].reset_index(drop=True)
    herg[
        ["Drug", "Y", "canonical_smiles", "source"]
    ].to_csv(PREPARED_ROOT / "herg.csv", index=False, encoding="utf-8-sig")
    audits["herg"] = {
        "source": "Zenodo 5807719 / ToxTree hERG external test",
        "source_sha256": hashlib.sha256(
            (EXTERNAL_ROOT / "hERG_Dataset.csv").read_bytes()
        ).hexdigest(),
        "label_rule": "PIC50 >= 4.5 (IC50 <= 30 uM)",
        "before_overlap": before,
        "removed_tdc_overlap": before - len(herg),
        "retained": len(herg),
        "positive_rate": float(herg["Y"].mean()),
    }

    b3db = pd.read_csv(EXTERNAL_ROOT / "B3DB_classification.tsv", sep="\t")
    b3db = b3db.dropna(subset=["SMILES", "BBB+/BBB-"]).copy()
    b3db["Drug"] = b3db["SMILES"].astype(str)
    b3db["Y"] = b3db["BBB+/BBB-"].map({"BBB+": 1, "BBB-": 0})
    b3db["source"] = "B3DB classification"
    b3db = b3db.dropna(subset=["Y"]).copy()
    b3db["Y"] = b3db["Y"].astype(int)
    b3db = _deduplicate(b3db)
    bbb_overlap = _tdc_canonical_set("bbb_martins")
    before = len(b3db)
    b3db = b3db[~b3db["canonical_smiles"].isin(bbb_overlap)].reset_index(drop=True)
    b3db[
        ["Drug", "Y", "canonical_smiles", "source"]
    ].to_csv(PREPARED_ROOT / "bbb_martins.csv", index=False, encoding="utf-8-sig")
    audits["bbb_martins"] = {
        "source": "B3DB classification dataset",
        "source_sha256": hashlib.sha256(
            (EXTERNAL_ROOT / "B3DB_classification.tsv").read_bytes()
        ).hexdigest(),
        "label_rule": "provider BBB+ / BBB- labels",
        "before_overlap": before,
        "removed_tdc_overlap": before - len(b3db),
        "retained": len(b3db),
        "positive_rate": float(b3db["Y"].mean()),
    }

    esol = pd.read_csv(EXTERNAL_ROOT / "delaney-processed.csv")
    esol["Drug"] = esol["smiles"].astype(str)
    esol = _deduplicate(esol)
    esol_overlap = _tdc_canonical_set("solubility_aqsoldb")
    retained_esol = esol[~esol["canonical_smiles"].isin(esol_overlap)]
    audits["solubility_aqsoldb"] = {
        "source": "DeepChem Delaney/ESOL",
        "retained": len(retained_esol),
        "removed_tdc_overlap": len(esol) - len(retained_esol),
        "status": "excluded: too few non-overlapping molecules",
    }
    write_json(EXTERNAL_ROOT / "external_audit.json", audits)
    return audits


def load_external(task: str) -> pd.DataFrame:
    path = PREPARED_ROOT / f"{task}.csv"
    if not path.exists():
        prepare_external_frames()
    if not path.exists():
        raise FileNotFoundError(f"External endpoint unavailable: {task}")
    return pd.read_csv(path, dtype={"Y": int})


def _morgan_features(smiles: list[str], n_bits: int = 512) -> np.ndarray:
    generator = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=n_bits)
    output = np.zeros((len(smiles), n_bits), dtype=np.float32)
    for index, text in enumerate(smiles):
        molecule = Chem.MolFromSmiles(text)
        if molecule is None:
            raise ValueError(f"Invalid external SMILES: {text}")
        values = np.zeros(n_bits, dtype=np.uint8)
        Chem.DataStructs.ConvertToNumpyArray(generator.GetFingerprint(molecule), values)
        output[index] = values
    return output


def external_features(task: str, base: str) -> np.ndarray:
    frame = load_external(task)
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    path = CACHE_ROOT / f"{task}_{base}.npy"
    if path.exists():
        values = np.load(path, mmap_mode="r")
        if values.shape[0] == len(frame):
            return np.asarray(values, dtype=np.float32)
        raise RuntimeError(f"External feature cache shape mismatch: {path}")
    smiles = frame["Drug"].astype(str).tolist()
    if base == "extra_trees":
        output = _morgan_features(smiles)
    elif base == "catboost":
        reference = _reference_runtime()
        reference.count_to_array = _fixed_count_to_array
        with np.errstate(over="ignore", invalid="ignore"):
            features = reference.get_fingerprints(pd.Series(smiles)).astype(np.float32)
        features[~np.isfinite(features)] = np.nan
        output = features
    else:
        raise ValueError(base)
    np.save(path, output, allow_pickle=False)
    return output


if __name__ == "__main__":
    print(json.dumps(prepare_external_frames(), ensure_ascii=False, indent=2))

