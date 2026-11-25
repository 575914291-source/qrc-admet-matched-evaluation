from __future__ import annotations

import shutil
from pathlib import Path

from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn


SOURCE = Path(r"D:\论文\qrc_admet\outputs\论文修订稿_v2_TDC完整实验.docx")
OUTPUT = Path(
    r"D:\论文\qrc_admet\outputs\Matched_Evaluation_Fixed_Quantum_Reservoir_TDC_ADMET.docx"
)


TEXT = {
    0: "Matched Evaluation of Fixed Quantum Reservoir Residuals on TDC ADMET with Random Realizations and Strong Baselines",
    1: "A Reproducible Benchmark of Fixed Quantum Reservoir Features on TDC ADMET",
    2: "Abstract",
    3: (
        "Quantum reservoirs can generate low-dimensional nonlinear molecular features, "
        "but their incremental value must be tested against equally sized classical "
        "feature families and sufficiently strong base models. We compare exactly "
        "simulated five-qubit amplitude-encoded reservoirs with real-orthogonal "
        "quadratic maps and random Fourier features on all 22 official TDC ADMET "
        "endpoints, using Morgan-ExtraTrees and MapLight-CatBoost. Each endpoint uses "
        "five scaffold splits, and each random family uses five maps before residual "
        "averaging. Ungated QRC is better on 6 and worse on 16 ExtraTrees endpoints, "
        "and better on 3 and worse on 19 CatBoost endpoints. After Holm correction, no "
        "endpoint is significantly better and three are significantly worse. Gating, "
        "joint correction, low-data scaling, finite shots, simulated noise, and a "
        "bounded reservoir-family search do not produce a cross-base advantage. External "
        "validation is source-dependent: CatBoost improves by 0.040 AUROC on 293 "
        "non-overlapping hERG molecules but both bases degrade on 2,317 B3DB BBB "
        "molecules. The hERG difference combines a QRC gain and an orthogonal-branch "
        "decrement relative to the base. Continuous-label ranking and an independent "
        "pIC50 regression do not survive joint multiplicity correction. Scaffold, "
        "nearest-neighbour, and physicochemical analyses do not support a simple "
        "chemical-space explanation. The main contribution is a reproducible evaluation "
        "workflow. The conclusion is bounded by fixed five-qubit amplitude encoding, 15 "
        "Pauli readouts, a linear residual head, and exact state-vector simulation; it "
        "is not a general claim against other encodings, trainable circuits, larger "
        "reservoirs, or physical hardware."
    ),
    4: "Keywords: ADMET; TDC; quantum reservoir; matched classical controls; random realizations; validation gating",
    5: "1 Introduction",
    6: (
        "ADMET prediction includes binary, continuous, and ranking endpoints with large "
        "differences in sample size, measurement resolution, and chemical-space coverage. "
        "TDC provides fixed test sets, endpoint-specific metrics, and scaffold split "
        "interfaces, enabling endpoint-level verification [1,2]. Molecular representation, "
        "model family, and evaluation split can each alter model rankings [3-6]. The value "
        "of quantum features therefore cannot be inferred from a comparison with a single "
        "weak base model."
    ),
    7: (
        "We ask a bounded question. Under the same input, the same 15 readouts, and the "
        "same linear residual head, does a fixed five-qubit reservoir provide an increment "
        "relative to real-orthogonal quadratic maps and random Fourier features across "
        "the 22 TDC endpoints, two classical bases, and independent external sources? "
        "Figure 1 summarizes the design. The study makes three contributions. First, it "
        "formalizes the current QRC and linear residual head as a constrained real "
        "quadratic feature family and constructs an equal-input, equal-capacity, "
        "equal-map-budget quadratic control. Second, it evaluates the family across all "
        "22 endpoints with validation gating and multiple-testing correction. Third, it "
        "uses low-data, finite-shot, simulated-noise, bounded-family, two-source external, "
        "continuous-label, independent pIC50 regression, and chemical-space analyses to "
        "delimit the conclusion."
    ),
    8: "2 Related Work",
    9: "2.1 ADMET Benchmarks and Classical Representations",
    10: (
        "TDC endpoint definitions, fixed test sets, and scoring interfaces support "
        "verification, but a public official test set is not a prospective validation. "
        "Scaffold splits are more demanding than random splits, yet near analogues can "
        "remain and cannot replace a temporal holdout [1-5]. We use a corrected MapLight "
        "feature set with CatBoost as a strong classical reference [6,7,25,26]: 1,024 "
        "Morgan counts, 1,024 Avalon counts, 315 ErG dimensions, and 200 RDKit "
        "descriptors. The upstream count conversion used int8 and could overflow; we use "
        "int32 when rebuilding the feature cache."
    ),
    11: "2.2 Quantum Molecular Features and Structural Controls",
    12: (
        "Beaulieu et al. studied fixed reservoirs and small-sample molecular activity "
        "learning [8]. Benson et al. concatenated Hamiltonian-derived readouts with "
        "classical descriptors before CatBoost, and Mansour et al. reported errors from "
        "quantum-inspired preprocessing on AqSolDB [9,10]. QCS-ADME focused on circuit "
        "search and simulator-to-hardware variation [11]. Jia et al. compared five-qubit "
        "amplitude-encoded residuals with real-orthogonal branches, but jointly trained "
        "the encoder and prediction head and did not address ADMET [12]. A recent "
        "48-task potency benchmark found no global advantage for quantum classifiers "
        "over their classical comparators [27]. Floquet-QRC work has also used sequential "
        "graph events and driven reservoirs under a different input and dynamics "
        "setting [28]."
    ),
    13: (
        "Our primary control follows directly from the representation. For real "
        "amplitudes, each fixed-evolution Z or ZZ expectation is a real quadratic form. "
        "A real-orthogonal map generates another set of quadratic forms with the same "
        "input, number of readouts, and fitted parameters, allowing the reservoir geometry "
        "to be tested rather than the mere presence of nonlinear features. Random Fourier "
        "features provide a second 15-dimensional nonlinear control. Five independent "
        "maps are averaged for all three families, so validation does not give any one "
        "family an extra candidate."
    ),
    14: "2.3 Validation Gating and Endpoint-Level Reporting",
    15: (
        "Out-of-fold offsets, validation-estimated stacking weights, and endpoint-level "
        "reporting have established precedents [14-16]. Ark-ADMET selected representation "
        "and fusion weights with internal validation across the 22 TDC endpoints [16]. "
        "Robinson et al. reanalyzed a large bioactivity-model comparison in the Journal "
        "of Computer-Aided Molecular Design and showed that evaluation design can change "
        "the resulting model conclusions [31]. "
        "We apply the same five-map averaging and scalar gating rule to QRC and both "
        "classical families. Test labels are not used for map generation, residual fitting, "
        "or weight selection. Repeated fits share a fixed outer test set, so inference is "
        "paired by test scaffold [17]."
    ),
    16: "3 Data and Official Evaluation",
    17: (
        "We obtained the official TDC ADMET archive from Harvard Dataverse file 4426004, "
        "SHA-256 bd0005246cb6f1672333c28ad202112a8bf071ab65d847848715030308faf1f1. "
        "The 22 endpoints contain 65,430 official training/validation records and 16,379 "
        "labelled test records. Thirteen classification endpoints use AUROC or AUPRC; "
        "nine regression endpoints use MAE or Spearman correlation [2]."
    ),
    18: (
        "For each endpoint, the official train_val table was split into 87.5% training "
        "and 12.5% validation with the PyTDC scaffold procedure and seeds 1-5. Official "
        "test membership, labels, and row order remained fixed. All SMILES parsed, and "
        "canonical non-isomeric identities and Bemis-Murcko scaffolds were disjoint "
        "across training, validation, and test [22]. Three scaffold folds inside each "
        "outer training set produced the out-of-fold base offsets. Test results were "
        "generated only after the configuration was frozen."
    ),
    19: (
        "The primary effect was computed from unrounded predictions by scoring each seed "
        "and then averaging the five seeds. For AUROC, AUPRC, and Spearman, the effect is "
        "the new method minus the reference; for MAE, it is the reference minus the new "
        "method; positive values always indicate improvement. We used 1,000 paired "
        "scaffold bootstrap resamples for 95% intervals and 1,999 paired scaffold "
        "permutations for the primary tests, followed by Holm correction across the 22 "
        "endpoints [18-20]. Exploratory TOST analysis used a practical margin of 0.01 "
        "for AUROC, AUPRC, and Spearman and 2% of base MAE for MAE. These margins are "
        "benchmark interpretation thresholds, not clinical limits. TOST consists of two "
        "one-sided tests. We describe practical equivalence only when the 90% confidence "
        "interval lies inside the prespecified margin and the equivalence test is "
        "significant after Holm correction. Results are reported in three states: a "
        "Holm-significant negative difference indicates significant degradation, a "
        "Holm-significant positive difference indicates improvement, and a significant "
        "equivalence test indicates practical statistical equivalence; all other cases "
        "are unresolved. Equivalence does not imply identical mechanisms or identical "
        "per-molecule predictions."
    ),
    20: "4 Methods",
    21: "4.1 Classical Bases and Out-of-Fold Offsets",
    22: (
        "Morgan-ExtraTrees used 512-bit radius-2 Morgan bits, 128 trees, a minimum leaf "
        "size of 2, and square-root feature subsampling. Regression kept the original "
        "label scale; classification returned class-1 probabilities. Each outer split "
        "was trained with its own seed. The final test base was refitted on the complete "
        "outer training set, while out-of-fold predictions were used only for residual "
        "fitting."
    ),
    23: (
        "MapLight-CatBoost used the corrected 2,563-feature representation with 240 "
        "iterations, depth 6, and learning rate 0.06. Classification used Logloss and "
        "regression used MAE. Half-life, VDss, and the two clearance endpoints used the "
        "target log transform of the MapLight protocol; other regressions stayed on their "
        "original scale. CatBoost handled missing values natively. Both bases shared "
        "outer splits and inner scaffold folds [25,26]."
    ),
    24: "4.2 Five-Qubit Reservoir and Matched Classical Features",
    25: (
        "We fit a training-only standardizer and 32-dimensional PCA, normalized each PCA "
        "vector, and amplitude-encoded it into five qubits. The fixed Hamiltonian "
        "contained independently sampled transverse fields, longitudinal fields, and "
        "ring-neighbour ZZ couplings with scale factors 0.4, 0.7, and 0.25, and evolution "
        "time 0.5; Hermiticity was checked explicitly. Five single-qubit Z and ten ZZ "
        "expectations formed 15 features. The circuit and readout used exact state-vector "
        "simulation; the zero vector was mapped to the all-zero computational basis state. "
        "Exact simulation is a deliberate controlled design for isolating the expressive "
        "behavior of the fixed circuit, encoding, and readout. Physical gate errors, "
        "readout errors, crosstalk, and connectivity would otherwise confound the "
        "structural comparison. Finite-shot and depolarizing analyses are sensitivity "
        "checks, not hardware validation; execution on physical devices remains a "
        "separate future study."
    ),
    26: "For input amplitudes a, readout operators D_j, and fixed evolution U,",
    28: (
        "Proposition 1. For any fixed set of 15 diagonal Pauli observables D_j and any "
        "fixed unitary U, the readouts of a normalized 32-dimensional real input a satisfy "
        "q_j(a)=a^T A_j a, where A_j=Re(U^dagger D_j U). Therefore any intercept-free "
        "linear readout is a real quadratic form a^T M a+b: fixed five-qubit QRC with a "
        "linear residual head belongs to a model family constrained by at most 15 real "
        "quadratic forms. The proof follows by expanding (Ua)^dagger D_j (Ua). This does "
        "not make QRC equivalent to a particular real-orthogonal map; it defines the "
        "function class available under the current encoding and readout."
    ),
    29: (
        "QRC, real-orthogonal quadratic, and random Fourier features each used the five "
        "independent maps with seeds 20261101-20261105. The real-orthogonal control "
        "replaced U by a random real orthogonal matrix and retained the same 15 readouts. "
        "The random Fourier control used 15 cosine features. All families shared the same "
        "PCA input, training-side standardization, and linear residual head: logistic "
        "offset regression with L2=1 for classification and ridge with alpha=10 for "
        "regression. Five-map residuals were averaged before validation gating and test "
        "evaluation."
    ),
    30: "4.3 Validation Matching and Endpoint-Level Gating",
    31: (
        "For each endpoint, base, outer seed, and candidate family, let f_0(x) be the base "
        "prediction and Delta_m(x) the five-map mean residual for family m. The gated "
        "prediction is"
    ),
    33: (
        "Validation selected a scalar weight from {0, 0.25, 0.5, 0.75, 1} on the endpoint "
        "metric, with ties preferring the smaller weight. Gating was applied to logits for "
        "classification and directly to predictions for regression. QRC and each "
        "classical family used the same weight grid and the same five-map budget. The "
        "primary comparison was ungated QRC versus the real-orthogonal quadratic map; "
        "Fourier and gated comparisons were secondary."
    ),
    34: (
        "All feature transformations, out-of-fold offsets, residual heads, and gate "
        "weights were fitted within the corresponding training or validation data. Test "
        "sets were used only for final prediction and official metrics after configuration "
        "lock. The main study contains 22 endpoints x 5 outer seeds x 2 bases = 220 base "
        "pipelines; each pipeline contains three out-of-fold fits and one full-training fit."
    ),
    35: "5 Results",
    36: "5.1 Overall Results",
    37: (
        "Table 1 reports five-seed mean official metrics for both bases and ungated "
        "branches. Relative to the fixed real-orthogonal control, QRC was better on 6 and "
        "worse on 16 ExtraTrees endpoints, and better on 3 and worse on 19 CatBoost "
        "endpoints. The corrected CatBoost base itself outperformed ExtraTrees on 21/22 "
        "endpoints; the exception was AUPRC on CYP2C9 substrate. The four endpoints with "
        "the most consistent directional signals in the earlier pilot did not reproduce "
        "consistently: only Caco2 and LD50 were positive against the base on ExtraTrees "
        "and only hERG was marginally positive on CatBoost. Against the orthogonal map, "
        "at most 2/4 were positive on either base, and none survived multiple-testing "
        "correction."
    ),
    38: "Table 1. Five-seed mean official metrics for both bases and ungated branches.",
    40: "Table 2. Endpoint effects of QRC versus the matched real-orthogonal map with Holm correction.",
    42: (
        "Effects in Table 2 are direction-normalized so positive values favour QRC; "
        "brackets show paired 95% scaffold-bootstrap intervals. Holm correction covers "
        "the 22 endpoints within each base. All three Holm-significant results favour the "
        "orthogonal map: AMES on ExtraTrees (AUROC difference -0.0115, Holm p=0.011), "
        "VDss on ExtraTrees (Spearman difference -0.1127, Holm p=0.042), and Solubility "
        "on CatBoost (MAE difference -0.0268, Holm p=0.011). No endpoint is significantly "
        "positive."
    ),
    43: "5.2 Endpoint-Level Gating",
    44: (
        "Validation gating set the QRC weight to zero in 47/110 selections on ExtraTrees "
        "and 55/110 selections on CatBoost. Gated QRC versus the identically gated "
        "orthogonal map was 11 better/11 worse on ExtraTrees and 4 better/17 worse/1 tied "
        "on CatBoost. Neither pair produced a Holm-significant positive endpoint. "
        "Exploratory equivalence covered 8 and 10 endpoints, respectively, but several of "
        "those results reflect both branches being returned to the base model and are not "
        "evidence of a quantum contribution."
    ),
    45: "Table 3. Representative behaviour of validation gating.",
    47: (
        "The small-effect endpoints show that gating limits negative transfer without "
        "creating new extrapolation ability. On ExtraTrees, Half-life improved by 0.0616 "
        "after gating but had Holm p=0.94; PPBR remained -0.1531. On CatBoost, all five "
        "seeds set the QRC weight to zero for Half-life, producing exactly zero "
        "difference; Solubility selected zero in three of five splits and retained a "
        "difference of -0.0010."
    ),
    48: "5.3 Additional Comparisons",
    49: "Table 4. Direction counts and Holm-significant counts across endpoints.",
    51: (
        "QRC versus random Fourier features was also 3 better/19 worse on each base. "
        "Relative to the residual-free base, QRC was 6 better/16 worse on ExtraTrees and "
        "4 better/18 worse on CatBoost, with 2 and 5 Holm-significant negative endpoints, "
        "respectively. Metrics with different units were not averaged across endpoints."
    ),
    52: (
        "Pairing each QRC map index with the corresponding real-orthogonal map produced "
        "visible within-endpoint variation but no stable positive task subset. Full "
        "per-map metrics and predictions are included in the reproduction package."
    ),
    53: (
        "Allowing QRC and the orthogonal branch to enter together, with two scalar "
        "weights selected on validation, produced 12 better/10 worse versus identically "
        "gated orthogonal features on ExtraTrees and 6 better/14 worse/2 tied on CatBoost. "
        "No endpoint was Holm-significantly positive. Against the residual-free base, "
        "the combined model was 10 better/12 worse on ExtraTrees, including one positive "
        "and one negative significant endpoint, and 7 better/14 worse/1 tied on CatBoost "
        "without a significant improvement. Joint gating did not provide transferable "
        "QRC complementarity."
    ),
    54: (
        "The finite-shot panel covered BBB, hERG, Caco2, LD50, PPBR, DILI, CYP2D6 "
        "inhibition, and VDss. Each Pauli readout was independently simulated with 1,024, "
        "4,096, and 16,384 shots, and residual heads were retrained on the sampled "
        "features. QRC versus gated orthogonal features was 5/3 on ExtraTrees at all shot "
        "budgets and 2/6, 1/7, and 1/7 on CatBoost. Increasing shots moved the CatBoost "
        "direction counts toward those observed under exact simulation rather than "
        "revealing a shot-dependent benefit."
    ),
    55: "5.4 Low-Data Scaling",
    56: (
        "To test the regime in which QRC has the clearest theoretical motivation, we used "
        "the same eight representative endpoints at 5%, 10%, 20%, 40%, and 100% of the "
        "outer training data. Each subset contained at least 96 records so that three "
        "inner scaffold folds remained estimable; actual sample counts are recorded for "
        "every result. Subsets were drawn only from outer training data, while validation "
        "and test membership remained fixed."
    ),
    57: (
        "The number of endpoints where ungated QRC beat the orthogonal map was 2/8, 0/8, "
        "1/8, 0/8, and 2/8 on ExtraTrees and 1/8, 0/8, 1/8, 0/8, and 1/8 on CatBoost. "
        "Validation gating reduced degradation and reached 6/8 positive endpoints on "
        "ExtraTrees at 20% training, but the corresponding CatBoost count was 4/8; no "
        "other scale produced a synchronized positive shift across bases. Gated results "
        "therefore indicate risk control, not a low-data quantum advantage. Endpoint "
        "curves are shown in Supplementary Figure S1."
    ),
    58: "5.5 Independent External Endpoints",
    59: (
        "External validation used the ToxTree hERG test collection and the B3DB BBB "
        "classification set [29,30]. hERG used the original binary cutoff PIC50 >= 4.5; "
        "after removing canonical identities present in TDC hERG training or test data, "
        "293 molecules remained. For B3DB, provider BBB+/BBB- labels were used; after "
        "removing canonical TDC BBB overlaps, 2,317 molecules remained. DeepChem ESOL "
        "shared almost all canonical molecules with TDC AqSolDB, leaving only 18 "
        "non-overlapping records, and was therefore excluded."
    ),
    60: (
        "On external hERG, gated QRC minus gated orthogonal AUROC was +0.0112 for "
        "ExtraTrees (95% CI [-0.0029, 0.0246], Holm p=0.200) and +0.0402 for CatBoost "
        "([0.0221, 0.0591], Holm p=0.002). On B3DB BBB, the same effect was -0.0046 for "
        "ExtraTrees ([-0.0076, -0.0019], Holm p=0.002) and -0.0034 for CatBoost "
        "([-0.0065, -0.0006], Holm p=0.016). Joint gating showed the same split: CatBoost "
        "was +0.0298 on hERG and negative with Holm significance on BBB for both bases. "
        "The coexistence of a hERG signal and BBB negative transfer implies source "
        "dependence rather than a general transferable advantage. Full external intervals "
        "are shown in Supplementary Figure S2."
    ),
    61: "5.6 Simulated Decoherence",
    62: (
        "As a controlled noise stress test, we added local single-qubit depolarizing noise "
        "with probabilities 0.001, 0.005, and 0.010 and fixed 4,096 shots on the same "
        "eight endpoints. Symmetric depolarizing multiplies Z expectations by "
        "lambda=1-4p/3 and ZZ expectations by lambda^2; residual heads were retrained on "
        "the noisy features. The model excludes gate-specific error, leakage, crosstalk, "
        "and hardware connectivity and therefore tests sensitivity to controlled readout "
        "attenuation only."
    ),
    63: (
        "Across all three noise levels, QRC versus gated orthogonal features remained "
        "5/3 on ExtraTrees and 1/7 on CatBoost. Against the residual-free base, the counts "
        "were 3/5 for ExtraTrees and 2/6 for CatBoost. Increasing the depolarizing "
        "probability from 0.001 to 0.010 produced no directional reversal. Supplementary "
        "Figure S3 records the sensitivity."
    ),
    64: "5.7 Bounded Reservoir-Family Search",
    65: (
        "To address the possibility that only one reservoir was tested, we prespecified "
        "five fixed parameter families: baseline, weak, strong, short, and long. Each "
        "family contained five independent quantum maps. We also constructed five "
        "real-orthogonal candidate groups of five independent maps each. Every candidate "
        "formed a five-map residual ensemble, and TDC validation selected its gate weight. "
        "QRC and the orthogonal family therefore had equal candidate and map budgets "
        "before testing."
    ),
    66: (
        "Across the eight representative endpoints, the validation-selected QRC was "
        "better/worse on 4/4 endpoints for ExtraTrees and 2/5/1 tied endpoints for "
        "CatBoost relative to the matched orthogonal search. No endpoint was "
        "Holm-significantly positive. The baseline configuration remained the most "
        "frequently selected QRC setting (15/40 on ExtraTrees and 25/40 on CatBoost), "
        "indicating that the broader family did not reveal a new stable signal. Against "
        "the residual-free base, the counts were 4/4 and 2/5/1, respectively; VDss was "
        "significantly worse on both bases. This narrows the possibility that "
        "under-tuning explains the null result."
    ),
    68: (
        "Figure 4. Endpoint-level differences of ungated QRC versus the matched "
        "real-orthogonal map. Classification metrics use absolute units, MAE uses a "
        "relative percentage of the reference MAE, and Spearman uses absolute units. "
        "Intervals are 95% scaffold-cluster bootstrap intervals; red indicates Holm "
        "significance."
    ),
    69: "6 Discussion",
    70: "6.1 What the Constrained Quadratic Map Explains",
    71: (
        "With real amplitude inputs, every Z or ZZ expectation after fixed evolution can "
        "be computed exactly as a real symmetric quadratic form. Training-side "
        "standardization is an affine feature transform, so the linear readout only "
        "combines these quadratic forms and adds a fixed offset. Given the fitted "
        "parameters, the QRC residual can be reproduced by a real quadratic form and a "
        "constant. This structure applies to the normalized 32-dimensional latent input, "
        "not to the raw molecular graph. All five QRC maps had rank 15 and a median "
        "condition number of 1.210; the real-orthogonal maps had condition number 1.000. "
        "The nominal capacities are equal, while the geometries of the quadratic matrices "
        "differ."
    ),
    72: (
        "The real-orthogonal quadratic map had lower point-estimate error on 16/22 "
        "ExtraTrees endpoints and 19/22 CatBoost endpoints. Averaging five random "
        "realizations did not support the hypothesis that the fixed Ising reservoir "
        "geometry is better suited to ADMET than a general quadratic map. This agrees "
        "with a recent cross-target QML benchmark in which localized candidate signals "
        "did not produce a global advantage [27]. The conclusion is limited to the "
        "current five-qubit amplitude encoding, readout, and exact simulation "
        "[12,13,28]."
    ),
    73: "6.2 When Gating Reduces Degradation",
    74: (
        "The benefit of gating mainly comes from stopping harmful residuals, not from "
        "discovering transferable quantum corrections. CatBoost selected zero QRC weight "
        "in half of all endpoint-split decisions, and 17 endpoints remained worse than "
        "the identically gated orthogonal branch. Several endpoints had near-zero "
        "differences within the exploratory equivalence margins, but this is consistent "
        "with the quantum branch being suppressed and cannot replace a test of positive "
        "superiority. Gating is a risk-control rule and not a molecule-level confidence "
        "estimate."
    ),
    75: "6.3 What the Strong Base and External Cohorts Reveal",
    76: (
        "The strong-base experiment is the main difference from the preliminary pilot. "
        "MapLight-CatBoost outperformed Morgan-ExtraTrees on 21/22 endpoints, while QRC "
        "performed worse relative to control on the stronger base. Joint gating did not "
        "produce a stable increment across endpoints, and finite-shot, low-data, and "
        "simulated-noise analyses did not reverse this result. The positive external "
        "hERG signal suggests that a source-specific candidate may remain. Its pIC50 rank "
        "transfer and independent continuous regression point in the same weak direction, "
        "but the rank transfer did not survive 12-comparison Holm correction and the "
        "regression confidence intervals crossed zero without any corrected significant "
        "contrast. BBB logBB transfer was near zero, and significant B3DB BBB "
        "classification degradation rules out a cross-source interpretation. Future "
        "quantum encodings should be tested directly on a strong base with matched input, "
        "capacity, and candidate budgets. For computer-aided molecular design practice, "
        "fixed amplitude-encoded QRC should not yet be treated as a general ADMET "
        "descriptor; new quantum encodings should also be evaluated on genuinely "
        "independent regression cohorts and source cohorts."
    ),
    77: "6.4 Chemical-Space and Source Dependence",
    78: (
        "We added a descriptive chemical-space audit to determine whether the external "
        "cohort differences could be attributed to source proximity. Both cohorts were "
        "already free of exact canonical identities from their corresponding TDC archive. "
        "For hERG, 23 of 293 molecules (7.8%) retained a Bemis-Murcko scaffold present in "
        "TDC train/validation data; the median nearest Morgan Tanimoto similarity "
        "(radius 2, 2048 bits) to TDC train/validation molecules was 0.234 and the 90th "
        "percentile was 0.423. For B3DB BBB, 562 of 2,317 molecules (24.3%) shared a TDC "
        "train/validation scaffold, with a median nearest similarity of 0.346 and a 90th "
        "percentile of 0.722. B3DB contained 48.9% positives versus 76.4% in the full TDC "
        "BBB archive, whereas hERG contained 76.4% positives versus 68.9% in TDC. The two "
        "cohorts therefore differ from their TDC sources in both chemical proximity and "
        "label composition."
    ),
    79: (
        "Re-scoring the existing held-out predictions by these chemical strata did not "
        "support a simple scaffold-overlap explanation for the hERG signal. For CatBoost, "
        "the hERG gated-QRC minus gated-orthogonal effect was -0.0026 AUROC among the 23 "
        "molecules with a shared train/validation scaffold and +0.0452 among the 270 "
        "molecules with a novel scaffold. The effect was +0.0196 in the highest nearest-"
        "similarity quartile and +0.0494 in the remaining three quartiles. In contrast, "
        "the BBB effect was negative across shared-scaffold, novel-scaffold, and "
        "similarity strata. Full source audits and hERG strata are reported in "
        "Supplementary Tables S5 and S6. These descriptive strata locate where an effect appears; "
        "they do not control source, assay batch, or label definition and cannot establish "
        "a causal chemical mechanism."
    ),
    80: (
        "A low-dimensional fixed quantum reservoir has its clearest theoretical rationale "
        "for tasks with limited training data, strong local nonlinear interactions, and "
        "classical kernels that do not adequately cover the chemical distribution. The "
        "global TDC ADMET endpoints generally contain larger and more heterogeneous label "
        "collections, the regime in which the present design showed no stable gain. The "
        "low-data curves likewise did not show a synchronized positive shift across bases. "
        "This observation does not rule out angle encodings, task-conditioned amplitude "
        "encodings, trainable circuits, larger reservoirs, or different readout strategies; "
        "each must be reassessed against strong bases and independent source cohorts."
    ),
    81: (
        "The hERG point improvement is a candidate signal, not evidence that the quantum "
        "features learned a mechanism of cardiac toxicity. The significant B3DB negative "
        "transfer is not evidence that quantum methods are universally ineffective for "
        "ADMET. The QML-ADMET studies reviewed here use different fixed reservoirs, "
        "Hamiltonian-derived features, quantum-inspired preprocessing, circuit search, or "
        "jointly trained residuals; their task counts, controls, and external validation "
        "settings do not support a like-for-like equivalence claim. Supplementary Table "
        "S4 summarizes the differences. The contribution is a reusable minimum evaluation "
        "workflow: prespecify the primary comparator, match candidate and map budgets, "
        "infer with scaffold clusters, correct across endpoints, interpret equivalence "
        "separately from superiority, and report both cross-base and cross-source results."
    ),
    82: "7 Limitations",
    83: (
        "The fixed official test set supports reproducible comparisons but may have been "
        "reused by earlier public leaderboards and is not a prospective cohort. Similar "
        "molecules may remain under different Murcko scaffolds, so extrapolation across "
        "laboratories, time, and chemical series requires separate evaluation. The "
        "exact state-vector calculation is a controlled choice for isolating circuit "
        "expressivity and does not replace evaluation of physical gate error, readout "
        "crosstalk, connectivity, or scheduling. The equivalence margins are exploratory "
        "and are not clinical or regulatory thresholds [3-5,21]."
    ),
    84: (
        "We evaluate independent per-molecule inputs and one fixed five-qubit evolution. "
        "Finite-shot analysis sampled each Pauli expectation independently; noise analysis "
        "used a simplified local depolarizing model and did not simulate gate error, "
        "leakage, readout crosstalk, or measurement scheduling. We did not test trainable "
        "circuits, task-conditioned amplitude encoding, or other PCA dimensions. The "
        "low-data analysis covers eight representative endpoints, and the 96-record "
        "minimum changes the effective fraction for the smallest endpoints. The primary "
        "external analysis contains two classification endpoints; hERG uses the "
        "source-defined binary cutoff but still differs in assay source and label "
        "generation. The supplementary continuous-label analysis ranks binary-model "
        "outputs and is not an independently trained regression evaluation. The separate "
        "pIC50 regression uses 214 test molecules in 155 scaffolds under a fixed protocol; "
        "it is scaffold-disjoint but statistically underpowered. B3DB logBB "
        "was available for only 613/2,317 non-overlapping molecules and was strongly "
        "class-enriched, so it does not represent the full BBB chemical space. The "
        "chemical-space figure uses a linear fingerprint projection and three basic "
        "descriptors, not a complete applicability-domain model, and equivalence counts "
        "depend on the prespecified margins. Random-map "
        "sensitivity covers five "
        "realizations per family, and hardware cost, decoherence, and connectivity were "
        "not evaluated on physical devices. The present comparison therefore applies only "
        "to five-qubit amplitude encoding, a fixed Hamiltonian reservoir, 15 Pauli "
        "readouts, a linear residual head, and exact simulation. It does not establish the "
        "behavior of other quantum representations or physical hardware. Repeated use of "
        "the public TDC test set may also reduce generalization to unseen chemical series."
    ),
    85: "8 Conclusion",
    86: (
        "Across 22 official TDC ADMET endpoints, fixed five-qubit reservoir residuals "
        "showed no stable increment over equal-capacity real-orthogonal quadratic maps. "
        "This result held on both Morgan-ExtraTrees and the stronger "
        "MapLight-CatBoost base. Validation gating pushed some harmful residuals back to "
        "the classical base but did not produce a stable advantage over the gated "
        "classical control. Joint gating, low-data scaling, finite shots, and simulated "
        "decoherence did not reverse this conclusion. External hERG provided a "
        "CatBoost-specific candidate signal, whereas B3DB BBB showed significant negative "
        "transfer. Continuous-label rank transfer and independent pIC50 regression both "
        "showed only uncorrected weak CatBoost/hERG directions, with no Holm-significant "
        "comparison and no corresponding BBB signal. Chemical-space and physicochemical "
        "strata support a source-dependent local signal rather than an identifiable general "
        "chemical rule. The main contribution is a reproducible QML evaluation workflow. "
        "The result is bounded by the tested "
        "five-qubit amplitude-encoded, fixed-Hamiltonian reservoir with 15 Pauli readouts, "
        "a linear residual head, and exact simulation; other encodings, trainable circuits, "
        "larger reservoirs, and physical hardware require independent evaluation."
    ),
    87: "Data and Code Availability",
    88: (
        "The official TDC archive is available as Harvard Dataverse file 4426004 with "
        "SHA-256 bd0005246cb6f1672333c28ad202112a8bf071ab65d847848715030308faf1f1. "
        "External hERG data are from Zenodo 5807719 and BBB data from B3DB; source, label "
        "rules, deduplication, and overlap audits are included in the reproduction package. "
        "The package also contains processing scripts, five scaffold splits, five random "
        "maps per family, base configurations, all split-level predictions, joint gating, "
        "finite-shot, low-data, external-endpoint decomposition and calibration, "
        "continuous-label transfer, independent pIC50 regression, simulated-noise, "
        "bounded-family, TOST-sensitivity, and chemical-space audit results, statistical "
        "scripts, figure-generation code, and environment locks. The versioned code and "
        "result index are available at "
        "https://github.com/575914291-source/qrc-admet-matched-evaluation; the submission "
        "archive contains complete split-level predictions and supplementary materials. "
        "The MapLight reference and MIT license are retained. Official test labels were "
        "used only for scoring after configuration lock and were not used for training, "
        "map generation, joint weights, or gating."
    ),
    89: "References",
}

