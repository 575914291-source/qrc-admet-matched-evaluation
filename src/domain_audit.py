from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import rdFingerprintGenerator
from rdkit.Chem.Scaffolds import MurckoScaffold

from src.config import RESULTS_ROOT, SPLIT_SEEDS, TASK_BY_NAME
from src.data import load_task_frames, write_json
from src.external_data import load_external
from src.fast_metrics import metric_value


RDLogger.DisableLog("rdApp.*")
EXTERNAL_ROOT = RESULTS_ROOT / "external_validation"
OUTPUT_ROOT = RESULTS_ROOT / "domain_audit"
ACYCLIC_KEY = "<ACYCLIC>"
TASKS = ("herg", "bbb_martins")


def _parse_molecule(text: object) -> Chem.Mol | None:
    try:
        molecule = Chem.MolFromSmiles(str(text))
    except Exception:
        return None
    return molecule if molecule is not None and molecule.GetNumAtoms() > 0 else None


def _canonical_smiles(molecule: Chem.Mol) -> str:
    return Chem.MolToSmiles(molecule, isomericSmiles=False, canonical=True)


def _murcko_scaffold(molecule: Chem.Mol) -> str:
    try:
        value = MurckoScaffold.MurckoScaffoldSmiles(
            mol=molecule,
            includeChirality=False,
        )
    except Exception:
        return ""
    return value or ACYCLIC_KEY


def _fingerprint_generator():
    return rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)


def _reference_molecules(task: str) -> dict[str, object]:
    frames = load_task_frames(task)
    trainval = frames.train_val
    all_records = pd.concat(
        [frames.train_val, frames.test],
        ignore_index=True,
    )
    generator = _fingerprint_generator()

    def collect(frame: pd.DataFrame):
        molecules = []
        canonical = []
        scaffolds = []
        for text in frame["Drug"].astype(str):
            molecule = _parse_molecule(text)
            if molecule is None:
                continue
            molecules.append(molecule)
            canonical.append(_canonical_smiles(molecule))
            scaffolds.append(_murcko_scaffold(molecule))
        fingerprints = generator.GetFingerprints(molecules, numThreads=0)
        return {
            "molecules": molecules,
            "canonical": set(canonical),
            "scaffolds": {
                value
                for value in scaffolds
                if value and value != ACYCLIC_KEY
            },
            "fingerprints": fingerprints,
        }

    return {
        "trainval": collect(trainval),
        "all": collect(all_records),
    }


def _nearest_similarities(
    molecules: list[Chem.Mol],
    reference_fingerprints: list,
) -> np.ndarray:
    generator = _fingerprint_generator()
    values = np.empty(len(molecules), dtype=np.float64)
    for start in range(0, len(molecules), 128):
        batch = generator.GetFingerprints(
            molecules[start : start + 128],
            numThreads=0,
        )
        for offset, fingerprint in enumerate(batch):
            similarities = DataStructs.BulkTanimotoSimilarity(
                fingerprint,
                reference_fingerprints,
            )
            values[start + offset] = (
                float(max(similarities)) if similarities else np.nan
            )
    return values


def _external_molecular_table(task: str) -> pd.DataFrame:
    external = load_external(task)
    reference = _reference_molecules(task)
    rows = []
    molecules = []
    for row in external.itertuples(index=False):
        molecule = _parse_molecule(row.Drug)
        if molecule is None:
            continue
        canonical = _canonical_smiles(molecule)
        scaffold = _murcko_scaffold(molecule)
        molecules.append(molecule)
        rows.append(
            {
                "row_index": len(rows),
                "y": int(row.Y),
                "canonical_smiles": canonical,
                "scaffold": scaffold,
                "exact_overlap_tdc_all": canonical
                in reference["all"]["canonical"],
                "scaffold_overlap_tdc_all": scaffold != ACYCLIC_KEY
                and scaffold in reference["all"]["scaffolds"],
                "exact_overlap_tdc_trainval": canonical
                in reference["trainval"]["canonical"],
                "scaffold_overlap_tdc_trainval": scaffold != ACYCLIC_KEY
                and scaffold in reference["trainval"]["scaffolds"],
            }
        )
    frame = pd.DataFrame(rows)
    frame["nearest_tanimoto_tdc_all"] = _nearest_similarities(
        molecules,
        reference["all"]["fingerprints"],
    )
    frame["nearest_tanimoto_tdc_trainval"] = _nearest_similarities(
        molecules,
        reference["trainval"]["fingerprints"],
    )
    frame["source"] = external["source"].astype(str)
    frame["task"] = task
    return frame


