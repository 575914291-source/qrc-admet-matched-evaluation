from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import RESULTS_ROOT, SPLIT_SEEDS
from src.data import write_json
from src.fast_metrics import metric_value


DOMAIN_ROOT = RESULTS_ROOT / "domain_audit"
EXTERNAL_ROOT = RESULTS_ROOT / "external_validation"
OUTPUT_ROOT = RESULTS_ROOT / "source_gradient"


def _bins() -> dict[str, pd.DataFrame]:
    result = {}
    for task in ("herg", "bbb_martins"):
        frame = pd.read_csv(
            DOMAIN_ROOT / f"{task}_molecules.csv",
            encoding="utf-8-sig",
        )
        frame["similarity_quartile"] = pd.qcut(
            frame["nearest_tanimoto_tdc_trainval"],
            q=4,
            labels=False,
            duplicates="drop",
        )
        result[task] = frame
    return result


def _per_bin_rows(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for task, frame in frames.items():
        similarity = frame["nearest_tanimoto_tdc_trainval"].to_numpy()
        for base in ("extra_trees", "catboost"):
            for seed in SPLIT_SEEDS:
                path = EXTERNAL_ROOT / base / task / f"split_{seed}.npz"
                with np.load(path, allow_pickle=False) as archive:
                    values = {
                        name: np.asarray(archive[name])
                        for name in archive.files
                    }
                if len(values["y"]) != len(frame):
                    raise RuntimeError(f"External row misalignment: {path}")
                groups = {
                    f"Q{quartile + 1}": (
                        frame["similarity_quartile"].to_numpy() == quartile
                    )
                    for quartile in sorted(
                        frame["similarity_quartile"].dropna().unique()
                    )
                }
                groups["shared_scaffold"] = frame[
                    "scaffold_overlap_tdc_trainval"
                ].to_numpy(dtype=bool)
                groups["novel_scaffold"] = ~groups["shared_scaffold"]
                for group, mask in groups.items():
                    truth = values["y"][mask]
                    if len(np.unique(truth)) != 2:
                        continue
                    qrc = metric_value("AUROC", truth, values["qrc_ungated"][mask])
                    orth = metric_value(
                        "AUROC", truth, values["orth_ungated"][mask]
                    )
                    base_score = metric_value(
                        "AUROC", truth, values["base"][mask]
                    )
                    rows.append(
                        {
                            "task": task,
                            "base": base,
                            "split_seed": seed,
                            "similarity_group": group,
                            "n": int(mask.sum()),
                            "n_positive": int(truth.sum()),
                            "similarity_min": float(similarity[mask].min()),
                            "similarity_median": float(
                                np.median(similarity[mask])
                            ),
                            "similarity_max": float(similarity[mask].max()),
                            "base_auroc": base_score,
                            "qrc_auroc": qrc,
                            "orth_auroc": orth,
                            "qrc_minus_base": qrc - base_score,
                            "orth_minus_base": orth - base_score,
                            "qrc_specific": qrc - orth,
                        }
                    )
    return pd.DataFrame(rows)


def _summarize(rows: pd.DataFrame) -> pd.DataFrame:
    records = []
    for (task, base, group), subset in rows.groupby(
        ["task", "base", "similarity_group"]
    ):
        effect = subset["qrc_specific"].to_numpy()
        standard_error = effect.std(ddof=1) / np.sqrt(len(effect))
        records.append(
            {
                "task": task,
                "base": base,
                "similarity_group": group,
                "n": int(subset["n"].median()),
                "similarity_median": float(
                    subset["similarity_median"].mean()
                ),
                "qrc_specific_mean": float(effect.mean()),
                "qrc_specific_sd": float(effect.std(ddof=1)),
                "ci_low": float(effect.mean() - 1.96 * standard_error),
                "ci_high": float(effect.mean() + 1.96 * standard_error),
                "positive_splits": int((effect > 0).sum()),
                "n_splits": int(len(effect)),
            }
        )
    return pd.DataFrame(records).sort_values(
        ["task", "base", "similarity_group"]
    )


def _plot(summary: pd.DataFrame) -> None:
    quartiles = summary[
        summary["similarity_group"].isin(["Q1", "Q2", "Q3", "Q4"])
    ]
    colors = {"extra_trees": "#5B9BD5", "catboost": "#8B1E3F"}
    tasks = ("herg", "bbb_martins")
    figure, axes = plt.subplots(1, 2, figsize=(8.2, 3.8), sharey=True)
    for axis, task in zip(axes, tasks, strict=True):
        for base in ("extra_trees", "catboost"):
            subset = quartiles[
                quartiles["task"].eq(task) & quartiles["base"].eq(base)
            ].sort_values("similarity_group")
            x = np.arange(len(subset))
            axis.errorbar(
                x,
                subset["qrc_specific_mean"],
                yerr=np.vstack(
                    [
                        subset["qrc_specific_mean"] - subset["ci_low"],
                        subset["ci_high"] - subset["qrc_specific_mean"],
                    ]
                ),
                marker="o",
                linewidth=1.2,
                capsize=3,
                color=colors[base],
                label=base.replace("_", " ").title(),
            )
        axis.axhline(0.0, color="#444444", linewidth=0.8)
        axis.set_xticks(np.arange(4))
        axis.set_xticklabels(["Q1", "Q2", "Q3", "Q4"])
        axis.set_title(
            "hERG" if task == "herg" else "B3DB BBB",
            fontsize=10,
        )
        axis.set_xlabel("Nearest-TDC similarity quartile")
        axis.grid(color="#E5E7EB", linewidth=0.6)
    axes[0].set_ylabel("QRC minus matched orthogonal AUROC")
    axes[1].legend(frameon=False, fontsize=8)
    figure.tight_layout()
    figure.savefig(OUTPUT_ROOT / "source_gradient.png", dpi=600)
    figure.savefig(OUTPUT_ROOT / "source_gradient.pdf", bbox_inches="tight")
    plt.close(figure)


def analyze() -> dict[str, object]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    frames = _bins()
    rows = _per_bin_rows(frames)
    summary = _summarize(rows)
    rows.to_csv(
        OUTPUT_ROOT / "effects_by_split.csv",
        index=False,
        encoding="utf-8-sig",
    )
    summary.to_csv(
        OUTPUT_ROOT / "summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    _plot(summary)
    result = {
        "status": "passed",
        "purpose": (
            "Stratify external QRC-specific effects by nearest-TDC chemical "
            "similarity and scaffold overlap."
        ),
        "tasks": ["herg", "bbb_martins"],
        "bases": ["extra_trees", "catboost"],
        "rows": int(len(rows)),
        "quartile_sizes": {
            task: {
                str(int(index)): int(count)
                for index, count in frame["similarity_quartile"]
                .value_counts()
                .sort_index()
                .items()
            }
            for task, frame in frames.items()
        },
    }
    write_json(OUTPUT_ROOT / "summary.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(analyze(), ensure_ascii=False, indent=2))
