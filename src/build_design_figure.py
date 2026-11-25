from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from src.config import RESULTS_ROOT


FIGURE_ROOT = RESULTS_ROOT / "manuscript" / "figures"


def build_design_figure() -> Path:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(7.2, 4.7), constrained_layout=True)
    axis.set_xlim(0, 100)
    axis.set_ylim(0, 72)
    axis.axis("off")

    def box(
        x: float,
        y: float,
        width: float,
        height: float,
        title: str,
        detail: str,
        color: str,
    ) -> tuple[float, float]:
        patch = FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.35,rounding_size=1.2",
            facecolor=color,
            edgecolor="#555555",
            linewidth=0.7,
        )
        axis.add_patch(patch)
        axis.text(
            x + width / 2,
            y + height * 0.62,
            title,
            ha="center",
            va="center",
            fontsize=8.2,
            fontweight="bold",
        )
        axis.text(
            x + width / 2,
            y + height * 0.27,
            detail,
            ha="center",
            va="center",
            fontsize=7.0,
            linespacing=1.15,
        )
        return x + width / 2, y + height / 2

    def arrow(
        start: tuple[float, float],
        end: tuple[float, float],
        label: str | None = None,
    ) -> None:
        patch = FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=9,
            linewidth=0.9,
            color="#444444",
            shrinkA=4,
            shrinkB=4,
        )
        axis.add_patch(patch)
        if label:
            axis.text(
                (start[0] + end[0]) / 2,
                (start[1] + end[1]) / 2 + 1.2,
                label,
                fontsize=6.2,
                ha="center",
                va="bottom",
                color="#333333",
            )

    tdc_right = box(
        2,
        56,
        22,
        11,
        "TDC ADMET",
        "22 endpoints\n65,430 train/valid | 16,379 test",
        "#D9E2F3",
    )
    ext_right = box(
        2,
        39,
        22,
        11,
        "External cohorts",
        "ToxTree hERG | B3DB BBB",
        "#D9E2F3",
    )
    et_right = box(
        28,
        56,
        19,
        11,
        "Morgan-ExtraTrees",
        "512-bit ECFP4",
        "#E2F0D9",
    )
    cb_right = box(
        28,
        39,
        19,
        11,
        "MapLight-CatBoost",
        "2,563 descriptors",
        "#E2F0D9",
    )
    pca_right = box(
        51,
        45,
        20,
        16,
        "Training-only PCA",
        "32 dimensions\nL2-normalized amplitude",
        "#FFF2CC",
    )
    qrc_right = box(
        75,
        57,
        22,
        10,
        "Fixed QRC",
        "5 qubits | 15 Pauli readouts",
        "#FBE5D6",
    )
    orth_right = box(
        75,
        43,
        22,
        10,
        "Real orthogonal",
        "matched 15-form quadratic control",
        "#DEEBF7",
    )
    rff_right = box(
        75,
        29,
        22,
        10,
        "Random Fourier",
        "15 cosine features",
        "#E4DFEC",
    )
    head_left = box(
        75,
        8,
        22,
        12,
        "Residual head",
        "five maps averaged\nsame regularization",
        "#FFF2CC",
    )
    gate_left = box(
        45,
        8,
        22,
        12,
        "Validation gate",
        "weights 0 to 1\ntest labels unused",
        "#FFF2CC",
    )
    evidence_left = box(
        2,
        8,
        34,
        12,
        "Scaffold-level evidence",
        "paired inference | Holm | TOST\nchemical space | source validation",
        "#E2F0D9",
    )

    arrow(tdc_right, (28, 61.5))
    arrow(tdc_right, (28, 44.5))
    arrow(ext_right, (28, 58.5), "external")
    arrow(ext_right, (28, 41.5), "external")
    arrow(et_right, (51, 55))
    arrow(cb_right, (51, 51))
    arrow(pca_right, (75, 62))
    arrow(pca_right, (75, 51.5))
    arrow(pca_right, (75, 36.5))
    arrow(qrc_right, (86, 20))
    arrow(orth_right, (86, 20))
    arrow(rff_right, (86, 20))
    arrow(head_left, (67, 14))
    arrow(gate_left, (36, 14))

    axis.text(
        50,
        68.5,
        "Matched evaluation design",
        fontsize=11,
        fontweight="bold",
        ha="center",
        va="center",
    )
    axis.text(
        59,
        25.2,
        "Equal input | equal readout dimension | equal five-map budget",
        fontsize=7,
        ha="center",
        va="center",
    )
    theory_band = FancyBboxPatch(
        (2, 0.6),
        95,
        5.2,
        boxstyle="round,pad=0.15,rounding_size=0.8",
        facecolor="#F4F4F4",
        edgecolor="#B8B8B8",
        linewidth=0.6,
    )
    axis.add_patch(theory_band)
    axis.text(
        5,
        3.2,
        r"$q_j(\mathbf{a})=\mathbf{a}^{\mathsf{T}}A_j\mathbf{a}$",
        fontsize=8.2,
        ha="left",
        va="center",
    )
    axis.text(
        24,
        3.2,
        "All 15 Pauli readouts form constrained real quadratic features",
        fontsize=7.0,
        ha="left",
        va="center",
    )
    axis.text(
        5,
        1.45,
        "The equal-dimensional orthogonal branch samples a matched quadratic control",
        fontsize=6.8,
        ha="left",
        va="center",
        color="#333333",
    )

    png = FIGURE_ROOT / "figure1_design.png"
    pdf = FIGURE_ROOT / "figure1_design.pdf"
    figure.savefig(png, dpi=600, bbox_inches="tight")
    figure.savefig(pdf, bbox_inches="tight")
    plt.close(figure)
    return png


if __name__ == "__main__":
    print(build_design_figure())
