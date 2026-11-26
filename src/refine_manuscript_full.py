from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
from docx.text.paragraph import Paragraph

from src.config import PROJECT_ROOT


OUTPUT_ROOT = PROJECT_ROOT / "outputs"
SOURCE = OUTPUT_ROOT / "Matched_Evaluation_Fixed_Quantum_Reservoir_TDC_ADMET.docx"
REVISED = (
    OUTPUT_ROOT
    / "Matched_Evaluation_Fixed_Quantum_Reservoir_TDC_ADMET_REVISED.docx"
)
REPORT_MD = OUTPUT_ROOT / "Manuscript_Revision_Before_After.md"
REPORT_JSON = OUTPUT_ROOT / "Manuscript_Revision_Changes.json"


@dataclass(frozen=True)
class TextEdit:
    location: str
    before_start: str
    after: str
    reason: str


def _find_unique(document: Document, prefix: str) -> Paragraph:
    matches = [
        paragraph
        for paragraph in document.paragraphs
        if paragraph.text.strip().startswith(prefix)
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one paragraph starting with {prefix!r}, found {len(matches)}"
        )
    return matches[0]


def _replace(paragraph: Paragraph, text: str) -> None:
    if paragraph.runs:
        paragraph.runs[0].text = text
        for run in paragraph.runs[1:]:
            run._r.getparent().remove(run._r)
    else:
        run = paragraph.add_run(text)
        run.font.name = "Arial"
        run.font.size = Pt(10.5)
    if not paragraph.style.name.startswith("Heading"):
        paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY


def _insert_after(
    source: Paragraph,
    text: str,
    style: str = "Normal",
) -> Paragraph:
    element = OxmlElement("w:p")
    source._p.addnext(element)
    paragraph = Paragraph(element, source._parent)
    paragraph.style = style
    if source._p.pPr is not None:
        element.insert(0, copy.deepcopy(source._p.pPr))
    paragraph.alignment = (
        WD_ALIGN_PARAGRAPH.JUSTIFY
        if style == "Normal"
        else WD_ALIGN_PARAGRAPH.LEFT
    )
    run = paragraph.add_run(text)
    run.font.name = "Arial"
    run.font.size = Pt(10.5 if style == "Normal" else 12.5)
    if style.startswith("Heading"):
        run.bold = True
    run._element.get_or_add_rPr().rFonts.set(
        qn("w:eastAsia"),
        "Times New Roman",
    )
    return paragraph


def _insert_before(
    marker: Paragraph,
    text: str,
    style: str = "Normal",
) -> Paragraph:
    paragraph = marker.insert_paragraph_before(text, style=style)
    paragraph.alignment = (
        WD_ALIGN_PARAGRAPH.JUSTIFY
        if style == "Normal"
        else WD_ALIGN_PARAGRAPH.LEFT
    )
    for run in paragraph.runs:
        run.font.name = "Arial"
        run.font.size = Pt(10.5 if style == "Normal" else 12.5)
        if style.startswith("Heading"):
            run.bold = True
        run._element.get_or_add_rPr().rFonts.set(
            qn("w:eastAsia"),
            "Times New Roman",
        )
    return paragraph


def _apply_edit(
    document: Document,
    edit: TextEdit,
    changes: list[dict[str, str]],
) -> Paragraph:
    paragraph = _find_unique(document, edit.before_start)
    before = paragraph.text
    _replace(paragraph, edit.after)
    changes.append(
        {
            "location": edit.location,
            "before": before,
            "after": edit.after,
            "reason": edit.reason,
        }
    )
    return paragraph


