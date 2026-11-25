from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors, rdFingerprintGenerator
from sklearn.decomposition import PCA, TruncatedSVD
from sklearn.preprocessing import StandardScaler

from src.config import RESULTS_ROOT, TASK_BY_NAME
from src.data import load_task_frames, write_json
from src.external_data import load_external


RDLogger.DisableLog("rdApp.*")
OUTPUT_ROOT = RESULTS_ROOT / "manuscript" / "tables"
PROJECTION_SAMPLE_SIZE = 3000
RANDOM_SEED = 20261125


def _canonical_molecule(text: str) -> tuple[Chem.Mol | None, str | None]:
    try:
        molecule = Chem.MolFromSmiles(str(text))
    except Exception:
        return None, None
    if molecule is None or molecule.GetNumAtoms() == 0:
        return None, None
    return molecule, Chem.MolToSmiles(
        molecule,
        isomericSmiles=False,
        canonical=True,
    )


def _descriptor_rows(molecule: Chem.Mol, canonical: str, cohort: str):
    return {
        "canonical_smiles": canonical,
        "cohort": cohort,
        "molecular_weight": float(Descriptors.MolWt(molecule)),
        "clogp": float(Descriptors.MolLogP(molecule)),
        "tpsa": float(Descriptors.TPSA(molecule)),
    }


def _tdc_molecules() -> tuple[pd.DataFrame, list[Chem.Mol]]:
    seen = set()
    rows = []
    molecules = []
    for task in TASK_BY_NAME:
        frames = load_task_frames(task)
        for text in pd.concat(
            [frames.train_val["Drug"], frames.test["Drug"]],
            ignore_index=True,
        ).astype(str):
            molecule, canonical = _canonical_molecule(text)
            if molecule is None or canonical in seen:
                continue
            seen.add(canonical)
            rows.append(_descriptor_rows(molecule, canonical, "TDC ADMET"))
            molecules.append(molecule)
    return pd.DataFrame(rows), molecules


def _external_molecules(task: str, cohort: str) -> tuple[pd.DataFrame, list[Chem.Mol]]:
    frame = load_external(task)
    rows = []
    molecules = []
    for text in frame["Drug"].astype(str):
        molecule, canonical = _canonical_molecule(text)
        if molecule is None:
            continue
        rows.append(_descriptor_rows(molecule, canonical, cohort))
        molecules.append(molecule)
    return pd.DataFrame(rows), molecules


def _projection(
    cohort_frames: dict[str, tuple[pd.DataFrame, list[Chem.Mol]]],
) -> tuple[pd.DataFrame, dict[str, object]]:
    generator = rdFingerprintGenerator.GetMorganGenerator(
        radius=2,
        fpSize=1024,
    )
    rng = np.random.default_rng(RANDOM_SEED)
    selected_indices: dict[str, np.ndarray] = {}
    for cohort, (_, molecules) in cohort_frames.items():
        count = len(molecules)
        target = (
            min(PROJECTION_SAMPLE_SIZE, count)
            if cohort == "TDC ADMET"
            else min(500, count)
        )
        selected_indices[cohort] = np.sort(
            rng.choice(count, size=target, replace=False)
        )

    selected_molecules = []
    selected_rows = []
    for cohort, (frame, molecules) in cohort_frames.items():
        indices = selected_indices[cohort]
        selected_molecules.extend(molecules[index] for index in indices)
        subset = frame.iloc[indices].copy()
        subset["source_row"] = indices
        selected_rows.append(subset)
    matrix = np.zeros((len(selected_molecules), 1024), dtype=np.float32)
    for index, molecule in enumerate(selected_molecules):
        Chem.DataStructs.ConvertToNumpyArray(
            generator.GetFingerprint(molecule),
            matrix[index],
        )
    if matrix.size == 0:
        raise RuntimeError("No molecules available for chemical-space projection")

    component_count = min(20, matrix.shape[0] - 1, matrix.shape[1] - 1)
    reduced = TruncatedSVD(
        n_components=component_count,
        random_state=RANDOM_SEED,
    ).fit_transform(matrix)
    reduced = StandardScaler().fit_transform(reduced)
    coordinates = PCA(n_components=2, random_state=RANDOM_SEED).fit_transform(
        reduced
    )
    combined = pd.concat(selected_rows, ignore_index=True)
    combined["pc1"] = coordinates[:, 0]
    combined["pc2"] = coordinates[:, 1]
    metadata = {
        "fingerprint": "Morgan radius 2, 1024 bits",
        "projection": (
            "TruncatedSVD to 20 components, standardization, then two-component PCA"
        ),
        "random_seed": RANDOM_SEED,
        "sample_sizes": {
            cohort: int(len(indices))
            for cohort, indices in selected_indices.items()
        },
    }
    return combined[
        [
            "cohort",
            "source_row",
            "pc1",
            "pc2",
            "molecular_weight",
            "clogp",
            "tpsa",
        ]
    ], metadata


def build_chemical_space_assets() -> dict[str, object]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    tdc, tdc_molecules = _tdc_molecules()
    herg, herg_molecules = _external_molecules("herg", "External hERG")
    bbb, bbb_molecules = _external_molecules(
        "bbb_martins",
        "External B3DB BBB",
    )
    descriptors = pd.concat([tdc, herg, bbb], ignore_index=True)
    descriptors.to_csv(
        OUTPUT_ROOT / "chemical_space_descriptors.csv",
        index=False,
        encoding="utf-8-sig",
    )
    projection, projection_metadata = _projection(
        {
            "TDC ADMET": (tdc, tdc_molecules),
            "External hERG": (herg, herg_molecules),
            "External B3DB BBB": (bbb, bbb_molecules),
        }
    )
    projection.to_csv(
        OUTPUT_ROOT / "chemical_space_projection.csv",
        index=False,
        encoding="utf-8-sig",
    )

    summary_rows = []
    for cohort, frame in descriptors.groupby("cohort", sort=False):
        row: dict[str, object] = {
            "cohort": cohort,
            "n_molecules": int(len(frame)),
        }
        for column in ("molecular_weight", "clogp", "tpsa"):
            row[f"{column}_median"] = float(frame[column].median())
            row[f"{column}_q25"] = float(frame[column].quantile(0.25))
            row[f"{column}_q75"] = float(frame[column].quantile(0.75))
        summary_rows.append(row)
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(
        OUTPUT_ROOT / "chemical_space_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    metadata = {
        **projection_metadata,
        "descriptor_counts": {
            row["cohort"]: int(row["n_molecules"])
            for row in summary_rows
        },
        "descriptors": ["MolWt", "MolLogP", "TPSA"],
    }
    write_json(OUTPUT_ROOT / "chemical_space_manifest.json", metadata)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return metadata


if __name__ == "__main__":
    build_chemical_space_assets()
