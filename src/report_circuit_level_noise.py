from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

from src.config import CIRCUIT_TASKS, PROJECT_ROOT, RESULTS_ROOT
from src.data import write_json


OUTPUT_ROOT = RESULTS_ROOT / "circuit_level_noise"
MANUSCRIPT_FIGURE_ROOT = RESULTS_ROOT / "manuscript" / "figures"
MANUSCRIPT_TABLE_ROOT = RESULTS_ROOT / "manuscript" / "tables"
PROFILES = ("ideal_circuit", "noisy_low", "noisy_medium", "noisy_high")


def build_report() -> pd.DataFrame:
    rows = []
    for task in CIRCUIT_TASKS:
        with np.load(OUTPUT_ROOT / f"{task}.npz", allow_pickle=False) as values:
            exact = np.asarray(values["exact"])
            datasets = {
                "ideal_circuit": np.asarray(values["ideal_circuit"]),
                "noisy_low": np.asarray(values["noisy_low"]),
                "noisy_medium": np.asarray(values["noisy_medium"]),
                "noisy_high": np.asarray(values["noisy_high"]),
            }
        for profile, observed in datasets.items():
            exact_flat = exact.reshape(-1)
            observed_flat = observed.reshape(-1)
            difference = observed - exact
            slope = float(
                np.dot(exact_flat, observed_flat)
                / np.dot(exact_flat, exact_flat)
            )
            rows.append(
                {
                    "task": task,
                    "profile": profile,
                    "states": exact.shape[1],
                    "maps": exact.shape[0],
                    "rmse": float(np.sqrt(np.mean(difference**2))),
                    "mae": float(np.mean(np.abs(difference))),
                    "max_abs_error": float(np.max(np.abs(difference))),
                    "normalized_rmse": float(
                        np.sqrt(np.mean(difference**2))
                        / np.sqrt(np.mean(exact_flat**2))
                    ),
                    "pearson": float(pearsonr(exact_flat, observed_flat).statistic),
                    "spearman": float(
                        spearmanr(exact_flat, observed_flat).statistic
                    ),
                    "signal_slope": slope,
                }
            )
    frame = pd.DataFrame(rows)
    frame.to_csv(
        OUTPUT_ROOT / "summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    MANUSCRIPT_TABLE_ROOT.mkdir(parents=True, exist_ok=True)
    frame.to_csv(
        MANUSCRIPT_TABLE_ROOT / "circuit_level_noise.csv",
        index=False,
        encoding="utf-8-sig",
    )

    figure, axes = plt.subplots(1, 2, figsize=(8.0, 3.4))
    labels = ["Ideal", "Low", "Medium", "High"]
    for axis, metric, ylabel in (
        (axes[0], "normalized_rmse", "Normalized RMSE"),
        (axes[1], "spearman", "Spearman correlation"),
    ):
        values = [
            frame[frame.profile == profile][metric].to_numpy()
            for profile in PROFILES
        ]
        axis.boxplot(values, tick_labels=labels, widths=0.55)
        axis.set_ylabel(ylabel)
        axis.grid(axis="y", alpha=0.2)
    figure.suptitle("Circuit-level readout fidelity")
    figure.tight_layout()
    figure.savefig(OUTPUT_ROOT / "figure_circuit_noise.png", dpi=300)
    figure.savefig(OUTPUT_ROOT / "figure_circuit_noise.pdf")
    MANUSCRIPT_FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    figure.savefig(
        MANUSCRIPT_FIGURE_ROOT / "figureS5_circuit_noise.png",
        dpi=300,
    )
    figure.savefig(
        MANUSCRIPT_FIGURE_ROOT / "figureS5_circuit_noise.pdf",
    )
    shutil.copy2(
        MANUSCRIPT_FIGURE_ROOT / "figureS5_circuit_noise.pdf",
        PROJECT_ROOT / "outputs" / "Supplementary_FigureS5_Circuit_Noise.pdf",
    )
    plt.close(figure)

    write_json(
        OUTPUT_ROOT / "report_manifest.json",
        {
            "tasks": list(CIRCUIT_TASKS),
            "profiles": list(PROFILES),
            "states_per_task": 32,
            "maps": 5,
            "base_representation": "MapLight-CatBoost PCA",
            "analysis": (
                "Circuit-level readout fidelity under gate depolarizing and "
                "readout bit-flip errors; this is not a hardware experiment."
            ),
        },
    )
    return frame


if __name__ == "__main__":
    print(build_report().to_string(index=False))