def refine() -> dict[str, object]:
    document = Document(SOURCE)
    changes: list[dict[str, str]] = []
    inserted: list[dict[str, str]] = []

    edits = [
        TextEdit(
            "Abstract, paragraph 1",
            "Reported QRC gains are difficult to interpret",
            (
                "Reported QRC gains are difficult to compare because studies "
                "often differ in classical controls, random realizations, "
                "base-model strength, and external validation. We therefore "
                "evaluated this question under a common, calibrated protocol "
                "across all 22 Therapeutics Data Commons (TDC) ADMET "
                "endpoints. We compared exact simulations of five-qubit "
                "amplitude-encoded reservoirs with real-orthogonal quadratic "
                "maps and random Fourier features, using Morgan-ExtraTrees "
                "and MapLight-CatBoost. Five scaffold splits and five averaged "
                "maps per family quantified randomness. Ungated QRC was better "
                "on 6 and worse on 16 ExtraTrees endpoints, and better on 3 "
                "and worse on 19 CatBoost endpoints. After Holm correction, "
                "no endpoint was significantly better and three were "
                "significantly worse. Validation gating, joint QRC-orthogonal "
                "residuals, low-data "
                "scaling, finite shots, simulated noise, and a bounded "
                "reservoir-family search did not produce a cross-base "
                "advantage. External validation was source-dependent: "
                "CatBoost improved by 0.040 AUROC on 293 non-overlapping hERG "
                "molecules, whereas both bases degraded on 2,317 B3DB BBB "
                "molecules. The hERG difference combined a QRC gain with an "
                "orthogonal-branch decrement relative to the base. "
                "Continuous-label ranking and an independent pIC50 regression "
                "did not survive joint multiplicity correction. Known-signal "
                "calibration recovered QRC and classical targets, with null "
                "false-positive rates of 2.0-4.7%. Circuit-level simulation "
                "preserved rank under error but attenuated amplitudes. "
                "Chemical-space analyses showed no simple source effect. The "
                "main contribution is a calibrated evaluation workflow; its "
                "scope is limited to five-qubit amplitude encoding, 15 Pauli "
                "readouts, a linear residual head, and exact state-vector "
                "simulation, not to other encodings, trainable circuits, "
                "larger reservoirs, or physical hardware."
            ),
            (
                "Sharpened the comparison problem, removed compressed "
                "nominal phrases, and grouped each result with its evidential "
                "role while retaining all values."
            ),
        ),
        TextEdit(
            "1 Introduction, paragraph 1",
            "ADMET prediction includes binary",
            (
                "ADMET prediction includes binary, continuous, and ranking "
                "endpoints that differ in sample size, measurement "
                "resolution, and chemical-space coverage. TDC supplies fixed "
                "test sets, endpoint-specific metrics, and scaffold split "
                "interfaces, allowing endpoint-level verification [1,2]. "
                "Molecular representation, model family, and evaluation split "
                "can each change model rankings [3-6]. A comparison with one "
                "weak base model cannot separate the contribution of quantum "
                "features from nonlinear capacity, training choices, or "
                "dataset-specific effects."
            ),
            (
                "Replaced the abstract rationale with three observable "
                "confounders and a direct implication for comparison design."
            ),
        ),
        TextEdit(
            "1 Introduction, paragraph 2",
            "We ask a bounded question.",
            (
                "The study addresses one question: with molecular input, 15 "
                "readouts, and the linear residual head held constant, does a "
                "fixed five-qubit reservoir add predictive value beyond "
                "real-orthogonal quadratic maps and random Fourier features "
                "across 22 TDC endpoints, two classical bases, and independent "
                "external sources? Figure 1 summarizes the design. The study "
                "makes three contributions. First, it treats the current QRC "
                "residual as a constrained real quadratic feature family and "
                "constructs a control with the same input, readout dimension, "
                "fitted-parameter budget, and map budget. Second, it evaluates "
                "the family across all 22 endpoints with validation gating and "
                "multiple-testing correction. Third, it uses low-data, "
                "finite-shot, simulated-noise, bounded-family, two-source "
                "external, continuous-label, independent pIC50 regression, and "
                "chemical-space analyses to define the limits of the conclusion."
            ),
            (
                "Converted a broad statement of scope into one research "
                "question and three explicit, non-overlapping contributions."
            ),
        ),
        TextEdit(
            "2.2 Quantum Molecular Features and Structural Controls, paragraph 1",
            "Beaulieu et al. studied",
            (
                "Beaulieu et al. reported more stable fixed-reservoir "
                "performance in smaller molecular-activity datasets and "
                "analyzed embedding separation [8]. Benson et al. concatenated "
                "Hamiltonian-derived readouts with classical descriptors before "
                "CatBoost and reported improvement on 8/10 TDC tasks; this "
                "hybrid feature design does not isolate a capacity-matched "
                "residual [9]. Mansour et al. found that compact "
                "quantum-inspired Hamiltonian features performed comparably to "
                "a second-degree polynomial interaction control on AqSolDB, "
                "making an explicit quadratic comparator central to the present "
                "design [10]. QCS-ADME addressed quantum-circuit search and "
                "simulator-to-hardware variation rather than one fixed circuit "
                "family [11]. Jia et al. compared five-qubit amplitude-encoded "
                "residuals with real-orthogonal controls, but jointly trained "
                "the encoder and residual head and evaluated receptor-potency "
                "tasks rather than ADMET [12]. A 48-task potency benchmark "
                "found no global advantage for quantum classifiers [27], and "
                "Floquet-QRC tested sequential graph events and driven "
                "reservoirs under a different input regime [28]. These studies "
                "differ in task, control, and training protocol; Table 1 "
                "accordingly compares design choices rather than model scores."
            ),
            (
                "State the reported scope of each source, distinguish "
                "positive, negative, and mechanistic findings, and explain why "
                "the table is not a numerical ranking."
            ),
        ),
        TextEdit(
            "2.2 Quantum Molecular Features and Structural Controls, paragraph 2",
            "Our primary control follows directly",
            (
                "The comparison asks whether reservoir geometry contributes "
                "information beyond the nonlinear interactions available to a "
                "classical map. For fixed real amplitudes, every Z or ZZ "
                "expectation is a real quadratic form. A real-orthogonal "
                "transformation produces another set of quadratic readouts "
                "with the same input, readout count, and fitted parameters. "
                "Differences between these branches therefore reflect matrix "
                "geometry rather than feature dimensionality. Random Fourier "
                "features provide a second 15-dimensional nonlinear control. "
                "All three families use five independent maps, and no family "
                "receives extra validation candidates."
            ),
            (
                "Removed the duplicated derivation emphasis and made the "
                "purpose of each comparator explicit."
            ),
        ),
        TextEdit(
            "2.3 Validation Gating and Endpoint-Level Reporting",
            "Out-of-fold offsets",
            (
                "Out-of-fold offsets, validation-estimated stacking weights, "
                "and endpoint-level reporting provide established precedents "
                "[14-16]. Ark-ADMET selected representation and fusion weights "
                "with internal validation across 22 TDC endpoints [16]. "
                "Robinson et al. reanalyzed a large bioactivity comparison in "
                "the Journal of Computer-Aided Molecular Design and showed that "
                "evaluation design can change the conclusions [31]. We apply "
                "the same five-map averaging and scalar gating rule to QRC and "
                "both classical families. Test labels are not used for map "
                "generation, residual fitting, or weight selection. Because "
                "repeated fits share a fixed outer test set, bootstrap and "
                "permutation inference is performed with the test scaffold as "
                "the sampling unit [17-20]."
            ),
            (
                "Aligned the citation range with the statistical method and "
                "made the data-selection safeguards follow in logical order."
            ),
        ),
        TextEdit(
            "3 Data and Official Evaluation",
            "3 Data and Official Evaluation",
            "3 Data, Splits, and Statistical Evaluation",
            "The section heading now covers the split and inference content.",
        ),
        TextEdit(
            "3 Data, Splits, and Statistical Evaluation, paragraph 2",
            "For each endpoint, the official train_val",
            (
                "For each endpoint, the official train_val table was split "
                "into 87.5% training and 12.5% validation with the PyTDC "
                "scaffold procedure and seeds 1-5. Official test membership, "
                "labels, and row order remained fixed. Every SMILES string "
                "parsed successfully; canonical non-isomeric identities and "
                "Bemis-Murcko scaffolds were disjoint across training, "
                "validation, and test [22]. Three scaffold folds inside each "
                "outer training set produced the out-of-fold base offsets. Test "
                "results were generated only after the configuration was frozen."
            ),
            (
                "Corrected an awkward validation sentence and preserved the "
                "same split and leakage checks."
            ),
        ),
        TextEdit(
            "3 Data, Splits, and Statistical Evaluation, paragraph 3",
            "The primary effect was computed",
            (
                "The primary effect was computed from unrounded predictions: "
                "each seed was scored, and the scores were averaged over the "
                "five seeds. For AUROC, AUPRC, and Spearman, the effect is the "
                "new method minus the reference; for MAE, it is the reference "
                "minus the new method. Positive values indicate improvement. "
                "We used 1,000 paired scaffold bootstrap resamples for 95% "
                "intervals and 1,999 paired scaffold permutations for the "
                "primary tests, with Holm correction across the 22 endpoints "
                "[18-20]."
            ),
            (
                "Split the dense statistics paragraph at the change from "
                "estimation to equivalence interpretation, keeping all tests "
                "and values."
            ),
        ),
        TextEdit(
            "4.2 Five-Qubit Reservoir and Matched Classical Features, paragraph 2",
            "Five qubits support 32 real amplitudes",
            (
                "A five-qubit register provides 32 amplitudes, so a "
                "32-dimensional PCA vector can be encoded without truncation "
                "or zero padding. The 15 readouts are five Z and ten ZZ "
                "expectations. The scale is a controlled identifiability "
                "choice, not a hardware-capacity claim: it permits exact "
                "state-vector evaluation, an equal-dimensional classical "
                "control, and five complete map realizations. For a normalized "
                "PCA vector v, the amplitudes are a_j = v_j / ||v||. The "
                "Hamiltonian H and evolution U = exp(-iHt) were fixed and were "
                "not trained on test labels. PCA dimension and readout set were "
                "held fixed so that the primary benchmark did not add another "
                "capacity search."
            ),
            (
                "Replaced 'smallest complete' with a precise reason for the "
                "32-dimensional design and clarified which quantities were fixed."
            ),
        ),
        TextEdit(
            "4.2 Five-Qubit Reservoir and Matched Classical Features, Proposition 1",
            "Proposition 1.",
            (
                "Proposition 1. For any fixed set of 15 diagonal Pauli "
                "observables D_j and any fixed unitary U, the readouts of a "
                "normalized 32-dimensional real input a satisfy "
                "q_j(a)=a^T A_j a, where A_j=Re(U^dagger D_j U). An intercept "
                "can be absorbed into b, so any linear readout of these "
                "features has the form a^T M a+b. Thus fixed five-qubit QRC "
                "with a linear residual head belongs to a model family "
                "constrained by at most 15 real quadratic forms. The proof "
                "follows by expanding (Ua)^dagger D_j(Ua). This class "
                "description does not equate QRC with a particular "
                "real-orthogonal map; it identifies the function family and "
                "motivates the matched control."
            ),
            (
                "Removed the contradiction between 'intercept-free' and the "
                "intercept-containing expression, and stated the role of the "
                "proposition directly."
            ),
        ),
        TextEdit(
            "4.4 Benchmark Calibration and Attribution, paragraph 1",
            "To test whether the evaluation",
            (
                "To test sensitivity and specificity separately from ADMET "
                "performance, we performed a feature-stage calibration on "
                "hERG, B3DB BBB, and AqSolDB solubility. Real molecular inputs "
                "were projected to 32 dimensions and passed through the same "
                "five QRC, orthogonal, and Fourier map draws. We generated "
                "QRC-derived, orthogonal-derived, and independent null targets; "
                "trained the same 15-dimensional heads on the fixed training "
                "splits; averaged the five map predictions; and evaluated "
                "held-out recovery. For each base and scenario, this produced "
                "150 synthetic datasets (3 endpoints x 5 split seeds x 10 "
                "replicates). The calibration isolates the feature comparison "
                "and intentionally omits the classical base offset."
            ),
            (
                "Made the calibration's purpose, exact scope, and 150-dataset "
                "budget explicit without changing the experiment."
            ),
        ),
        TextEdit(
            "4.4 Benchmark Calibration and Attribution, paragraph 2",
            "We also decomposed",
            (
                "We further decomposed each QRC-versus-base endpoint effect "
                "into a matched-classical nonlinearity term and a "
                "QRC-specific term; compared validation-selected QRC and "
                "orthogonal maps to quantify selection optimism; computed "
                "effective rank, condition number, and centered kernel "
                "alignment for all 220 task-base-split combinations; and "
                "stratified external QRC-specific AUROC by nearest-TDC "
                "similarity quartiles. Supplementary Tables S12-S16 and "
                "Figures S6-S10 report these analyses."
            ),
            (
                "Repaired punctuation and parallel construction in the list "
                "of supporting analyses."
            ),
        ),
        TextEdit(
            "5.1 Overall Results, paragraph 1",
            "Table 2 reports five-seed",
            (
                "Table 2 reports five-seed mean official metrics for both bases "
                "and ungated branches. Relative to the fixed real-orthogonal "
                "control, point estimates favored QRC on 6 and the matched "
                "control on 16 ExtraTrees endpoints; on CatBoost, they favored "
                "QRC on 3 and the matched control on 19 endpoints. The "
                "corrected MapLight-CatBoost base outperformed ExtraTrees on "
                "21/22 endpoints; the exception was AUPRC on CYP2C9 substrate. "
                "An earlier exploratory pilot selected BBB, hERG, Caco2, and "
                "LD50 as candidate endpoints. Their directions did not "
                "reproduce consistently: only Caco2 and LD50 were positive "
                "against the base on ExtraTrees and only hERG was marginally "
                "positive on CatBoost; against the matched orthogonal control, "
                "at most 2/4 were positive on either base, and none survived "
                "multiple-testing correction. These four endpoints are "
                "reported as exploratory and are not used for confirmatory "
                "inference."
            ),
            (
                "Named the four endpoints from the exploratory pilot, preserved "
                "their direction counts, and explicitly separated them from "
                "confirmatory inference."
            ),
        ),
        TextEdit(
            "5.5 Independent External Endpoints, paragraph 3",
            "Figure 3 separates",
            (
                "Figure 3 decomposes the hERG and B3DB differences. For "
                "CatBoost/hERG, gated QRC minus the residual-free base was "
                "+0.0285 AUROC (95% CI [0.0137, 0.0437]), whereas gated "
                "orthogonal minus the base was -0.0117 ([-0.0216, -0.0011]); "
                "the +0.0402 primary difference therefore combines a QRC gain "
                "with an orthogonal decrement. The hERG QRC-minus-orthogonal "
                "AUPRC difference was +0.0304, with Brier-score and log-loss "
                "improvements of +0.0038 and +0.0363. Both hERG branches "
                "remained poorly calibrated, with slopes of approximately "
                "0.15-0.26. In B3DB, QRC minus orthogonal AUPRC was -0.0047 "
                "for ExtraTrees and -0.0061 for CatBoost, and Brier-score and "
                "log-loss differences did not favor QRC. Full values are "
                "reported in Supplementary Tables S7 and S8."
            ),
            (
                "Separated the external effect decomposition from the "
                "continuous-label analysis and removed compressed numeric "
                "labels."
            ),
        ),
        TextEdit(
            "5.7 Bounded Reservoir-Family Search, paragraph 2",
            "Across the eight representative endpoints",
            (
                "For the eight representative endpoints, validation selected "
                "QRC and the orthogonal search at four endpoints each on "
                "ExtraTrees. On CatBoost, it selected QRC at two endpoints, the "
                "orthogonal search at five, and recorded one tie. No endpoint "
                "was Holm-significantly positive. The baseline QRC setting "
                "remained the most frequently selected configuration (15/40 on "
                "ExtraTrees and 25/40 on CatBoost), indicating that the broader "
                "family did not reveal a new stable signal. Against the "
                "residual-free base, the direction counts were 4/4 on "
                "ExtraTrees and 2/5/1 on CatBoost; VDss was significantly worse "
                "on both bases. These results weaken under-tuning as an "
                "explanation for the null finding."
            ),
            (
                "Removed the circular phrase 'selected QRC' and separated the "
                "selection, tuning, and residual-free comparisons."
            ),
        ),
        TextEdit(
            "5.8 Independent Continuous pIC50 Regression and Circuit-Level Audit",
            "5.8 Independent Continuous pIC50 Regression and Circuit-Level Audit",
            "5.8 Independent Continuous hERG Regression",
            (
                "The section heading now describes only the regression analysis; "
                "the circuit audit receives its own section."
            ),
        ),
        TextEdit(
            "5.8 Independent Continuous hERG Regression, paragraph 2",
            "Five model seeds did not show",
            (
                "Across five model seeds, no comparison showed a confirmed QRC "
                "increment. QRC minus orthogonal Spearman was +0.0229 on "
                "ExtraTrees (95% CI [-0.0121, 0.0608]) and +0.0093 on CatBoost "
                "([-0.0168, 0.0325]); QRC minus the CatBoost base was +0.0292 "
                "([-0.0034, 0.0604]). MAE differences were close to zero. No "
                "comparison was significant after Holm correction across the "
                "12 metric, base, and contrast tests. The cohort is independent "
                "of TDC labels, but 214 test molecules in 155 scaffolds limit "
                "statistical power. Full results are shown in Supplementary "
                "Figure S4 and Supplementary Table S10."
            ),
            (
                "Separated regression evidence from the unrelated circuit "
                "audit and stated the power limitation next to the estimate."
            ),
        ),
        TextEdit(
            "5.9 Benchmark Calibration and Source Diagnostics",
            "5.9 Benchmark Calibration and Source Diagnostics",
            "5.10 Benchmark Calibration and Source Diagnostics",
            "Renumbered after inserting the circuit-level audit section.",
        ),
        TextEdit(
            "5.10 Benchmark Calibration and Source Diagnostics, paragraph 1",
            "The known-signal calibration recovered",
            (
                "The known-signal calibration separated the three feature "
                "families. For QRC-derived targets, QRC minus orthogonal test "
                "performance was +0.302 on ExtraTrees and +0.190 on CatBoost, "
                "and the expected QRC family ranked first in 150/150 "
                "simulations (100.0%) for both bases. For orthogonal-derived "
                "targets, the same contrast reversed to -0.332 and -0.238, and "
                "the expected orthogonal family ranked first in 149/150 "
                "simulations (99.3%) for ExtraTrees and 149/150 (99.3%) for "
                "CatBoost. For null targets, two-sided paired permutation "
                "tests were significant in 7/150 simulations (4.7%) on "
                "ExtraTrees and 3/150 (2.0%) on CatBoost."
            ),
            (
                "Replaced generic 'recovered' language with the number and "
                "direction of recovered cases, and clarified what the null "
                "rate measures."
            ),
        ),
        TextEdit(
            "5.10 Benchmark Calibration and Source Diagnostics, paragraph 2",
            "Effect decomposition showed",
            (
                "Effect decomposition identified endpoints where an apparent "
                "QRC-versus-base gain did not remain after the matched "
                "orthogonal contribution was removed. Among the six "
                "ExtraTrees endpoints with a positive QRC-versus-base point "
                "estimate, two had a non-positive QRC-specific effect; on "
                "CatBoost, three of four such endpoints were neutralized. When "
                "both branches were selected on validation, QRC beat the "
                "orthogonal map on 13/22 ExtraTrees and 12/22 CatBoost "
                "endpoints, a near-balanced result rather than a cross-base "
                "advantage."
            ),
            (
                "Removed the repeated connector and stated the attribution "
                "finding through the concrete comparison that produced it."
            ),
        ),
        TextEdit(
            "5.10 Benchmark Calibration and Source Diagnostics, paragraph 3",
            "Capacity diagnostics showed",
            (
                "Feature-capacity diagnostics indicated that the QRC branch was "
                "not advantaged by higher-dimensional test features. The mean "
                "test effective rank over 15 readouts was 14.10 for QRC versus "
                "14.62 for the orthogonal control on ExtraTrees, and 12.82 "
                "versus 14.25 on CatBoost. Linear centered-kernel alignment "
                "between the five-map mean QRC and orthogonal features was "
                "0.20 and 0.30, respectively, showing distinct geometries at "
                "comparable output and fitted-parameter budgets."
            ),
            (
                "Separated capacity evidence from the source gradient and "
                "removed the unsupported implication that all capacities were "
                "equal."
            ),
        ),
        TextEdit(
            "6.1 What the Constrained Quadratic Map Explains, paragraph 1",
            "With real amplitude inputs",
            (
                "With real amplitude inputs, every Z or ZZ expectation after "
                "fixed evolution is a real symmetric quadratic form. "
                "Training-side standardization is affine, so the linear "
                "readout combines these forms and adds a fixed offset. Given "
                "the fitted parameters, the QRC residual can therefore be "
                "reproduced by a real quadratic form and a constant on the "
                "normalized 32-dimensional latent input. This statement applies "
                "to that latent space, not to the raw molecular graph. All five "
                "QRC readout matrices had rank 15 and a median condition number "
                "of 1.210; the real-orthogonal readout matrices had rank 15 and "
                "condition number 1.000. On held-out molecular features, "
                "effective rank was 14.10 versus 14.62 on ExtraTrees and 12.82 "
                "versus 14.25 on CatBoost, with linear centered-kernel "
                "alignments of 0.20 and 0.30. The branches therefore had equal "
                "output and fitted-parameter budgets, different geometry, and "
                "comparable but not identical effective feature capacity."
            ),
            (
                "Distinguished full-rank readout matrices from held-out feature "
                "effective rank and removed the unsupported phrase that nominal "
                "capacities were equal."
            ),
        ),
    ]

    for edit in edits:
        _apply_edit(document, edit, changes)

    # Split the statistical paragraph after the calculation description.
    primary_stats = _find_unique(
        document,
        "The primary effect was computed from unrounded predictions",
    )
    t_ost_text = (
        "Exploratory TOST used margins of 0.01 for AUROC, AUPRC, and "
        "Spearman and 2% of base MAE for MAE. These thresholds define "
        "practical benchmark equivalence, not clinical limits. Practical "
        "equivalence was reported only when the 90% confidence interval lay "
        "inside the prespecified margin and the equivalence test remained "
        "significant after Holm correction. Results are therefore classified "
        "as significant degradation, significant improvement, practical "
        "equivalence, or unresolved. Equivalence does not imply identical "
        "mechanisms or identical per-molecule predictions."
    )
    inserted_paragraph = _insert_after(primary_stats, t_ost_text)
    inserted.append(
        {
            "location": "3 Data, Splits, and Statistical Evaluation, paragraph 3",
            "text": inserted_paragraph.text,
            "purpose": "Separated hypothesis testing from TOST interpretation.",
        }
    )

    # Split the external-validation paragraph before the rank-transfer analysis.
    external = _find_unique(document, "Figure 3 decomposes the hERG and B3DB")
    continuous_external = (
        "The continuous-label rank transfer produced an unadjusted "
        "CatBoost/hERG pIC50 Spearman difference of +0.043. This difference "
        "did not survive Holm correction across 12 comparisons and did not "
        "replicate for BBB logBB. Because it ranks predictions from "
        "binary-trained models, it is not an independently trained regression "
        "evaluation; the B3DB continuous subset is 86.8% positive."
    )
    inserted_paragraph = _insert_after(external, continuous_external)
    inserted.append(
        {
            "location": "5.5 Independent External Endpoints, paragraphs 3-4",
            "text": inserted_paragraph.text,
            "purpose": "Separated external effect decomposition from continuous-label transfer.",
        }
    )

    # Insert the circuit-level audit between regression and calibration.
    calibration_heading = _find_unique(
        document,
        "5.10 Benchmark Calibration and Source Diagnostics",
    )
    circuit_heading = _insert_before(
        calibration_heading,
        "5.9 Circuit-Level Aer Audit",
        style="Heading 2",
    )
    circuit_paragraph_1 = _insert_before(
        calibration_heading,
        (
            "We also examined circuit-specific readout degradation with "
            "explicit Qiskit circuits: 32-dimensional amplitude preparation, "
            "an eight-step Lie-Trotter fixed-Hamiltonian evolution, and "
            "all-qubit Z-basis measurement. The panel covered eight "
            "representative endpoints, 32 stratified test states per endpoint, "
            "and five reservoir maps; transpiled circuits had depth 81 and "
            "about 136 operations. Aer density-matrix simulation included "
            "one- and two-qubit gate depolarizing errors plus independent "
            "readout flips."
        ),
        style="Normal",
    )
    circuit_paragraph_2 = _insert_before(
        calibration_heading,
        (
            "Relative to exact matrix readouts, normalized RMSE was "
            "0.189-0.199, 0.337-0.351, and 0.551-0.569 at low, medium, and "
            "high error, respectively. Signal slopes were approximately 0.81, "
            "0.66, and 0.45, whereas Spearman correlations remained "
            "0.9974-0.9986, 0.9916-0.9958, and 0.9742-0.9866. The noiseless "
            "Trotterized RMSE was 0.0058-0.0070. Circuit errors mainly "
            "contracted readout amplitude while retaining substantial relative "
            "ordering; they did not add new advantage evidence. This is a "
            "readout-fidelity audit, not end-to-end retraining on noisy "
            "features. Full results are reported in Supplementary Figure S5 and "
            "Supplementary Table S11."
        ),
        style="Normal",
    )
    inserted.extend(
        [
            {
                "location": "5.9 Circuit-Level Aer Audit",
                "text": circuit_heading.text,
                "purpose": "Separated an unrelated audit from continuous regression.",
            },
            {
                "location": "5.9 Circuit-Level Aer Audit, paragraph 1",
                "text": circuit_paragraph_1.text,
                "purpose": "Placed circuit design before its results.",
            },
            {
                "location": "5.9 Circuit-Level Aer Audit, paragraph 2",
                "text": circuit_paragraph_2.text,
                "purpose": "Made circuit evidence and its interpretation contiguous.",
            },
        ]
    )

    # Add the external similarity result as its own paragraph.
    capacity = _find_unique(
        document,
        "Feature-capacity diagnostics indicated",
    )
    source_text = (
        "External stratification did not follow a monotonic similarity "
        "gradient. For CatBoost/hERG, QRC-specific AUROC changed from +0.003 "
        "in Q1 to +0.037, +0.070, and +0.013 across Q2-Q4; the Q3 interval "
        "[+0.011, +0.128] excluded zero. ExtraTrees showed a different "
        "pattern, with QRC-specific effects of -0.064, -0.059, +0.055, and "
        "-0.006 across Q1-Q4; the Q3 interval was [+0.018, +0.092]. B3DB "
        "showed no consistently positive quartile. The hERG signal is "
        "therefore localized and source-specific rather than a simple "
        "function of nearest-TDC similarity."
    )
    inserted_paragraph = _insert_after(capacity, source_text)
    inserted.append(
        {
            "location": "5.10 Benchmark Calibration and Source Diagnostics, paragraph 4",
            "text": inserted_paragraph.text,
            "purpose": "Connected the source-dependence claim to non-monotonic quartile evidence.",
        }
    )

    # Split the strong-base discussion into evidence and interpretation.
    strong_base = _find_unique(document, "The strong-base experiment")
    strong_base_before = strong_base.text
    _replace(
        strong_base,
        (
            "The strong-base comparison provides a direct stress test. "
            "MapLight-CatBoost outperformed Morgan-ExtraTrees on 21/22 "
            "endpoints, but QRC's relative advantage did not persist on the "
            "stronger base. Validation gating, finite shots, low-data scaling, "
            "and simulated noise therefore did not reveal a transferable "
            "quantum correction. The circuit audit likewise showed readout "
            "attenuation without new advantage evidence."
        ),
    )
    changes.append(
        {
            "location": "6.3 What the Strong Base and External Cohorts Reveal, paragraph 1",
            "before": strong_base_before,
            "after": strong_base.text,
            "reason": (
                "Deleted an undefined comparison with a preliminary pilot and "
                "stated the role of the strong base directly."
            ),
        }
    )
    discussion_next_heading = _find_unique(
        document,
        "6.4 Chemical-Space and Source Dependence",
    )
    source_interpretation = _insert_before(
        discussion_next_heading,
        (
            "The external results support only a source-specific candidate on "
            "hERG. The same direction appeared in pIC50 rank transfer and "
            "independent regression, but neither survived the joint "
            "multiplicity correction. B3DB logBB was near zero and B3DB BBB "
            "classification degraded significantly, so the hERG result cannot "
            "be generalized across sources. These findings support testing "
            "future quantum encodings on a strong classical base with matched "
            "input, capacity, and candidate budgets; they do not establish a "
            "general ADMET descriptor."
        ),
        style="Normal",
    )
    inserted.append(
        {
            "location": "6.3 What the Strong Base and External Cohorts Reveal, paragraph 2",
            "text": source_interpretation.text,
            "purpose": "Separated the evidence summary from the design implication and removed repeated scope language.",
        }
    )

    # Update the chemical-space discussion with the completed quartile analysis.
    external_audit = _find_unique(
        document,
        "We added a descriptive chemical-space audit",
    )
    external_audit_before = external_audit.text
    _replace(
        external_audit,
        (
            "A descriptive chemical-space audit tested whether cohort "
            "differences could reflect source proximity. Both cohorts were free "
            "of exact canonical identities from the corresponding TDC archive. "
            "For hERG, 23 of 293 molecules (7.8%) retained a Bemis-Murcko "
            "scaffold present in TDC train/validation data; the median nearest "
            "Morgan Tanimoto similarity (radius 2, 2048 bits) was 0.234 and the "
            "90th percentile was 0.423. For B3DB BBB, 562 of 2,317 molecules "
            "(24.3%) shared a TDC train/validation scaffold, with a median "
            "nearest similarity of 0.346 and a 90th percentile of 0.722. B3DB "
            "contained 48.9% positives versus 76.4% in the full TDC BBB "
            "archive, whereas hERG contained 76.4% versus 68.9% in TDC. The two "
            "cohorts therefore differed from their TDC sources in both "
            "chemical proximity and label composition."
        ),
    )
    changes.append(
        {
            "location": "6.4 Chemical-Space and Source Dependence, paragraph 1",
            "before": external_audit_before,
            "after": external_audit.text,
            "reason": (
                "Replaced an unnecessary description of the authors' action "
                "with a direct statement of what the analysis tested."
            ),
        }
    )

    stratum = _find_unique(
        document,
        "Re-scoring the existing held-out predictions",
    )
    stratum_before = stratum.text
    _replace(
        stratum,
        (
            "Stratifying the held-out predictions did not support a simple "
            "scaffold-overlap or similarity explanation for the hERG signal. "
            "For CatBoost, the hERG gated-QRC minus gated-orthogonal effect was "
            "-0.0026 AUROC among the 23 molecules with a shared "
            "train/validation scaffold and +0.0452 among the 270 molecules with "
            "a novel scaffold. The earlier top-quartile split gave +0.0196 in "
            "the highest-similarity group and +0.0494 in the other three "
            "quartiles. The finer quartile analysis was non-monotonic: "
            "CatBoost and ExtraTrees were positive in Q3 but not in every "
            "adjacent quartile. B3DB effects were negative across shared-scaffold, "
            "novel-scaffold, and most similarity strata. Full source audits "
            "are reported in Supplementary Tables S5, S6, and S16. These "
            "descriptive strata locate where an effect appears; they do not "
            "control source, assay batch, or label definition and cannot "
            "establish a causal chemical mechanism."
        ),
    )
    changes.append(
        {
            "location": "6.4 Chemical-Space and Source Dependence, paragraph 2",
            "before": stratum_before,
            "after": stratum.text,
            "reason": (
                "Aligned the discussion with the expanded quartile analysis and "
                "removed wording that suggested a monotonic source gradient."
            ),
        }
    )

    # Give the broader interpretation its own heading.
    low_data_interpretation = _find_unique(
        document,
        "A low-dimensional fixed quantum reservoir",
    )
    interpretation_heading = _insert_before(
        low_data_interpretation,
        "6.5 Interpretation and Reuse",
        style="Heading 2",
    )
    inserted.append(
        {
            "location": "6.5 Interpretation and Reuse",
            "text": interpretation_heading.text,
            "purpose": "Separated interpretation boundaries from the chemical-space description.",
        }
    )
    interpretation = _find_unique(
        document,
        "The hERG point improvement is a candidate signal",
    )
    interpretation_before = interpretation.text
    _replace(
        interpretation,
        (
            "Neither the hERG candidate nor the B3DB negative transfer "
            "establishes a mechanistic or general quantum effect. The reviewed "
            "QML-ADMET studies use different fixed reservoirs, "
            "Hamiltonian-derived features, quantum-inspired preprocessing, "
            "circuit search, or jointly trained residuals. Their task counts, "
            "controls, and external validation settings therefore do not support "
            "like-for-like equivalence. Table 1 summarizes the design "
            "differences, and Supplementary Table S4 provides the expanded "
            "comparison. The study contributes a reusable minimum evaluation "
            "protocol: prespecify the primary comparator, match candidate and "
            "map budgets, infer with scaffold clusters, correct across "
            "endpoints, interpret equivalence separately from superiority, and "
            "report both cross-base and cross-source results."
        ),
    )
    changes.append(
        {
            "location": "6.5 Interpretation and Reuse, paragraph 2",
            "before": interpretation_before,
            "after": interpretation.text,
            "reason": (
                "Combined the two broad negative statements into one bounded "
                "interpretation and kept the literature differences connected "
                "to the evaluation protocol."
            ),
        }
    )

    # Consolidate limitations into three thematic paragraphs.
    limitation_1 = _find_unique(document, "The fixed official test set")
    limitation_1_before = limitation_1.text
    _replace(
        limitation_1,
        (
            "Three evaluation limits constrain generalization. The public TDC "
            "test sets may have been reused by earlier studies and are not "
            "prospective cohorts; scaffold splits reduce, but do not eliminate, "
            "near analogues across laboratories, time, and chemical series. The "
            "low-data analysis covers eight endpoints, and its 96-record "
            "minimum changes the effective fraction for the smallest endpoints. "
            "The primary external comparison contains two classification "
            "cohorts that differ in assay source and label construction [3-5]."
        ),
    )
    changes.append(
        {
            "location": "7 Limitations, paragraph 1",
            "before": limitation_1_before,
            "after": limitation_1.text,
            "reason": (
                "Grouped related evaluation limitations and placed the "
                "non-clinical equivalence caveat with the statistical scope."
            ),
        }
    )

    limitation_2 = _find_unique(
        document,
        "We evaluate independent per-molecule inputs",
    )
    limitation_2_before = limitation_2.text
    _replace(
        limitation_2,
        (
            "The execution boundary is equally explicit. Exact state-vector "
            "calculation isolates the fixed circuit's expressive behavior but "
            "does not evaluate physical gate error, readout crosstalk, "
            "connectivity, or scheduling. Finite-shot analysis samples each "
            "Pauli expectation independently. The simplified depolarizing model "
            "omits gate-specific error, leakage, crosstalk, and physical "
            "scheduling. The Qiskit/Aer audit adds transpiled gate "
            "depolarization and readout flips, but uses fixed synthetic error "
            "parameters and does not retrain the full predictor on "
            "circuit-noisy features. Trainable circuits, task-conditioned "
            "amplitude encoding, and other PCA dimensions were not evaluated."
        ),
    )
    changes.append(
        {
            "location": "7 Limitations, paragraph 2",
            "before": limitation_2_before,
            "after": limitation_2.text,
            "reason": (
                "Removed repeated broad negatives and retained each real "
                "hardware or circuit omission once."
            ),
        }
    )

    conclusion_heading = _find_unique(document, "8 Conclusion")
    limitation_3 = _insert_before(
        conclusion_heading,
        (
            "The auxiliary analyses have narrower scope. Continuous-label "
            "transfer ranks outputs from binary-trained models and is not an "
            "independently trained regression. The separate pIC50 regression "
            "uses 214 test molecules in 155 scaffolds under a fixed protocol "
            "and has limited statistical power. B3DB logBB was available for "
            "only 613/2,317 non-overlapping molecules and was strongly "
            "class-enriched. The chemical-space figure uses a linear "
            "fingerprint projection and three basic descriptors, not a complete "
            "applicability-domain model, and TOST margins are exploratory "
            "benchmark thresholds rather than clinical or regulatory limits "
            "[21]. Random-map sensitivity covers five realizations per family. "
            "The known-signal calibration uses synthetic targets drawn from the "
            "tested feature families; it establishes detectability for those "
            "designs, not coverage of every possible nonlinear signal. "
            "The reported comparison therefore applies to five-qubit amplitude "
            "encoding, a fixed Hamiltonian reservoir, 15 Pauli readouts, a "
            "linear residual head, and exact simulation; other encodings, "
            "trainable circuits, larger reservoirs, and physical hardware "
            "require independent evaluation."
        ),
        style="Normal",
    )
    inserted.append(
        {
            "location": "7 Limitations, paragraph 3",
            "text": limitation_3.text,
            "purpose": (
                "Consolidated auxiliary-analysis limits and stated the final "
                "scope once."
            ),
        }
    )

    # Split the conclusion into empirical result and contribution.
    conclusion = _find_unique(document, "Across 22 official TDC ADMET endpoints")
    conclusion_before = conclusion.text
    _replace(
        conclusion,
        (
            "Across 22 official TDC ADMET endpoints, fixed five-qubit reservoir "
            "residuals showed no stable increment over real-orthogonal "
            "quadratic maps with the same readout dimension, fitted-parameter "
            "budget, and map budget. This result held on both "
            "Morgan-ExtraTrees and the stronger MapLight-CatBoost base. "
            "Validation gating reduced harmful residuals but did not produce a "
            "stable advantage over gated classical controls. Joint gating, "
            "low-data scaling, finite shots, and simulated decoherence did not "
            "reverse the result. External hERG produced a CatBoost-specific "
            "candidate signal, whereas B3DB BBB showed significant negative "
            "transfer. Continuous-label transfer and independent pIC50 "
            "regression showed only uncorrected weak CatBoost/hERG directions, "
            "and neither had a corresponding BBB signal. Known-signal "
            "calibration recovered the synthetic QRC and classical targets, "
            "and null false-positive rates remained at or below 5%."
        ),
    )
    changes.append(
        {
            "location": "8 Conclusion, paragraph 1",
            "before": conclusion_before,
            "after": conclusion.text,
            "reason": (
                "Converted a single dense paragraph into an evidence summary "
                "that does not repeat the full limitations list."
            ),
        }
    )

    data_heading = _find_unique(document, "Data and Code Availability")
    conclusion_2 = _insert_before(
        data_heading,
        (
            "The study's main contribution is therefore a calibrated "
            "matched-evaluation workflow that distinguishes ordinary quadratic "
            "effects, reservoir-specific candidate effects, and source "
            "dependence. The hERG signal is a bounded candidate, not a "
            "demonstrated mechanism of cardiotoxicity, and the B3DB result does "
            "not show that quantum methods are universally ineffective. The "
            "conclusion applies to the tested five-qubit amplitude-encoded, "
            "fixed-Hamiltonian reservoir with 15 Pauli readouts, a linear "
            "residual head, and exact simulation; other encodings, trainable "
            "circuits, larger reservoirs, and physical hardware require "
            "independent evaluation."
        ),
        style="Normal",
    )
    inserted.append(
        {
            "location": "8 Conclusion, paragraph 2",
            "text": conclusion_2.text,
            "purpose": "Separated the methodological contribution and final scope from the result summary.",
        }
    )

    # Split availability information into data and software.
    availability = _find_unique(document, "The official TDC archive is available")
    before_availability = availability.text
    _replace(
        availability,
        (
            "The official TDC archive is available as Harvard Dataverse file "
            "4426004 with SHA-256 "
            "bd0005246cb6f1672333c28ad202112a8bf071ab65d847848715030308faf1f1. "
            "External hERG data are from Zenodo 5807719 and BBB data from B3DB. "
            "Source, label rules, deduplication, and overlap audits are included "
            "in the reproduction package. The MapLight reference and MIT "
            "license are retained, and upstream data licenses are listed with "
            "the archived materials."
        ),
    )
    changes.append(
        {
            "location": "Data and Code Availability, paragraph 1",
            "before": before_availability,
            "after": availability.text,
            "reason": (
                "Made the availability statement easier to audit and kept the "
                "same identifiers."
            ),
        }
    )

    refs_heading = _find_unique(document, "References")
    availability_2 = _insert_before(
        refs_heading,
        (
            "The reproduction package contains processing scripts, five "
            "scaffold splits, five random maps per family, base configurations, "
            "all split-level predictions, gating, finite-shot, low-data, "
            "external decomposition and calibration, continuous-label transfer, "
            "independent pIC50 regression, simplified and circuit-level noise, "
            "bounded-family, TOST-sensitivity, effect-decomposition, "
            "capacity, and source-gradient results, statistical scripts, "
            "figure-generation code, and environment locks. The versioned code "
            "and result index are at "
            "https://github.com/575914291-source/"
            "qrc-admet-matched-evaluation. Official test labels were used only "
            "for scoring after configuration lock and were not used for "
            "training, map generation, joint weights, or gating."
        ),
        style="Normal",
    )
    inserted.append(
        {
            "location": "Data and Code Availability, paragraph 2",
            "text": availability_2.text,
            "purpose": "Separated the software inventory and test-label handling from source-data provenance.",
        }
    )

    # Replace table evidence references after adding calibration and diagnostics.
    table6 = document.tables[-1]
    cell_updates = {
        "Methods 3; Figure 4; Table 5": "Section 3; Figure 4; Table 5",
        "Figure 3; Tables S7-S10": "Figure 3; Tables S7-S10, S16",
        "Tables 3-5; Figures S1-S5": "Tables 3-5, S12-S16; Figures S1-S10",
        "Methods 4.2; Limitations; Figure S5": "Methods 4.2, 4.4; Limitations; Figures S5-S10",
    }
    for row in table6.rows:
        for cell in row.cells:
            if cell.text in cell_updates:
                old_text = cell.text
                new_text = cell_updates[old_text]
                cell.text = new_text
                inserted.append(
                    {
                        "location": "Table 6",
                        "text": f"{old_text} -> {new_text}",
                        "purpose": "Updated evidence cross-references.",
                    }
                )

    # Normalize spelling in the English body, leaving reference titles intact.
    reference_started = False
    spelling = {
        "favour": "favor",
        "Favour": "Favor",
        "favours": "favors",
        "favoured": "favored",
        "favouring": "favoring",
        "behaviour": "behavior",
        "neighbour": "neighbor",
        "neighbouring": "neighboring",
        "labelled": "labeled",
    }
    for paragraph in document.paragraphs:
        if paragraph.text.strip() == "References":
            reference_started = True
        if reference_started:
            continue
        updated = paragraph.text
        for old, new in spelling.items():
            updated = updated.replace(old, new)
        if updated != paragraph.text:
            _replace(paragraph, updated)

    # Normalize full-width punctuation in the English reference list.
    reference_started = False
    for paragraph in document.paragraphs:
        if paragraph.text.strip() == "References":
            reference_started = True
            continue
        if reference_started and re.match(r"^\d+\.", paragraph.text.strip()):
            updated = paragraph.text.replace("，", ", ")
            if updated != paragraph.text:
                _replace(paragraph, updated)

    # Remove redundant inference markers where the evidence-to-result
    # relation is already explicit in the sentence.
    connector_replacements = {
        "We therefore evaluated": "We evaluated",
        "Differences between these branches therefore reflect":
            "Differences between these branches reflect",
        "Results are therefore classified": "Results are classified",
        "Gated results therefore indicate": "Gated results indicate",
        "and was therefore excluded": "and was excluded",
        "primary difference therefore combines": "primary difference combines",
        "and therefore tests sensitivity": "and tests sensitivity",
        "orthogonal family therefore had": "orthogonal family had",
        "hERG signal is therefore localized": "hERG signal was localized",
        "residual can therefore be reproduced": "residual can be reproduced",
        "branches therefore had": "branches had",
        "simulated noise therefore did not reveal": "simulated noise did not reveal",
        "cohorts therefore differed": "cohorts differed",
        "settings therefore do not support": "settings do not support",
        "comparison therefore applies": "comparison applies",
        "contribution is therefore a calibrated": "contribution is a calibrated",
    }
    reference_started = False
    for paragraph in document.paragraphs:
        if paragraph.text.strip() == "References":
            reference_started = True
        if reference_started:
            continue
        updated = paragraph.text
        for old, new in connector_replacements.items():
            updated = updated.replace(old, new)
        if updated != paragraph.text:
            _replace(paragraph, updated)

    def normalize_post_edit(text: str) -> str:
        for old, new in spelling.items():
            text = text.replace(old, new)
        for old, new in connector_replacements.items():
            text = text.replace(old, new)
        return text

    for change in changes:
        change["after"] = normalize_post_edit(change["after"])
    for item in inserted:
        item["text"] = normalize_post_edit(item["text"])

    document.core_properties.title = document.paragraphs[0].text
    document.core_properties.subject = document.paragraphs[1].text
    document.core_properties.author = ""
    document.core_properties.comments = (
        "Editorially revised JCAMD submission manuscript; author metadata pending."
    )
    document.save(REVISED)
    report = {
        "source": str(SOURCE),
        "revised": str(REVISED),
        "changes": changes,
        "insertions": inserted,
        "scope": (
            "English JCAMD submission manuscript; facts, numerical values, "
            "and citation identities were preserved."
        ),
    }
    REPORT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_markdown_report(report)
    return report