INSERTED_TEXT = {
    9: (
        "Figure 1. Matched evaluation design. The two data sources share the two "
        "classical bases, the 32-dimensional PCA amplitude input, five-map residual "
        "ensembles, and the same gating budget. The primary control is the fixed "
        "five-qubit QRC versus a parameter-matched real-orthogonal quadratic map."
    ),
    22: (
        "Supplementary Table S1 reports endpoint sample sizes, official metrics, and "
        "label summaries. Supplementary Table S2 reports the hierarchy of primary, "
        "secondary, sensitivity, external, and exploratory analyses. Supplementary "
        "Table S9 reports TOST counts under tight, primary, and wide margins. Figure 2 "
        "shows the chemical-space and physicochemical context of the TDC, hERG, and "
        "B3DB cohorts."
    ),
    24: (
        "Figure 2. Chemical space and applicability-domain context. (A) Morgan radius-2 "
        "1024-bit fingerprints projected by 20-component truncated SVD, "
        "standardization, and two-dimensional PCA. TDC and B3DB were randomly sampled "
        "to 3,000 and 500 unique molecules, respectively; all 293 hERG molecules were "
        "used. (B-D) Molecular weight, cLogP, and TPSA distributions for all unique TDC, "
        "hERG, and B3DB molecules. Box plots omit outlier markers for readability."
    ),
    31: (
        "Five qubits support 32 real amplitudes, so the 32-dimensional PCA is the "
        "smallest complete amplitude input without truncation or padding at this scale. "
        "The 15 readouts comprise five single-qubit Z expectations and all ten pair-wise "
        "ZZ expectations. This is not a hardware-capacity claim; it is a closed design "
        "that permits exact state-vector evaluation, an equal-dimensional classical "
        "control, and five complete map realizations. For normalized PCA vector v, the "
        "amplitudes are a_j = v_j / ||v||. The Hamiltonian H and evolution U = "
        "exp(-iHt) are fixed and not trained on test labels. PCA dimension and readout "
        "set were held fixed to avoid adding another capacity search to the primary "
        "benchmark."
    ),
    67: (
        "Figure 3 separates QRC gain from orthogonal-branch degradation using the existing "
        "predictions. For CatBoost/hERG, gated QRC minus the residual-free base was "
        "+0.0285 AUROC (95% CI [0.0137, 0.0437]), whereas gated orthogonal minus the "
        "base was -0.0117 ([-0.0216, -0.0011]); the +0.0402 primary difference therefore "
        "contains both a QRC gain and an orthogonal decrement. The hERG QRC-minus-"
        "orthogonal AUPRC difference was +0.0304, with Brier and log-loss improvements "
        "of +0.0038 and +0.0363. Both hERG branches remained poorly calibrated, with "
        "calibration slopes of approximately 0.15-0.26. In B3DB, QRC minus orthogonal "
        "AUPRC was -0.0047 for ExtraTrees and -0.0061 for CatBoost, and Brier and "
        "log-loss differences did not favour QRC. Full decomposition and calibration "
        "values are reported in Supplementary Tables S7 and S8. The continuous-label "
        "rank transfer "
        "showed an unadjusted CatBoost/hERG pIC50 Spearman difference of +0.043, which "
        "did not survive Holm correction across 12 comparisons and did not replicate "
        "for BBB logBB. It is not an independently trained regression evaluation, and "
        "the B3DB continuous subset is 86.8% positive."
    ),
    69: (
        "Figure 3. External classification decomposition and calibration. (A-B) AUROC "
        "differences for gated QRC versus base, gated orthogonal versus base, and gated "
        "QRC versus gated orthogonal; positive values favour the first method. (C-D) "
        "Five-seed mean CatBoost calibration curves using prediction quintiles; the "
        "dashed diagonal is perfect calibration. Decomposition explains the primary "
        "comparison and does not replace the prespecified external AUROC test."
    ),
    78: "5.8 Independent Continuous pIC50 Regression",
    79: (
        "To avoid treating rank preservation from a binary classifier as continuous-value "
        "prediction, we added a fixed ToxTree hERG pIC50 regression. After removing TDC "
        "overlap, the source Dev-set was split by Bemis-Murcko scaffold into 6,895 "
        "training and 985 validation molecules. The source Test-set was filtered to "
        "remove TDC overlaps and scaffolds shared with the external Dev-set, retaining "
        "214 test molecules in 155 scaffolds. QRC, orthogonal quadratic, random Fourier, "
        "and linear residual heads followed the TDC protocol. External test labels were "
        "not used to select map seeds, PCA dimension, regularization, or hyperparameters."
    ),
    80: (
        "Five model seeds did not show a confirmed QRC increment. QRC minus orthogonal "
        "Spearman was +0.0229 on ExtraTrees (95% CI [-0.0121, 0.0608]) and +0.0093 on "
        "CatBoost ([-0.0168, 0.0325]); QRC minus the CatBoost base was +0.0292 "
        "([-0.0034, 0.0604]). MAE differences were close to zero. No comparison was "
        "significant after Holm correction across all 12 metric, base, and contrast "
        "tests. The cohort is independent of TDC labels but contains only 214 molecules "
        "and cannot provide a high-power validation on its own. Full results are shown "
        "in Supplementary Figure S4 and Supplementary Table S10."
    ),
    94: (
        "For computational context, exact state-vector simulation of five qubits is not "
        "a quantum-speedup demonstration and provides no hardware runtime estimate. The "
        "scale was chosen to construct an exact, equal-readout quadratic control and to "
        "avoid confounding circuit expressivity with physical noise. The results do not "
        "support a quantum runtime advantage and cannot be used to infer the feasibility "
        "of larger reservoirs, fault-tolerant quantum computing, or a specific hardware "
        "topology; these are separate experimental questions."
    ),
}


