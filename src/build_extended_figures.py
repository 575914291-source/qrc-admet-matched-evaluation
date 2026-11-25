from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import RESULTS_ROOT


ASSET_ROOT = RESULTS_ROOT / "manuscript"
FIGURE_ROOT = ASSET_ROOT / "figures"
TABLE_ROOT = ASSET_ROOT / "tables"
DIAGNOSTIC_ROOT = RESULTS_ROOT / "external_diagnostics"

PALETTE = {
    "TDC ADMET": "#999999",
    "External hERG": "#D55E00",
    "External B3DB BBB": "#0072B2",
    "qrc_gated": "#D55E00",
    "orthogonal_gated": "#0072B2",
    "base": "#666666",
}
COHORT_LABELS = {
    "TDC ADMET": "TDC ADMET",
    "External hERG": "External hERG",
    "External B3DB BBB": "B3DB BBB",
}


def _style_axis(axis) -> None:
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.tick_params(labelsize=7, width=0.7)
    axis.grid(alpha=0.18, linewidth=0.6)


def _panel_label(axis, label: str) -> None:
    axis.text(
        -0.12,
        1.04,
        label,
        transform=axis.transAxes,
        fontsize=10,
        fontweight="bold",
        ha="left",
        va="bottom",
    )


def build_chemical_space_figure() -> Path:
    projection = pd.read_csv(
        TABLE_ROOT / "chemical_space_projection.csv",
        encoding="utf-8-sig",
    )
    descriptors = pd.read_csv(
        TABLE_ROOT / "chemical_space_descriptors.csv",
        encoding="utf-8-sig",
    )
    cohorts = ["TDC ADMET", "External hERG", "External B3DB BBB"]
    figure, axes = plt.subplots(
        2,
        2,
        figsize=(7.1, 6.2),
        constrained_layout=True,
    )
    scatter_axis = axes[0, 0]
    for cohort in cohorts:
        subset = projection[projection.cohort == cohort]
        scatter_axis.scatter(
            subset.pc1,
            subset.pc2,
            s=6 if cohort == "TDC ADMET" else 10,
            alpha=0.12 if cohort == "TDC ADMET" else 0.55,
            color=PALETTE[cohort],
            linewidths=0,
            rasterized=True,
            label=COHORT_LABELS[cohort],
        )
    scatter_axis.set_xlabel("Chemical-space component 1", fontsize=8)
    scatter_axis.set_ylabel("Chemical-space component 2", fontsize=8)
    scatter_axis.legend(
        frameon=False,
        fontsize=7,
        markerscale=2.2,
        loc="best",
    )
    scatter_axis.set_title("Morgan fingerprint projection", fontsize=9)
    _panel_label(scatter_axis, "A")
    _style_axis(scatter_axis)

    descriptor_specs = (
        ("molecular_weight", "Molecular weight (Da)", "B"),
        ("clogp", "cLogP", "C"),
        ("tpsa", "TPSA (A^2)", "D"),
    )
    for axis, (column, label, panel) in zip(
        axes.flat[1:],
        descriptor_specs,
        strict=True,
    ):
        values = [
            descriptors.loc[descriptors.cohort == cohort, column].dropna().to_numpy()
            for cohort in cohorts
        ]
        boxes = axis.boxplot(
            values,
            patch_artist=True,
            widths=0.58,
            showfliers=False,
            medianprops={"color": "black", "linewidth": 0.9},
            whiskerprops={"linewidth": 0.7},
            capprops={"linewidth": 0.7},
            boxprops={"linewidth": 0.7},
        )
        for patch, cohort in zip(boxes["boxes"], cohorts, strict=True):
            patch.set_facecolor(PALETTE[cohort])
            patch.set_alpha(0.7)
        axis.set_xticks(np.arange(1, 4))
        axis.set_xticklabels(["TDC", "hERG", "BBB"], fontsize=7)
        axis.set_ylabel(label, fontsize=8)
        _panel_label(axis, panel)
        _style_axis(axis)
    figure.suptitle(
        "Chemical-space and applicability-domain context",
        fontsize=11,
    )
    png = FIGURE_ROOT / "figure2_chemical_space.png"
    pdf = FIGURE_ROOT / "figure2_chemical_space.pdf"
    figure.savefig(png, dpi=600, bbox_inches="tight")
    figure.savefig(pdf, bbox_inches="tight")
    plt.close(figure)
    return png