def _chemical_group(frame: pd.DataFrame) -> np.ndarray:
    groups = np.full(len(frame), "novel_scaffold", dtype=object)
    groups[
        frame["scaffold_overlap_tdc_trainval"].to_numpy(dtype=bool)
    ] = "shared_scaffold"
    groups[frame["scaffold"].eq(ACYCLIC_KEY).to_numpy()] = "acyclic"
    return groups


def _summary_row(task: str, frame: pd.DataFrame) -> dict[str, object]:
    tdc_frames = load_task_frames(task)
    tdc_all_y = pd.concat(
        [tdc_frames.train_val["Y"], tdc_frames.test["Y"]],
        ignore_index=True,
    )
    similarity = frame["nearest_tanimoto_tdc_trainval"]
    quantiles = similarity.quantile([0.25, 0.5, 0.75, 0.9])
    return {
        "task": task,
        "source": str(frame["source"].iloc[0]),
        "n_external": int(len(frame)),
        "n_positive": int(frame["y"].sum()),
        "positive_rate": float(frame["y"].mean()),
        "tdc_positive_rate_all": float(tdc_all_y.mean()),
        "positive_rate_difference": float(
            frame["y"].mean() - tdc_all_y.mean()
        ),
        "n_unique_scaffolds": int(frame["scaffold"].nunique()),
        "n_acyclic": int(frame["scaffold"].eq(ACYCLIC_KEY).sum()),
        "n_exact_overlap_tdc_all": int(
            frame["exact_overlap_tdc_all"].sum()
        ),
        "n_scaffold_overlap_tdc_all": int(
            frame["scaffold_overlap_tdc_all"].sum()
        ),
        "pct_scaffold_overlap_tdc_all": float(
            100 * frame["scaffold_overlap_tdc_all"].mean()
        ),
        "n_scaffold_overlap_tdc_trainval": int(
            frame["scaffold_overlap_tdc_trainval"].sum()
        ),
        "pct_scaffold_overlap_tdc_trainval": float(
            100 * frame["scaffold_overlap_tdc_trainval"].mean()
        ),
        "nearest_tanimoto_min": float(similarity.min()),
        "nearest_tanimoto_q25": float(quantiles.loc[0.25]),
        "nearest_tanimoto_median": float(quantiles.loc[0.5]),
        "nearest_tanimoto_q75": float(quantiles.loc[0.75]),
        "nearest_tanimoto_q90": float(quantiles.loc[0.9]),
        "nearest_tanimoto_max": float(similarity.max()),
        "fingerprint": "Morgan radius 2, 2048 bits",
        "scaffold_definition": "Bemis-Murcko, non-isomeric",
    }


def _prediction_arrays(base: str, task: str) -> list[dict[str, np.ndarray]]:
    values = []
    for seed in SPLIT_SEEDS:
        path = EXTERNAL_ROOT / base / task / f"split_{seed}.npz"
        with np.load(path, allow_pickle=False) as archive:
            values.append(
                {
                    name: np.asarray(archive[name])
                    for name in (
                        "y",
                        "scaffold",
                        "base",
                        "qrc_gated",
                        "orth_gated",
                    )
                }
            )
    return values