def _final_paragraph_index(original_index: int) -> int:
    if original_index < 8:
        return original_index
    if original_index < 20:
        return original_index + 2
    if original_index < 26:
        return original_index + 5
    if original_index < 61:
        return original_index + 6
    if original_index < 69:
        return original_index + 9
    if original_index < 82:
        return original_index + 12
    return original_index + 13


HEADERS = {
    0: ["Endpoint", "Metric", "ET", "QRC-ET", "Orth-ET", "CB", "QRC-CB", "Orth-CB"],
    1: [
        "Endpoint",
        "Metric",
        "ET effect [95% CI]",
        "ET Holm p",
        "CB effect [95% CI]",
        "CB Holm p",
    ],
    2: [
        "Base",
        "Endpoint",
        "Metric",
        "QRC gate weights",
        "Gated QRC-Orth [95% CI]",
        "Holm p",
    ],
    3: ["Contrast", "QRC better", "QRC worse", "Holm positive", "Holm negative"],
}


def replace_paragraph(paragraph, text: str) -> None:
    style = paragraph.style.name
    paragraph.text = text
    size = 10.6
    if style == "Title":
        size = 18.0
    elif style == "Subtitle":
        size = 12.0
    elif style == "Heading 1":
        size = 14.0
    elif style == "Heading 2":
        size = 12.0
    for run in paragraph.runs:
        run.font.name = "Times New Roman"
        run.font.size = Pt(size)
        run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Times New Roman")