def build_external_diagnostics_figure() -> Path:
    summary = pd.read_csv(
        DIAGNOSTIC_ROOT / "summary.csv",
        encoding="utf-8-sig",
    )
    calibration = pd.read_csv(
        DIAGNOSTIC_ROOT / "calibration_curves.csv",
        encoding="utf-8-sig",
    )
    figure, axes = plt.subplots(
        2,
        2,
        figsize=(7.2, 6.0),
        constrained_layout=True,
    )
    contrasts = [
        ("qrc_gated", "base", "QRC vs base"),
        ("orthogonal_gated", "base", "Orthogonal vs base"),
        ("qrc_gated", "orthogonal_gated", "QRC vs orthogonal"),
    ]
    colors = ["#D55E00", "#0072B2", "#009E73"]
    labels = {
        "extra_trees": "ExtraTrees",
        "catboost": "CatBoost",
    }
    for axis, task, title, panel in (
        (axes[0, 0], "herg", "hERG AUROC decomposition", "A"),
        (axes[0, 1], "bbb_martins", "B3DB BBB AUROC decomposition", "B"),
    ):
        subset = summary[
            (summary.task == task)
            & (summary.metric == "AUROC")
            & summary.method.isin([value[0] for value in contrasts])
        ]
        x = np.arange(2, dtype=float)
        width = 0.23
        for offset, (method, reference, label), color in zip(
            (-width, 0, width),
            contrasts,
            colors,
            strict=True,
        ):
            values = [
                subset[
                    (subset.base == base)
                    & (subset.method == method)
                    & (subset.reference == reference)
                ].effect_better_positive.iloc[0]
                for base in ("extra_trees", "catboost")
            ]
            axis.bar(
                x + offset,
                values,
                width=width,
                color=color,
                label=label,
            )
        axis.axhline(0, color="black", linewidth=0.7)
        axis.set_xticks(x)
        axis.set_xticklabels([labels["extra_trees"], labels["catboost"]])
        axis.set_ylabel("AUROC difference", fontsize=8)
        axis.set_title(title, fontsize=9)
        _panel_label(axis, panel)
        _style_axis(axis)
        if panel == "A":
            axis.legend(frameon=False, fontsize=6.5, ncol=1, loc="upper left")

    for axis, task, title, panel in (
        (axes[1, 0], "herg", "hERG calibration", "C"),
        (axes[1, 1], "bbb_martins", "B3DB BBB calibration", "D"),
    ):
        subset = calibration[
            (calibration.task == task)
            & (calibration.base == "catboost")
        ]
        axis.plot([0, 1], [0, 1], linestyle="--", color="#666666", linewidth=0.8)
        for method, label in (
            ("qrc_gated", "Gated QRC"),
            ("orthogonal_gated", "Gated orthogonal"),
        ):
            curve = subset[subset.method == method].sort_values("mean_prediction")
            axis.plot(
                curve.mean_prediction,
                curve.observed_rate,
                marker="o",
                markersize=3.5,
                linewidth=1.2,
                color=PALETTE[method],
                label=label,
            )
        axis.set_xlim(0, 1)
        axis.set_ylim(0, 1)
        axis.set_xlabel("Mean predicted probability", fontsize=8)
        axis.set_ylabel("Observed positive rate", fontsize=8)
        axis.set_title(title, fontsize=9)
        axis.legend(frameon=False, fontsize=6.5, loc="best")
        _panel_label(axis, panel)
        _style_axis(axis)
    figure.suptitle(
        "External validation decomposition and calibration",
        fontsize=11,
    )
    png = FIGURE_ROOT / "figure3_external_diagnostics.png"
    pdf = FIGURE_ROOT / "figure3_external_diagnostics.pdf"
    figure.savefig(png, dpi=600, bbox_inches="tight")
    figure.savefig(pdf, bbox_inches="tight")
    plt.close(figure)
    return png


def build_external_regression_figure() -> Path | None:
    path = RESULTS_ROOT / "external_regression" / "comparisons.csv"
    if not path.exists():
        return None
    comparisons = pd.read_csv(path, encoding="utf-8-sig")
    selected = comparisons[
        (
            (comparisons["method"] == "qrc")
            & (comparisons.reference == "real_orthogonal")
        )
        | (
            (comparisons["method"] == "qrc")
            & (comparisons.reference == "base")
        )
    ].copy()
    selected["label"] = (
        selected.base.map(
            {"extra_trees": "ExtraTrees", "catboost": "CatBoost"}
        )
        + " / "
        + selected.reference.map(
            {"real_orthogonal": "vs orthogonal", "base": "vs base"}
        )
        + " / "
        + selected.metric
    )
    selected = selected.sort_values("effect_better_positive")
    figure, axis = plt.subplots(figsize=(6.8, 3.3), constrained_layout=True)
    y = np.arange(len(selected))
    axis.errorbar(
        selected.effect_better_positive,
        y,
        xerr=np.vstack(
            [
                selected.effect_better_positive - selected.ci_low,
                selected.ci_high - selected.effect_better_positive,
            ]
        ),
        fmt="o",
        markersize=4,
        color="#D55E00",
        ecolor="#555555",
        elinewidth=0.8,
        capsize=2,
    )
    axis.axvline(0, color="black", linewidth=0.7)
    axis.set_yticks(y)
    axis.set_yticklabels(selected.label, fontsize=7)
    axis.set_xlabel("Direction-normalized external regression effect", fontsize=8)
    axis.set_title("Independent ToxTree hERG pIC50 regression", fontsize=10)
    _style_axis(axis)
    png = FIGURE_ROOT / "figureS4_external_regression.png"
    pdf = FIGURE_ROOT / "figureS4_external_regression.pdf"
    figure.savefig(png, dpi=600, bbox_inches="tight")
    figure.savefig(pdf, bbox_inches="tight")
    plt.close(figure)
    return png


def main() -> int:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    build_chemical_space_figure()
    build_external_diagnostics_figure()
    build_external_regression_figure()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