def _model_subgroup_rows(
    task: str,
    frame: pd.DataFrame,
) -> list[dict[str, object]]:
    chemical_groups = _chemical_group(frame)
    similarity = frame["nearest_tanimoto_tdc_trainval"].to_numpy()
    top_quartile_cutoff = float(np.quantile(similarity, 0.75))
    analysis_groups = {
        "all": np.ones(len(frame), dtype=bool),
        "shared_scaffold": chemical_groups == "shared_scaffold",
        "novel_scaffold": chemical_groups == "novel_scaffold",
        "acyclic": chemical_groups == "acyclic",
        "nearest_similarity_top_quartile": similarity >= top_quartile_cutoff,
        "nearest_similarity_lower_three_quartiles": (
            similarity < top_quartile_cutoff
        ),
    }
    rows = []
    for base in ("extra_trees", "catboost"):
        splits = _prediction_arrays(base, task)
        for group_name, mask in analysis_groups.items():
            truth = splits[0]["y"][mask]
            scaffolds = splits[0]["scaffold"][mask]
            counts = np.bincount(truth.astype(int), minlength=2)
            effects = []
            qrc_scores = []
            orth_scores = []
            base_scores = []
            if len(counts) == 2 and counts[0] > 0 and counts[1] > 0:
                for values in splits:
                    qrc = metric_value("AUROC", truth, values["qrc_gated"][mask])
                    orth = metric_value("AUROC", truth, values["orth_gated"][mask])
                    base_score = metric_value("AUROC", truth, values["base"][mask])
                    qrc_scores.append(qrc)
                    orth_scores.append(orth)
                    base_scores.append(base_score)
                    effects.append(qrc - orth)
            rows.append(
                {
                    "task": task,
                    "base": base,
                    "subgroup": group_name,
                    "n": int(mask.sum()),
                    "n_positive": int(counts[1]),
                    "n_negative": int(counts[0]),
                    "n_scaffolds": int(len(np.unique(scaffolds))),
                    "top_quartile_cutoff": top_quartile_cutoff,
                    "base_mean_auroc": (
                        float(np.mean(base_scores)) if base_scores else np.nan
                    ),
                    "qrc_gated_mean_auroc": (
                        float(np.mean(qrc_scores)) if qrc_scores else np.nan
                    ),
                    "orth_gated_mean_auroc": (
                        float(np.mean(orth_scores)) if orth_scores else np.nan
                    ),
                    "qrc_minus_orth_mean": (
                        float(np.mean(effects)) if effects else np.nan
                    ),
                    "qrc_minus_orth_min": (
                        float(np.min(effects)) if effects else np.nan
                    ),
                    "qrc_minus_orth_max": (
                        float(np.max(effects)) if effects else np.nan
                    ),
                    "positive_splits": int(sum(value > 0 for value in effects)),
                    "defined_splits": int(len(effects)),
                }
            )
    return rows


def build_domain_audit() -> dict[str, object]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    summaries = []
    subgroup_rows = []
    for task in TASKS:
        if task not in TASK_BY_NAME:
            raise KeyError(f"Unknown TDC task: {task}")
        frame = _external_molecular_table(task)
        if frame["exact_overlap_tdc_all"].any():
            raise RuntimeError(
                f"{task} contains exact TDC overlaps after preparation"
            )
        frame.to_csv(
            OUTPUT_ROOT / f"{task}_molecules.csv",
            index=False,
            encoding="utf-8-sig",
        )
        summaries.append(_summary_row(task, frame))
        subgroup_rows.extend(_model_subgroup_rows(task, frame))

    summary = pd.DataFrame(summaries)
    summary.to_csv(
        OUTPUT_ROOT / "domain_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    subgroups = pd.DataFrame(subgroup_rows)
    subgroups.to_csv(
        OUTPUT_ROOT / "model_subgroups.csv",
        index=False,
        encoding="utf-8-sig",
    )

    result = {
        "purpose": (
            "Descriptive chemical-space and source-proximity audit of the two "
            "external cohorts. Subgroup model results are exploratory and are "
            "not used for model selection or causal attribution."
        ),
        "tasks": {
            row["task"]: row
            for row in summary.to_dict(orient="records")
        },
        "analysis_groups": {
            "shared_scaffold": (
                "non-acyclic Murcko scaffold present in official TDC "
                "train/validation records for the same endpoint"
            ),
            "novel_scaffold": (
                "non-acyclic Murcko scaffold absent from official TDC "
                "train/validation records for the same endpoint"
            ),
            "acyclic": "Murcko scaffold is empty",
            "nearest_similarity_top_quartile": (
                "top 25% of nearest Morgan Tanimoto similarity to TDC "
                "train/validation molecules within each external cohort"
            ),
        },
        "caveat": (
            "Scaffold overlap and nearest-neighbor similarity describe source "
            "proximity only. They do not establish a causal chemical mechanism "
            "for endpoint-specific prediction differences."
        ),
    }
    write_json(OUTPUT_ROOT / "domain_summary.json", result)
    print(summary.to_string(index=False))
    print("\nSubgroup model audit:")
    print(subgroups.to_string(index=False))
    return result


if __name__ == "__main__":
    build_domain_audit()