def main() -> int:
    shutil.copy2(SOURCE, OUTPUT)
    document = Document(OUTPUT)
    paragraphs = document.paragraphs
    translated = {
        _final_paragraph_index(original_index): text
        for original_index, text in TEXT.items()
    }
    translated.update(INSERTED_TEXT)
    for index, text in translated.items():
        replace_paragraph(paragraphs[index], text)
    for table_index, header in enumerate(HEADERS.values()):
        table = document.tables[table_index]
        for column, text in enumerate(header):
            cell = table.rows[0].cells[column]
            cell.text = ""
            run = cell.paragraphs[0].add_run(text)
            run.font.name = "Times New Roman"
            run.font.size = Pt(7.5)
            run.bold = True
    alt_texts = (
        "Study-design schematic from molecular data and two classical bases through "
        "matched quantum, orthogonal, and Fourier branches to scaffold-level evidence.",
        "Chemical-space projection and molecular-weight, cLogP, and TPSA distributions "
        "for TDC, external hERG, and B3DB molecules.",
        "External hERG and B3DB effect decomposition and CatBoost calibration curves.",
        "Endpoint-level paired differences of ungated QRC versus matched orthogonal "
        "quadratic features across all 22 TDC ADMET endpoints.",
    )
    for shape, alt_text in zip(document.inline_shapes, alt_texts, strict=True):
        shape._inline.docPr.set("descr", alt_text)
        shape._inline.docPr.set("title", alt_text)
    for paragraph in paragraphs[103:134]:
        paragraph.text = (
            paragraph.text.replace("arXiv 预印本", "arXiv preprint")
            .replace("bioRxiv 预印本", "bioRxiv preprint")
            .replace("预印本", "preprint")
        )
        for run in paragraph.runs:
            run.font.name = "Times New Roman"
            run.font.size = Pt(9.5)
    footer = document.sections[0].footer.paragraphs[0]
    for run in footer.runs:
        if "第" in run.text:
            run.text = "Page "
        elif "页" in run.text:
            run.text = ""
        run.font.name = "Times New Roman"
    document.save(OUTPUT)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