def _write_markdown_report(report: dict[str, object]) -> None:
    lines = [
        "---",
        'title: "论文全文修改报告"',
        'subtitle: "代表性前后对照与具体改善"',
        'date: "2026-11-26"',
        "lang: zh-CN",
        "---",
        "",
        "## 修改范围",
        "",
        (
            "本次修改针对英文 JCAMD 投稿全文。研究问题、模型、数据集、"
            "全部数值、实验判断和引文编号保持不变；未新增文献立场或"
            "未做实验。修改集中在段落功能、衔接、句法、范围界定、"
            "结果分组和重复防御表达。"
        ),
        "",
        "## 总体改善",
        "",
        (
            "- 将统计计算与 TOST 解释拆成独立段落。"
        ),
        (
            "- 将连续 pIC50 回归与 Qiskit/Aer 电路审计拆成独立 Results "
            "章节，并相应重排编号。"
        ),
        (
            "- 把扩大后的容量诊断与外部相似度四分位结果写入讨论，"
            "避免把读出矩阵满秩写成样本特征容量相等。"
        ),
        (
            "- 将局限重写为评估、量子执行和辅助分析三个主题，"
            "说明每项限制影响哪一类推断。"
        ),
        (
            "- 将结论拆为经验结果与方法贡献，避免在摘要、讨论、"
            "局限和结论中重复同一段防御性表述。"
        ),
        (
            "- 统一英美拼写，并清除英文参考文献中的全角标点。"
        ),
        "",
        "## 七项检查结果",
        "",
        "| 检查项 | 发现的问题 | 已采取的处理 |",
        "|---|---|---|",
        (
            "| 段落功能 | 统计计算与 TOST 解释同段；连续回归与电路审计同节；"
            "部分研究过程缺少定义 | 拆分统计、TOST、回归和电路章节；"
            "补充 exploratory pilot 的四个具体端点，并说明其不进入确证推断 |"
        ),
        (
            "| 标点与套话 | 英文参考文献中存在 7 处全角逗号；少量压缩标签"
            "信息不足 | 统一英文标点；将压缩标签改为可核对的说明 |"
        ),
        (
            "| 衔接 | therefore 等连接词在部分句子中重复，但未发现连续冒号滥用 | "
            "仅删除可由论据直接表达的连接词；保留 TOST 分类和命题推导所需的"
            "逻辑标记 |"
        ),
        (
            "| 文献 | 部分近邻研究只写“做了什么”，未说明其结果和适用范围 | "
            "对 Beaulieu、Benson、Mansour、Zheng、Jia、Garg、Wang 的结果"
            "方向、控制方式和任务范围作了更明确的区分 |"
        ),
        (
            "| 句式 | 结果段落有重复的主语—动词序列 | 重写为“对象—比较—结果”"
            "顺序，不改变数值 |"
        ),
        (
            "| 分析 | 容量讨论把读出矩阵满秩与样本特征有效秩混在一起 | "
            "区分矩阵秩、条件数、held-out effective rank 和 CKA |"
        ),
        (
            "| 防御表达 | 摘要、讨论、局限和结论重复说明“不能外推” | "
            "将限制按评估、执行和辅助分析三类集中陈述，各保留一次 |"
        ),
        "",
        "## 文献适用范围核对",
        "",
        (
            "- Beaulieu 等工作支持小样本固定储层与嵌入可分性的讨论，"
            "不支持对其它编码或真实硬件的普遍推断。"
        ),
        (
            "- Benson 等报告的是 Hamiltonian 衍生特征与完整经典表示拼接"
            "后的 10 任务结果，不等同于本研究的同容量固定残差控制。"
        ),
        (
            "- Mansour 等的二次多项式消融说明量子启发特征可能被经典"
            "交互项解释，直接支持本文加入显式二次控制。"
        ),
        (
            "- Zheng 等研究线路搜索与 sim-to-real，Garg 等研究跨靶点"
            "量子分类基准；两者与本研究的固定线路匹配评估对象不同。"
        ),
        (
            "- Jia 等同样使用幅度编码残差和实正交控制，但其编码器与"
            "量子头联合训练，且任务是受体效价而非 ADMET。"
        ),
        (
            "- Wang 等研究序列图事件、Floquet 驱动和硬件执行，"
            "支持“输入和动力学改变结论”的边界说明，不进入本文主比较。"
        ),
        "",
        "## 代表性上下文前后对照",
        "",
    ]
    representative_locations = (
        "Abstract, paragraph 1",
        "1 Introduction, paragraph 2",
        "2.2 Quantum Molecular Features and Structural Controls, paragraph 1",
        "4.2 Five-Qubit Reservoir and Matched Classical Features, Proposition 1",
        "5.1 Overall Results, paragraph 1",
        "5.10 Benchmark Calibration and Source Diagnostics, paragraph 1",
        "6.1 What the Constrained Quadratic Map Explains, paragraph 1",
        "6.4 Chemical-Space and Source Dependence, paragraph 2",
        "7 Limitations, paragraph 1",
        "8 Conclusion, paragraph 1",
        "Data and Code Availability, paragraph 1",
    )
    selected_changes = [
        change
        for change in report["changes"]
        if change["location"] in representative_locations
    ]
    lines.extend(
        [
            (
                f"本节列出 {len(selected_changes)} 个代表性修改；"
                "其余修改保留在完整 JSON 日志中。"
            ),
            "",
        ]
    )
    for index, change in enumerate(selected_changes, start=1):
        lines.extend(
            [
                f"### {index}. {change['location']}",
                "",
                "**原文**",
                "",
                change["before"],
                "",
                "**修改后**",
                "",
                change["after"],
                "",
                "**具体改善**",
                "",
                change["reason"],
                "",
            ]
        )
    lines.extend(
        [
            "## 新增与重排段落",
            "",
        ]
    )
    for item in report["insertions"]:
        lines.extend(
            [
                f"- **{item['location']}**：{item['purpose']}",
                "",
                f"  {item['text']}",
                "",
            ]
        )
    lines.extend(
        [
            "## 未发现的问题",
            "",
            (
                "- 未发现需要删除的虚假引用，也未改动任何研究数字、"
                "指标方向或实验判断。"
            ),
            (
                "- 未把句式变化当作作者身份证据，也未对作者身份作任何推断。"
            ),
            (
                "- 未发现连续冒号堆叠或成组的空泛排比；不存在的风格问题"
                "没有为了“改得多”而强行添加。"
            ),
            (
                "- 对已有引用，保留了原编号和基本立场。近距离 QML 分子"
                "预测工作继续按固定储层、Hamiltonian 特征、线路搜索、"
                "可训练残差和序列储层的适用范围分别表述。"
            ),
            "",
            "## 逐项交付对照",
            "",
            (
                f"本次共记录 {len(report['changes'])} 处段落级修改和 "
                f"{len(report['insertions'])} 处新增或重排。完整修改日志见 "
                "`Manuscript_Revision_Changes.json`；本报告保留具有代表性的"
                "上下文对照，没有把所有改动机械展开。"
            ),
            "",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = refine()
    print(
        json.dumps(
            {
                "revised": report["revised"],
                "report_md": str(REPORT_MD),
                "report_json": str(REPORT_JSON),
                "representative_changes": len(report["changes"]),
                "insertions": len(report["insertions"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
