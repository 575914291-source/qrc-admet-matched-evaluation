from __future__ import annotations

import json

import pandas as pd

from src.config import RESULTS_ROOT, TASKS
from src.data import load_task_frames, write_json


TABLE_ROOT = RESULTS_ROOT / "manuscript" / "tables"
DIAGNOSTIC_ROOT = RESULTS_ROOT / "external_diagnostics"


def _label_summary(series: pd.Series, kind: str) -> str:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if kind == "classification":
        return f"{100 * float(values.mean()):.1f}% positive"
    return (
        f"median {values.median():.3g} "
        f"(IQR {values.quantile(0.25):.3g}-{values.quantile(0.75):.3g})"
    )


def build_endpoint_characteristics() -> pd.DataFrame:
    rows = []
    for spec in TASKS:
        frames = load_task_frames(spec.name)
        rows.append(
            {
                "endpoint": spec.name,
                "task_type": spec.kind,
                "metric": spec.metric,
                "n_train_valid": int(len(frames.train_val)),
                "n_test": int(len(frames.test)),
                "train_valid_label_summary": _label_summary(
                    frames.train_val["Y"],
                    spec.kind,
                ),
                "test_label_summary": _label_summary(
                    frames.test["Y"],
                    spec.kind,
                ),
            }
        )
    frame = pd.DataFrame(rows)
    frame.to_csv(
        TABLE_ROOT / "endpoint_characteristics.csv",
        index=False,
        encoding="utf-8-sig",
    )
    return frame


def build_analysis_hierarchy() -> pd.DataFrame:
    rows = [
        {
            "analysis_tier": "Primary",
            "question": "Does ungated QRC improve over the matched quadratic control?",
            "scope": "22 endpoints x 2 bases",
            "inference": (
                "Paired scaffold bootstrap and permutation; Holm across 22 "
                "endpoints within each base"
            ),
        },
        {
            "analysis_tier": "Predefined secondary",
            "question": (
                "How do Fourier features, residual-free bases, gating, and joint "
                "QRC-plus-orthogonal corrections compare?"
            ),
            "scope": "22 endpoints x 2 bases x predefined contrasts",
            "inference": (
                "Direction-normalized effects and endpoint-level confidence "
                "intervals; Holm within each reported comparison family"
            ),
        },
        {
            "analysis_tier": "Sensitivity",
            "question": (
                "Are conclusions stable to training size, finite shots, "
                "depolarizing attenuation, or reservoir-family selection?"
            ),
            "scope": "8 preselected endpoints and bounded candidate families",
            "inference": (
                "Direction counts and paired endpoint summaries; interpreted "
                "descriptively unless a comparison family is explicitly corrected"
            ),
        },
        {
            "analysis_tier": "External binary validation",
            "question": (
                "Does the matched comparison transfer to independent hERG and "
                "B3DB BBB collections?"
            ),
            "scope": "293 hERG and 2,317 B3DB molecules; 2 bases",
            "inference": (
                "Paired scaffold permutation/bootstrap; Holm across the external "
                "endpoint family; decomposition and calibration are secondary"
            ),
        },
        {
            "analysis_tier": "Exploratory label transfer",
            "question": (
                "Do binary-model outputs preserve continuous pIC50 or logBB ranking?"
            ),
            "scope": "hERG pIC50 and 613 B3DB logBB records; 12 contrasts",
            "inference": "Holm across all 12 exploratory comparisons",
        },
        {
            "analysis_tier": "Supplementary external regression",
            "question": (
                "Does QRC add value when directly trained for ToxTree hERG pIC50?"
            ),
            "scope": "214 scaffold-disjoint test molecules; 2 bases; 5 model seeds",
            "inference": (
                "Paired scaffold bootstrap/permutation; Holm across 12 metric/base/"
                "contrast tests"
            ),
        },
    ]
    frame = pd.DataFrame(rows)
    frame.to_csv(
        TABLE_ROOT / "analysis_hierarchy.csv",
        index=False,
        encoding="utf-8-sig",
    )
    return frame


