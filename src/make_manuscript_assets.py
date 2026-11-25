from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import RESULTS_ROOT


REPORT_ROOT = RESULTS_ROOT / "report"
ASSET_ROOT = RESULTS_ROOT / "manuscript"


def main() -> int:
    ASSET_ROOT.mkdir(parents=True, exist_ok=True)
    (ASSET_ROOT / "figures").mkdir(exist_ok=True)
    (ASSET_ROOT / "tables").mkdir(exist_ok=True)

    endpoint = pd.read_csv(REPORT_ROOT / "endpoint_summary.csv")
    comparisons = pd.read_csv(REPORT_ROOT / "comparisons.csv")
    gates = pd.read_csv(REPORT_ROOT / "gate_weights.csv")
    metrics = pd.read_csv(REPORT_ROOT / "metrics_by_seed.csv")
    finite_counts = pd.read_csv(RESULTS_ROOT / "finite_shot" / "direction_counts.csv")
    low_data_counts = pd.read_csv(RESULTS_ROOT / "low_data" / "direction_counts.csv")
    noise_counts = pd.read_csv(RESULTS_ROOT / "noise" / "direction_counts.csv")
    tuned_counts = pd.read_csv(RESULTS_ROOT / "tuned_qrc" / "direction_counts.csv")
    external_summary = pd.read_csv(
        RESULTS_ROOT / "external_validation" / "summary.csv"
    )

    result_table = endpoint[
        [
            "base",
            "task",
            "metric",
            "classical_base",
            "qrc_ungated",
            "real_orthogonal_ungated",
            "random_fourier_ungated",
            "qrc_gated",
            "real_orthogonal_gated",
        ]
    ].copy()
    gate_summary = (
        gates.groupby(["base", "task", "metric"], as_index=False)
        .agg(
            qrc_gate_mean=("weight", lambda x: x[gates.loc[x.index, "family"] == "qrc"].mean()),
            qrc_gate_zero_fraction=(
                "weight",
                lambda x: (x[gates.loc[x.index, "family"] == "qrc"] == 0).mean(),
            ),
        )
    )
    result_table = result_table.merge(
        gate_summary, on=["base", "task", "metric"], how="left"
    )
    result_table.to_csv(
        ASSET_ROOT / "tables" / "endpoint_results.csv",
        index=False,
        encoding="utf-8-sig",
    )

    effect_table = comparisons[
        comparisons.comparison.isin(
            [
                "qrc_vs_matched",
                "gated_qrc_vs_matched",
                "qrc_vs_fourier",
                "qrc_vs_base",
                "gated_qrc_vs_base",
                "augmented_qrc_vs_matched",
                "augmented_qrc_vs_base",
            ]
        )
    ].copy()
    effect_table.to_csv(
        ASSET_ROOT / "tables" / "effects.csv",
        index=False,
        encoding="utf-8-sig",
    )

    count_rows = []
    for (base, comparison), frame in comparisons.groupby(["base", "comparison"]):
        count_rows.append(
            {
                "base": base,
                "comparison": comparison,
                "positive": int((frame.effect_better_positive > 0).sum()),
                "negative": int((frame.effect_better_positive < 0).sum()),
                "zero": int((frame.effect_better_positive == 0).sum()),
                "holm_significant_positive": int(
                    (
                        (frame.holm_p < 0.05)
                        & (frame.effect_better_positive > 0)
                    ).sum()
                ),
                "holm_significant_negative": int(
                    (
                        (frame.holm_p < 0.05)
                        & (frame.effect_better_positive < 0)
                    ).sum()
                ),
                "holm_equivalent": int((frame.holm_equivalence_p < 0.05).sum()),
            }
        )
    counts = pd.DataFrame(count_rows)
    counts.to_csv(
        ASSET_ROOT / "tables" / "direction_counts.csv",
        index=False,
        encoding="utf-8-sig",
    )

    significantly_negative = comparisons[
        (comparisons.comparison == "qrc_vs_matched")
        & (comparisons.holm_p < 0.05)
        & (comparisons.effect_better_positive < 0)
    ][["base", "task", "metric", "effect_better_positive", "holm_p"]]
    significantly_positive = comparisons[
        (comparisons.comparison == "qrc_vs_matched")
        & (comparisons.holm_p < 0.05)
        & (comparisons.effect_better_positive > 0)
    ][["base", "task", "metric", "effect_better_positive", "holm_p"]]
    base_pivot = endpoint.pivot(
        index=["task", "metric"], columns="base", values="classical_base"
    ).reset_index()
    base_pivot["catboost_better"] = np.where(
        base_pivot.metric == "MAE",
        base_pivot.catboost < base_pivot.extra_trees,
        base_pivot.catboost > base_pivot.extra_trees,
    )
    summary = {
        "catboost_better_endpoints": int(base_pivot.catboost_better.sum()),
        "map_seeds_per_family": 5,
        "split_seeds": 5,
        "qrc_vs_matched_counts": counts[
            counts.comparison == "qrc_vs_matched"
        ].to_dict(orient="records"),
        "gated_qrc_vs_matched_counts": counts[
            counts.comparison == "gated_qrc_vs_matched"
        ].to_dict(orient="records"),
        "augmented_qrc_vs_matched_counts": counts[
            counts.comparison == "augmented_qrc_vs_matched"
        ].to_dict(orient="records"),
        "augmented_qrc_vs_base_counts": counts[
            counts.comparison == "augmented_qrc_vs_base"
        ].to_dict(orient="records"),
        "finite_shot_counts": finite_counts.to_dict(orient="records"),
        "low_data_counts": low_data_counts.to_dict(orient="records"),
        "noise_counts": noise_counts.to_dict(orient="records"),
        "tuned_qrc_counts": tuned_counts.to_dict(orient="records"),
        "external_validation": external_summary.to_dict(orient="records"),
        "significant_positive": significantly_positive.to_dict(orient="records"),
        "significant_negative": significantly_negative.to_dict(orient="records"),
        "qrc_gate_zero_counts": {
            base: int(
                ((gates.base == base) & (gates.family == "qrc") & (gates.weight == 0)).sum()
            )
            for base in sorted(gates.base.unique())
        },
        "qrc_gate_zero_denominators": {
            base: int(((gates.base == base) & (gates.family == "qrc")).sum())
            for base in sorted(gates.base.unique())
        },
    }
    (ASSET_ROOT / "manuscript_numbers.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    endpoint_effect = comparisons[comparisons.comparison == "qrc_vs_matched"].copy()
    reference_scores = (
        metrics[metrics.method == "real_orthogonal_ungated"]
        .groupby(["base", "task", "metric"])["score"]
        .mean()
        .rename("reference_score")
        .reset_index()
    )
    endpoint_effect = endpoint_effect.merge(
        reference_scores, on=["base", "task", "metric"], how="left"
    )
    endpoint_effect["display_effect"] = np.where(
        endpoint_effect.metric == "MAE",
        100.0
        * endpoint_effect.effect_better_positive
        / endpoint_effect.reference_score,
        endpoint_effect.effect_better_positive,
    )
    endpoint_effect["display_low"] = np.where(
        endpoint_effect.metric == "MAE",
        100.0 * endpoint_effect.ci_low / endpoint_effect.reference_score,
        endpoint_effect.ci_low,
    )
    endpoint_effect["display_high"] = np.where(
        endpoint_effect.metric == "MAE",
        100.0 * endpoint_effect.ci_high / endpoint_effect.reference_score,
        endpoint_effect.ci_high,
    )

    rows = [
        ("classification", "AUROC / AUPRC absolute difference"),
        ("MAE", "MAE improvement (%)"),
        ("Spearman", "Spearman difference"),
    ]
    bases = ["extra_trees", "catboost"]
    display_titles = {
        "extra_trees": "ExtraTrees base",
        "catboost": "MapLight-CatBoost base",
    }
    fig, axes = plt.subplots(
        len(rows),
        len(bases),
        figsize=(11.2, 12.0),
        gridspec_kw={"width_ratios": [1, 1]},
        constrained_layout=True,
    )
    for row_index, (metric_name, x_label) in enumerate(rows):
        for column_index, base in enumerate(bases):
            axis = axes[row_index, column_index]
            if metric_name == "classification":
                subset = endpoint_effect[
                    (endpoint_effect.base == base)
                    & endpoint_effect.metric.isin(["AUROC", "AUPRC"])
                ]
            else:
                subset = endpoint_effect[
                    (endpoint_effect.base == base) & (endpoint_effect.metric == metric_name)
                ]
            subset = subset.sort_values("display_effect")
            positions = np.arange(len(subset))
            significant = subset.holm_p < 0.05
            axis.errorbar(
                subset.display_effect,
                positions,
                xerr=np.vstack(
                    [
                        subset.display_effect - subset.display_low,
                        subset.display_high - subset.display_effect,
                    ]
                ),
                fmt="none",
                ecolor="#4b5563",
                elinewidth=0.8,
                capsize=0,
            )
            axis.scatter(
                subset.display_effect,
                positions,
                s=22,
                c=np.where(significant, "#b91c1c", "#1d4ed8"),
                zorder=3,
            )
            axis.axvline(0, color="black", linewidth=0.8, alpha=0.7)
            axis.set_yticks(positions)
            axis.set_yticklabels(
                [f"{task} ({metric})" for task, metric in zip(subset.task, subset.metric)],
                fontsize=7,
            )
            axis.set_xlabel(x_label, fontsize=8)
            axis.set_title(display_titles[base], fontsize=10)
            axis.grid(axis="x", alpha=0.2)
            axis.tick_params(axis="x", labelsize=8)
    fig.suptitle(
        "Ungated QRC minus matched real-orthogonal quadratic features",
        fontsize=13,
    )
    fig.savefig(ASSET_ROOT / "figures" / "forest_main.png", dpi=300)
    fig.savefig(ASSET_ROOT / "figures" / "forest_main.pdf")
    plt.close(fig)

    gate_counts = (
        gates.assign(selected=gates.weight > 0)
        .groupby(["base", "family", "selected"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=[False, True], fill_value=0)
    )
    labels = [f"{base}\n{family.replace('_', ' ')}" for base, family in gate_counts.index]
    selected = gate_counts[True].to_numpy()
    suppressed = gate_counts[False].to_numpy()
    x = np.arange(len(labels))
    gate_fig, gate_axis = plt.subplots(figsize=(8.2, 3.8), constrained_layout=True)
    gate_axis.bar(x, suppressed, color="#9ca3af", label="Weight 0")
    gate_axis.bar(x, selected, bottom=suppressed, color="#2563eb", label="Weight > 0")
    gate_axis.set_xticks(x)
    gate_axis.set_xticklabels(labels, fontsize=7, rotation=25, ha="right")
    gate_axis.set_ylabel("Endpoint-split selections")
    gate_axis.set_title("Validation gate selections by branch family")
    gate_axis.legend(frameon=False)
    gate_axis.grid(axis="y", alpha=0.2)
    gate_fig.savefig(ASSET_ROOT / "figures" / "gate_selections.png", dpi=300)
    gate_fig.savefig(ASSET_ROOT / "figures" / "gate_selections.pdf")
    plt.close(gate_fig)

    low_fig, low_axes = plt.subplots(
        1, 2, figsize=(9.2, 3.8), sharey=True, constrained_layout=True
    )
    fraction_labels = ["5%", "10%", "20%", "40%", "100%"]
    for axis, base in zip(low_axes, ["extra_trees", "catboost"]):
        subset = low_data_counts[low_data_counts.base == base].sort_values(
            "target_fraction"
        )
        axis.plot(
            fraction_labels,
            subset.qrc_better_ungated,
            marker="o",
            label="Ungated QRC",
            color="#1d4ed8",
        )
        axis.plot(
            fraction_labels,
            subset.qrc_better_gated,
            marker="s",
            label="Validation-gated QRC",
            color="#b45309",
        )
        axis.axhline(
            subset.endpoints.iloc[0] / 2,
            color="#6b7280",
            linestyle="--",
            linewidth=0.8,
            label="Half of endpoints",
        )
        axis.set_ylim(0, subset.endpoints.max())
        axis.set_title(
            "ExtraTrees" if base == "extra_trees" else "MapLight-CatBoost",
            fontsize=10,
        )
        axis.set_xlabel("Target training fraction", fontsize=8)
        axis.grid(alpha=0.2)
    low_axes[0].set_ylabel("Endpoints better than orthogonal (of 8)", fontsize=8)
    low_axes[0].legend(frameon=False, fontsize=7)
    low_fig.suptitle("Low-data direction counts against matched orthogonal maps", fontsize=11)
    low_fig.savefig(ASSET_ROOT / "figures" / "low_data_counts.png", dpi=300)
    low_fig.savefig(ASSET_ROOT / "figures" / "low_data_counts.pdf")
    plt.close(low_fig)

    external_plot = external_summary[
        (external_summary.method == "qrc_gated")
        & (external_summary.reference == "orth_gated")
    ].copy()
    external_plot["label"] = (
        external_plot.base.map(
            {"extra_trees": "ExtraTrees", "catboost": "MapLight-CatBoost"}
        )
        + " / "
        + external_plot.task.map({"herg": "hERG", "bbb_martins": "B3DB BBB"})
    )
    external_plot = external_plot.sort_values("effect")
    ext_fig, ext_axis = plt.subplots(figsize=(7.2, 3.2), constrained_layout=True)
    positions = np.arange(len(external_plot))
    ext_axis.errorbar(
        external_plot.effect,
        positions,
        xerr=np.vstack(
            [
                external_plot.effect - external_plot.ci_low,
                external_plot.ci_high - external_plot.effect,
            ]
        ),
        fmt="o",
        color="#1d4ed8",
        ecolor="#4b5563",
        capsize=2,
    )
    ext_axis.axvline(0, color="black", linewidth=0.8)
    ext_axis.set_yticks(positions)
    ext_axis.set_yticklabels(external_plot.label, fontsize=8)
    ext_axis.set_xlabel("Gated QRC minus gated orthogonal AUROC", fontsize=8)
    ext_axis.set_title("Independent external endpoint effects", fontsize=10)
    ext_axis.grid(axis="x", alpha=0.2)
    ext_fig.savefig(ASSET_ROOT / "figures" / "external_validation_effects.png", dpi=300)
    ext_fig.savefig(ASSET_ROOT / "figures" / "external_validation_effects.pdf")
    plt.close(ext_fig)

    noise_fig, noise_axes = plt.subplots(
        1, 2, figsize=(9.0, 3.6), sharey=True, constrained_layout=True
    )
    noise_labels = ["0.001", "0.005", "0.010"]
    for axis, base in zip(noise_axes, ["extra_trees", "catboost"]):
        subset = noise_counts[noise_counts.base == base].sort_values(
            "depolarizing_probability"
        )
        axis.plot(
            noise_labels,
            subset.qrc_better_than_orth,
            marker="o",
            label="Better than orthogonal",
            color="#1d4ed8",
        )
        axis.plot(
            noise_labels,
            subset.qrc_worse_than_orth,
            marker="s",
            label="Worse than orthogonal",
            color="#b45309",
        )
        axis.set_ylim(0, subset.endpoints.max())
        axis.set_title(
            "ExtraTrees" if base == "extra_trees" else "MapLight-CatBoost",
            fontsize=10,
        )
        axis.set_xlabel("Depolarizing probability p", fontsize=8)
        axis.grid(alpha=0.2)
    noise_axes[0].set_ylabel("Endpoints (of 8)", fontsize=8)
    noise_axes[0].legend(frameon=False, fontsize=7)
    noise_fig.suptitle("Noise sensitivity at 4,096 shots", fontsize=11)
    noise_fig.savefig(ASSET_ROOT / "figures" / "noise_counts.png", dpi=300)
    noise_fig.savefig(ASSET_ROOT / "figures" / "noise_counts.pdf")
    plt.close(noise_fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