def build_prior_study_comparison() -> pd.DataFrame:
    rows = [
        {
            "study": "Beaulieu et al. 2025",
            "molecular_setting": "Molecular activity prediction with small datasets",
            "quantum_or_hybrid_component": "Fixed quantum reservoir",
            "reporting_focus": (
                "Low-data robustness and separability of quantum reservoir embeddings"
            ),
            "relation_to_present_work": (
                "Motivates the low-data rationale; this study adds 22 endpoints, "
                "two strong bases, equal map budgets, external cohorts, and scope tests"
            ),
        },
        {
            "study": "Benson et al. 2026",
            "molecular_setting": "Ten TDC ADMET tasks",
            "quantum_or_hybrid_component": (
                "Hamiltonian-derived expectation values concatenated with classical features"
            ),
            "reporting_focus": (
                "Quantum-inspired features improved 8/10 tasks in the reported benchmark"
            ),
            "relation_to_present_work": (
                "Uses a different hybrid representation and output model; the present "
                "study isolates fixed-reservoir residuals against matched quadratic features"
            ),
        },
        {
            "study": "Mansour et al. 2026",
            "molecular_setting": "TDC AqSolDB solubility",
            "quantum_or_hybrid_component": (
                "Mutual-information Hamiltonian preprocessing with CatBoost"
            ),
            "reporting_focus": (
                "Ablation found comparable performance from a second-degree polynomial "
                "feature basis"
            ),
            "relation_to_present_work": (
                "Provides direct evidence that nonlinear quadratic structure should be "
                "controlled explicitly, as done here across 22 endpoints"
            ),
        },
        {
            "study": "Zheng et al. 2026",
            "molecular_setting": "8 imbalanced ADME classification and 4 regression tasks",
            "quantum_or_hybrid_component": "Search over quantum-circuit structures",
            "reporting_focus": (
                "Training-free circuit scoring and adaptation to imbalanced and continuous tasks"
            ),
            "relation_to_present_work": (
                "Focuses on circuit search; the present study fixes the circuit family "
                "and tests predictive transfer under a matched residual protocol"
            ),
        },
        {
            "study": "Jia et al. 2026",
            "molecular_setting": "GLP-1R, ADRB2, and MC4R receptor potency",
            "quantum_or_hybrid_component": "Jointly trained neural encoder and quantum residual",
            "reporting_focus": (
                "Parameter-matched real-orthogonal residuals had similar predictive performance"
            ),
            "relation_to_present_work": (
                "Supports the quadratic-control interpretation; differs in task, jointly "
                "trained representation, and the absence of an ADMET-wide benchmark"
            ),
        },
        {
            "study": "Garg and Garg 2026",
            "molecular_setting": "10 targets and 48 potency-classification tasks",
            "quantum_or_hybrid_component": "Quantum SVM and variational quantum classifier",
            "reporting_focus": (
                "No global quantum advantage; candidate signals were structurally sparse"
            ),
            "relation_to_present_work": (
                "Parallels the local-signal result and motivates scaffold clustering, "
                "strong controls, and source-level reporting"
            ),
        },
        {
            "study": "Wang et al. 2026",
            "molecular_setting": "Graph-prefix activity/BBB classification and molecular-gap forecasting",
            "quantum_or_hybrid_component": "Driven Floquet/DTM quantum reservoir",
            "reporting_focus": (
                "Matched echo-state comparisons and six-qubit hardware execution"
            ),
            "relation_to_present_work": (
                "Tests a different sequence input and driven dynamics; the present study "
                "uses independent molecules and a deliberately matched fixed quadratic family"
            ),
        },
    ]
    frame = pd.DataFrame(rows)
    frame.to_csv(
        TABLE_ROOT / "prior_qml_comparison.csv",
        index=False,
        encoding="utf-8-sig",
    )
    return frame


def build_external_validation_table() -> pd.DataFrame:
    diagnostics = pd.read_csv(
        DIAGNOSTIC_ROOT / "summary.csv",
        encoding="utf-8-sig",
    )
    calibration = pd.read_csv(
        DIAGNOSTIC_ROOT / "calibration_metrics.csv",
        encoding="utf-8-sig",
    )
    primary = pd.read_csv(
        RESULTS_ROOT / "external_validation" / "summary.csv",
        encoding="utf-8-sig",
    )
    rows = []
    for task in ("herg", "bbb_martins"):
        for base in ("extra_trees", "catboost"):
            cohort = calibration[
                (calibration.task == task) & (calibration.base == base)
            ].set_index("method")
            effect = diagnostics[
                (diagnostics.task == task)
                & (diagnostics.base == base)
                & (diagnostics.metric == "AUROC")
                & (diagnostics.method == "qrc_gated")
                & (diagnostics.reference == "orthogonal_gated")
            ].iloc[0]
            holm = primary[
                (primary.task == task)
                & (primary.base == base)
                & (primary.method == "qrc_gated")
                & (primary.reference == "orth_gated")
            ].holm_p.iloc[0]
            qrc = cohort.loc["qrc_gated"]
            orth = cohort.loc["orthogonal_gated"]
            rows.append(
                {
                    "cohort": "hERG" if task == "herg" else "B3DB BBB",
                    "base": base,
                    "n": int(effect.n),
                    "n_positive": int(effect.n_positive),
                    "prevalence": float(effect.prevalence),
                    "orthogonal_auroc": float(orth.auroc),
                    "qrc_auroc": float(qrc.auroc),
                    "qrc_minus_orthogonal": float(effect.effect_better_positive),
                    "ci_low": float(effect.ci_low),
                    "ci_high": float(effect.ci_high),
                    "holm_p": float(holm),
                    "qrc_auprc": float(qrc.auprc),
                    "qrc_brier": float(qrc.brier),
                    "orthogonal_brier": float(orth.brier),
                }
            )
    frame = pd.DataFrame(rows)
    frame.to_csv(
        TABLE_ROOT / "external_validation_table.csv",
        index=False,
        encoding="utf-8-sig",
    )
    return frame


def build_external_regression_table() -> pd.DataFrame | None:
    source = RESULTS_ROOT / "external_regression" / "comparisons.csv"
    if not source.exists():
        return None
    frame = pd.read_csv(source, encoding="utf-8-sig")
    frame.to_csv(
        TABLE_ROOT / "external_regression_table.csv",
        index=False,
        encoding="utf-8-sig",
    )
    return frame


def main() -> int:
    TABLE_ROOT.mkdir(parents=True, exist_ok=True)
    endpoints = build_endpoint_characteristics()
    hierarchy = build_analysis_hierarchy()
    prior = build_prior_study_comparison()
    external = build_external_validation_table()
    regression = build_external_regression_table()
    manifest = {
        "endpoint_rows": int(len(endpoints)),
        "hierarchy_rows": int(len(hierarchy)),
        "prior_study_rows": int(len(prior)),
        "external_validation_rows": int(len(external)),
        "external_regression_rows": (
            int(len(regression)) if regression is not None else 0
        ),
    }
    write_json(TABLE_ROOT / "extended_table_manifest.json", manifest)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
