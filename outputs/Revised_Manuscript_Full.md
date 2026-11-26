---
title: "Matched Evaluation of Fixed Quantum Reservoir Residuals on TDC ADMET with Random Realizations and Strong Baselines"
subtitle: "A Calibrated Reproducible Benchmark of Fixed Quantum Reservoir Features on TDC ADMET"
lang: en
---

# Abstract

Reported QRC gains are difficult to compare because studies often differ
in classical controls, random realizations, base-model strength, and
external validation. We evaluated this question under a common,
calibrated protocol across all 22 Therapeutics Data Commons (TDC) ADMET
endpoints. We compared exact simulations of five-qubit amplitude-encoded
reservoirs with real-orthogonal quadratic maps and random Fourier
features, using Morgan-ExtraTrees and MapLight-CatBoost. Five scaffold
splits and five averaged maps per family quantified randomness. Ungated
QRC was better on 6 and worse on 16 ExtraTrees endpoints, and better on
3 and worse on 19 CatBoost endpoints. After Holm correction, no endpoint
was significantly better and three were significantly worse. Validation
gating, joint QRC-orthogonal residuals, low-data scaling, finite shots,
simulated noise, and a bounded reservoir-family search did not produce a
cross-base advantage. External validation was source-dependent: CatBoost
improved by 0.040 AUROC on 293 non-overlapping hERG molecules, whereas
both bases degraded on 2,317 B3DB BBB molecules. The hERG difference
combined a QRC gain with an orthogonal-branch decrement relative to the
base. Continuous-label ranking and an independent pIC50 regression did
not survive joint multiplicity correction. Known-signal calibration
recovered QRC and classical targets, with null false-positive rates of
2.0-4.7%. Circuit-level simulation preserved rank under error but
attenuated amplitudes. Chemical-space analyses showed no simple source
effect. The main contribution is a calibrated evaluation workflow; its
scope is limited to five-qubit amplitude encoding, 15 Pauli readouts, a
linear residual head, and exact state-vector simulation, not to other
encodings, trainable circuits, larger reservoirs, or physical hardware.

Keywords: ADMET; TDC; quantum reservoir; matched classical controls;
random realizations; validation gating

# 1 Introduction

ADMET prediction includes binary, continuous, and ranking endpoints that
differ in sample size, measurement resolution, and chemical-space
coverage. TDC supplies fixed test sets, endpoint-specific metrics, and
scaffold split interfaces, allowing endpoint-level verification \[1,2\].
Molecular representation, model family, and evaluation split can each
change model rankings \[3-6\]. A comparison with one weak base model
cannot separate the contribution of quantum features from nonlinear
capacity, training choices, or dataset-specific effects.

The study addresses one question: with molecular input, 15 readouts, and
the linear residual head held constant, does a fixed five-qubit
reservoir add predictive value beyond real-orthogonal quadratic maps and
random Fourier features across 22 TDC endpoints, two classical bases,
and independent external sources? Figure 1 summarizes the design. The
study makes three contributions. First, it treats the current QRC
residual as a constrained real quadratic feature family and constructs a
control with the same input, readout dimension, fitted-parameter budget,
and map budget. Second, it evaluates the family across all 22 endpoints
with validation gating and multiple-testing correction. Third, it uses
low-data, finite-shot, simulated-noise, bounded-family, two-source
external, continuous-label, independent pIC50 regression, and
chemical-space analyses to define the limits of the conclusion.

<img src="outputs\Revised_Manuscript_Media\media\image1.png" title="Study-design schematic from molecular data and two classical bases through matched quantum, orthogonal, and Fourier branches to scaffold-level evidence; the lower band shows that 15 Pauli readouts form constrained real quadratic features." style="width:6.6in;height:4.34375in" alt="Study-design schematic from molecular data and two classical bases through matched quantum, orthogonal, and Fourier branches to scaffold-level evidence; the lower band shows that 15 Pauli readouts form constrained real quadratic features." />

Figure 1. Matched evaluation design. The two data sources share the two
classical bases, the 32-dimensional PCA amplitude input, five-map
residual ensembles, and the same gating budget. The primary control is
the fixed five-qubit QRC versus a parameter-matched real-orthogonal
quadratic map. The lower band states that all 15 Pauli readouts form
constrained real quadratic features q\_j(a)=a^T A\_j a.

# 2 Related Work

## 2.1 ADMET Benchmarks and Classical Representations

TDC endpoint definitions, fixed test sets, and scoring interfaces
support verification, but a public official test set is not a
prospective validation. Scaffold splits are more demanding than random
splits, yet near analogues can remain and cannot replace a temporal
holdout \[1-5\]. We use a corrected MapLight feature set with CatBoost
as a strong classical reference \[6,7,25,26\]: 1,024 Morgan counts,
1,024 Avalon counts, 315 ErG dimensions, and 200 RDKit descriptors. The
upstream count conversion used int8 and could overflow; we use int32
when rebuilding the feature cache.

## 2.2 Quantum Molecular Features and Structural Controls

Beaulieu et al. reported more stable fixed-reservoir performance in
smaller molecular-activity datasets and analyzed embedding separation
\[8\]. Benson et al. concatenated Hamiltonian-derived readouts with
classical descriptors before CatBoost and reported improvement on 8/10
TDC tasks; this hybrid feature design does not isolate a
capacity-matched residual \[9\]. Mansour et al. found that compact
quantum-inspired Hamiltonian features performed comparably to a
second-degree polynomial interaction control on AqSolDB, making an
explicit quadratic comparator central to the present design \[10\].
QCS-ADME addressed quantum-circuit search and simulator-to-hardware
variation rather than one fixed circuit family \[11\]. Jia et al.
compared five-qubit amplitude-encoded residuals with real-orthogonal
controls, but jointly trained the encoder and residual head and
evaluated receptor-potency tasks rather than ADMET \[12\]. A 48-task
potency benchmark found no global advantage for quantum classifiers
\[27\], and Floquet-QRC tested sequential graph events and driven
reservoirs under a different input regime \[28\]. These studies differ
in task, control, and training protocol; Table 1 accordingly compares
design choices rather than model scores.

Table 1. Representative QML molecular-property studies and their
relation to the present evaluation. Tasks, encodings, and training
protocols are not numerically equivalent across studies.

|               |                          |                                  |                                                         |
|---------------|--------------------------|----------------------------------|---------------------------------------------------------|
| **Study**     | **Molecular setting**    | **Quantum/control focus**        | **Relation to this benchmark**                          |
| Beaulieu 2025 | Activity; small N        | Fixed QRC                        | Adds 22 endpoints, two bases, and external tests        |
| Benson 2026   | 10 TDC tasks             | Hamiltonian + CatBoost           | Different hybrid model; matched residual test           |
| Mansour 2026  | AqSolDB                  | MI Hamiltonian + CatBoost        | Polynomial ablation motivates matched quadratic control |
| Zheng 2026    | 8 class + 4 regression   | Circuit search                   | Search versus fixed matched comparison                  |
| Jia 2026      | 3 receptor-potency tasks | Joint encoder + quantum residual | Orthogonal control showed similar performance           |
| Garg 2026     | 10 targets; 48 tasks     | QSVM and VQC                     | No global advantage; local sparse signals               |
| Wang 2026     | Graph prefixes; gap      | Floquet QRC                      | Sequence input and hardware; not ADMET-wide             |

The comparison asks whether reservoir geometry contributes information
beyond the nonlinear interactions available to a classical map. For
fixed real amplitudes, every Z or ZZ expectation is a real quadratic
form. A real-orthogonal transformation produces another set of quadratic
readouts with the same input, readout count, and fitted parameters.
Differences between these branches reflect matrix geometry rather than
feature dimensionality. Random Fourier features provide a second
15-dimensional nonlinear control. All three families use five
independent maps, and no family receives extra validation candidates.

## 2.3 Validation Gating and Endpoint-Level Reporting

Out-of-fold offsets, validation-estimated stacking weights, and
endpoint-level reporting provide established precedents \[14-16\].
Ark-ADMET selected representation and fusion weights with internal
validation across 22 TDC endpoints \[16\]. Robinson et al. reanalyzed a
large bioactivity comparison in the Journal of Computer-Aided Molecular
Design and showed that evaluation design can change the conclusions
\[31\]. We apply the same five-map averaging and scalar gating rule to
QRC and both classical families. Test labels are not used for map
generation, residual fitting, or weight selection. Because repeated fits
share a fixed outer test set, bootstrap and permutation inference is
performed with the test scaffold as the sampling unit \[17-20\].

# 3 Data, Splits, and Statistical Evaluation

We obtained the official TDC ADMET archive from Harvard Dataverse file
4426004, SHA-256
bd0005246cb6f1672333c28ad202112a8bf071ab65d847848715030308faf1f1. The 22
endpoints contain 65,430 official training/validation records and 16,379
labeled test records. Thirteen classification endpoints use AUROC or
AUPRC; nine regression endpoints use MAE or Spearman correlation \[2\].

For each endpoint, the official train\_val table was split into 87.5%
training and 12.5% validation with the PyTDC scaffold procedure and
seeds 1-5. Official test membership, labels, and row order remained
fixed. Every SMILES string parsed successfully; canonical non-isomeric
identities and Bemis-Murcko scaffolds were disjoint across training,
validation, and test \[22\]. Three scaffold folds inside each outer
training set produced the out-of-fold base offsets. Test results were
generated only after the configuration was frozen.

The primary effect was computed from unrounded predictions: each seed
was scored, and the scores were averaged over the five seeds. For AUROC,
AUPRC, and Spearman, the effect is the new method minus the reference;
for MAE, it is the reference minus the new method. Positive values
indicate improvement. We used 1,000 paired scaffold bootstrap resamples
for 95% intervals and 1,999 paired scaffold permutations for the primary
tests, with Holm correction across the 22 endpoints \[18-20\].

Exploratory TOST used margins of 0.01 for AUROC, AUPRC, and Spearman and
2% of base MAE for MAE. These thresholds define practical benchmark
equivalence, not clinical limits. Practical equivalence was reported
only when the 90% confidence interval lay inside the prespecified margin
and the equivalence test remained significant after Holm correction.
Results are classified as significant degradation, significant
improvement, practical equivalence, or unresolved. Equivalence does not
imply identical mechanisms or identical per-molecule predictions.

Supplementary Table S1 reports endpoint sample sizes, official metrics,
and label summaries. Supplementary Table S2 reports the hierarchy of
primary, secondary, sensitivity, external, and exploratory analyses.
Supplementary Table S9 reports TOST counts under tight, primary, and
wide margins. Figure 2 shows the chemical-space and physicochemical
context of the TDC, hERG, and B3DB cohorts.

<img src="outputs\Revised_Manuscript_Media\media\image2.png" title="Chemical-space projection and molecular-weight, cLogP, and TPSA distributions for TDC, external hERG, and B3DB molecules." style="width:6.3in;height:5.51389in" alt="Chemical-space projection and molecular-weight, cLogP, and TPSA distributions for TDC, external hERG, and B3DB molecules." />

Figure 2. Chemical space and applicability-domain context. (A) Morgan
radius-2 1024-bit fingerprints projected by 20-component truncated SVD,
standardization, and two-dimensional PCA. TDC and B3DB were randomly
sampled to 3,000 and 500 unique molecules, respectively; all 293 hERG
molecules were used. (B-D) Molecular weight, cLogP, and TPSA
distributions for all unique TDC, hERG, and B3DB molecules. Box plots
omit outlier markers for readability.

# 4 Methods

## 4.1 Classical Bases and Out-of-Fold Offsets

Morgan-ExtraTrees used 512-bit radius-2 Morgan bits, 128 trees, a
minimum leaf size of 2, and square-root feature subsampling. Regression
kept the original label scale; classification returned class-1
probabilities. Each outer split was trained with its own seed. The final
test base was refitted on the complete outer training set, while
out-of-fold predictions were used only for residual fitting.

MapLight-CatBoost used the corrected 2,563-feature representation with
240 iterations, depth 6, and learning rate 0.06. Classification used
Logloss and regression used MAE. Half-life, VDss, and the two clearance
endpoints used the target log transform of the MapLight protocol; other
regressions stayed on their original scale. CatBoost handled missing
values natively. Both bases shared outer splits and inner scaffold folds
\[25,26\].

## 4.2 Five-Qubit Reservoir and Matched Classical Features

We fit a training-only standardizer and 32-dimensional PCA, normalized
each PCA vector, and amplitude-encoded it into five qubits. The fixed
Hamiltonian contained independently sampled transverse fields,
longitudinal fields, and ring-neighbor ZZ couplings with scale factors
0.4, 0.7, and 0.25, and evolution time 0.5; Hermiticity was checked
explicitly. Five single-qubit Z and ten ZZ expectations formed 15
features. The circuit and readout used exact state-vector simulation;
the zero vector was mapped to the all-zero computational basis state.
Exact simulation is a deliberate controlled design for isolating the
expressive behavior of the fixed circuit, encoding, and readout.
Physical gate errors, readout errors, crosstalk, and connectivity would
otherwise confound the structural comparison. Finite-shot and
depolarizing analyses are sensitivity checks, not hardware validation;
execution on physical devices remains a separate future study.

A five-qubit register provides 32 amplitudes, so a 32-dimensional PCA
vector can be encoded without truncation or zero padding. The 15
readouts are five Z and ten ZZ expectations. The scale is a controlled
identifiability choice, not a hardware-capacity claim: it permits exact
state-vector evaluation, an equal-dimensional classical control, and
five complete map realizations. For a normalized PCA vector v, the
amplitudes are a\_j = v\_j / \|\|v\|\|. The Hamiltonian H and evolution
U = exp(-iHt) were fixed and were not trained on test labels. PCA
dimension and readout set were held fixed so that the primary benchmark
did not add another capacity search.

For input amplitudes a, readout operators D\_j, and fixed evolution U,

$$q_{j}(a) = {(Ua)}^{\dagger}D_{j}(Ua) = a^{T}Re(U^{\dagger}D_{j}U)a.$$

Proposition 1. For any fixed set of 15 diagonal Pauli observables D\_j
and any fixed unitary U, the readouts of a normalized 32-dimensional
real input a satisfy q\_j(a)=a^T A\_j a, where A\_j=Re(U^dagger D\_j U).
An intercept can be absorbed into b, so any linear readout of these
features has the form a^T M a+b. Thus fixed five-qubit QRC with a linear
residual head belongs to a model family constrained by at most 15 real
quadratic forms. The proof follows by expanding (Ua)^dagger D\_j(Ua).
This class description does not equate QRC with a particular
real-orthogonal map; it identifies the function family and motivates the
matched control.

QRC, real-orthogonal quadratic, and random Fourier features each used
the five independent maps with seeds 20261101-20261105. The
real-orthogonal control replaced U by a random real orthogonal matrix
and retained the same 15 readouts. The random Fourier control used 15
cosine features. All families shared the same PCA input, training-side
standardization, and linear residual head: logistic offset regression
with L2=1 for classification and ridge with alpha=10 for regression.
Five-map residuals were averaged before validation gating and test
evaluation.

## 4.3 Validation Matching and Endpoint-Level Gating

For each endpoint, base, outer seed, and candidate family, let f\_0(x)
be the base prediction and Delta\_m(x) the five-map mean residual for
family m. The gated prediction is

$$f_{m}^{\text{gate}}(x) = f_{0}(x) + \alpha_{m}\Delta_{m}(x),\,\alpha ₘ \in \{ 0,0.25,0.5,0.75,1\}.$$

Validation selected a scalar weight from {0, 0.25, 0.5, 0.75, 1} on the
endpoint metric, with ties preferring the smaller weight. Gating was
applied to logits for classification and directly to predictions for
regression. QRC and each classical family used the same weight grid and
the same five-map budget. The primary comparison was ungated QRC versus
the real-orthogonal quadratic map; Fourier and gated comparisons were
secondary.

All feature transformations, out-of-fold offsets, residual heads, and
gate weights were fitted within the corresponding training or validation
data. Test sets were used only for final prediction and official metrics
after configuration lock. The main study contains 22 endpoints x 5 outer
seeds x 2 bases = 220 base pipelines; each pipeline contains three
out-of-fold fits and one full-training fit.

## 4.4 Benchmark Calibration and Attribution

To test sensitivity and specificity separately from ADMET performance,
we performed a feature-stage calibration on hERG, B3DB BBB, and AqSolDB
solubility. Real molecular inputs were projected to 32 dimensions and
passed through the same five QRC, orthogonal, and Fourier map draws. We
generated QRC-derived, orthogonal-derived, and independent null targets;
trained the same 15-dimensional heads on the fixed training splits;
averaged the five map predictions; and evaluated held-out recovery. For
each base and scenario, this produced 150 synthetic datasets (3
endpoints x 5 split seeds x 10 replicates). The calibration isolates the
feature comparison and intentionally omits the classical base offset.

We further decomposed each QRC-versus-base endpoint effect into a
matched-classical nonlinearity term and a QRC-specific term; compared
validation-selected QRC and orthogonal maps to quantify selection
optimism; computed effective rank, condition number, and centered kernel
alignment for all 220 task-base-split combinations; and stratified
external QRC-specific AUROC by nearest-TDC similarity quartiles.
Supplementary Tables S12-S16 and Figures S6-S10 report these analyses.

The calibration targets test the sensitivity and specificity of the
evaluation. They are not biological endpoints and are not used to infer
new ADMET mechanisms.

# 5 Results

## 5.1 Overall Results

Table 2 reports five-seed mean official metrics for both bases and
ungated branches. Relative to the fixed real-orthogonal control, point
estimates favored QRC on 6 and the matched control on 16 ExtraTrees
endpoints; on CatBoost, they favored QRC on 3 and the matched control on
19 endpoints. The corrected MapLight-CatBoost base outperformed
ExtraTrees on 21/22 endpoints; the exception was AUPRC on CYP2C9
substrate. An earlier exploratory pilot selected BBB, hERG, Caco2, and
LD50 as candidate endpoints. Their directions did not reproduce
consistently: only Caco2 and LD50 were positive against the base on
ExtraTrees and only hERG was marginally positive on CatBoost; against
the matched orthogonal control, at most 2/4 were positive on either
base, and none survived multiple-testing correction. These four
endpoints are reported as exploratory and are not used for confirmatory
inference.

Table 2. Five-seed mean official metrics for both bases and ungated
branches.

|                      |            |        |            |             |        |            |             |
|----------------------|------------|--------|------------|-------------|--------|------------|-------------|
| **Endpoint**         | **Metric** | **ET** | **QRC-ET** | **Orth-ET** | **CB** | **QRC-CB** | **Orth-CB** |
| Caco-2               | MAE        | 0.469  | 0.463      | 0.468       | 0.296  | 0.318      | 0.306       |
| HIA                  | AUROC      | 0.896  | 0.856      | 0.890       | 0.980  | 0.972      | 0.978       |
| P-gp                 | AUROC      | 0.912  | 0.893      | 0.913       | 0.927  | 0.932      | 0.936       |
| Bioavailability      | AUROC      | 0.612  | 0.595      | 0.643       | 0.722  | 0.694      | 0.715       |
| Lipophilicity        | MAE        | 0.796  | 0.798      | 0.795       | 0.576  | 0.581      | 0.577       |
| Solubility           | MAE        | 1.402  | 1.438      | 1.425       | 0.844  | 0.871      | 0.844       |
| BBB                  | AUROC      | 0.878  | 0.864      | 0.881       | 0.913  | 0.905      | 0.917       |
| PPBR                 | MAE        | 10.131 | 10.009     | 9.847       | 7.880  | 8.428      | 8.303       |
| VDss                 | Spearman   | 0.490  | 0.260      | 0.373       | 0.703  | 0.416      | 0.452       |
| CYP2C9 inhibition    | AUPRC      | 0.725  | 0.714      | 0.721       | 0.771  | 0.770      | 0.772       |
| CYP2D6 inhibition    | AUPRC      | 0.642  | 0.638      | 0.640       | 0.707  | 0.706      | 0.706       |
| CYP3A4 inhibition    | AUPRC      | 0.823  | 0.824      | 0.824       | 0.869  | 0.869      | 0.870       |
| CYP2C9 substrate     | AUPRC      | 0.381  | 0.382      | 0.384       | 0.355  | 0.348      | 0.345       |
| CYP3A4 substrate     | AUROC      | 0.622  | 0.612      | 0.626       | 0.658  | 0.662      | 0.665       |
| CYP2D6 substrate     | AUPRC      | 0.634  | 0.658      | 0.643       | 0.714  | 0.684      | 0.721       |
| Half-life            | Spearman   | 0.312  | 0.299      | 0.242       | 0.553  | 0.143      | 0.203       |
| Hepatocyte clearance | Spearman   | 0.363  | 0.358      | 0.348       | 0.459  | 0.449      | 0.454       |
| Microsome clearance  | Spearman   | 0.523  | 0.499      | 0.518       | 0.596  | 0.599      | 0.598       |
| LD50                 | MAE        | 0.660  | 0.658      | 0.660       | 0.647  | 0.654      | 0.645       |
| hERG                 | AUROC      | 0.810  | 0.807      | 0.809       | 0.853  | 0.853      | 0.856       |
| AMES                 | AUROC      | 0.835  | 0.822      | 0.834       | 0.855  | 0.850      | 0.854       |
| DILI                 | AUROC      | 0.796  | 0.776      | 0.790       | 0.894  | 0.870      | 0.894       |

Table 3. Endpoint effects of QRC versus the matched real-orthogonal map
with Holm correction.

|                      |            |                           |               |                           |               |
|----------------------|------------|---------------------------|---------------|---------------------------|---------------|
| **Endpoint**         | **Metric** | **ET effect \[95% CI\]**  | **ET Holm p** | **CB effect \[95% CI\]**  | **CB Holm p** |
| Caco-2               | MAE        | +0.005 \[-0.009, +0.017\] | 1.000         | -0.012 \[-0.025, -0.001\] | 0.646         |
| HIA                  | AUROC      | -0.034 \[-0.068, -0.004\] | 1.000         | -0.006 \[-0.019, +0.001\] | 1.000         |
| P-gp                 | AUROC      | -0.020 \[-0.046, +0.003\] | 1.000         | -0.004 \[-0.014, +0.004\] | 1.000         |
| Bioavailability      | AUROC      | -0.048 \[-0.093, -0.002\] | 1.000         | -0.021 \[-0.056, +0.006\] | 1.000         |
| Lipophilicity        | MAE        | -0.002 \[-0.007, +0.003\] | 1.000         | -0.004 \[-0.007, -0.000\] | 0.503         |
| Solubility           | MAE        | -0.013 \[-0.035, +0.006\] | 1.000         | -0.027 \[-0.038, -0.016\] | 0.011         |
| BBB                  | AUROC      | -0.017 \[-0.032, -0.003\] | 0.480         | -0.012 \[-0.024, -0.004\] | 0.230         |
| PPBR                 | MAE        | -0.162 \[-0.324, -0.005\] | 1.000         | -0.125 \[-0.236, -0.015\] | 0.639         |
| VDss                 | Spearman   | -0.113 \[-0.168, -0.053\] | 0.042         | -0.037 \[-0.130, +0.060\] | 1.000         |
| CYP2C9 inhibition    | AUPRC      | -0.007 \[-0.014, +0.001\] | 1.000         | -0.001 \[-0.003, +0.001\] | 1.000         |
| CYP2D6 inhibition    | AUPRC      | -0.002 \[-0.006, +0.004\] | 1.000         | +0.000 \[-0.003, +0.004\] | 1.000         |
| CYP3A4 inhibition    | AUPRC      | +0.000 \[-0.002, +0.003\] | 1.000         | -0.000 \[-0.002, +0.001\] | 1.000         |
| CYP2C9 substrate     | AUPRC      | -0.002 \[-0.046, +0.033\] | 1.000         | +0.003 \[-0.022, +0.025\] | 1.000         |
| CYP3A4 substrate     | AUROC      | -0.015 \[-0.039, +0.008\] | 1.000         | -0.003 \[-0.020, +0.015\] | 1.000         |
| CYP2D6 substrate     | AUPRC      | +0.015 \[-0.022, +0.045\] | 1.000         | -0.036 \[-0.063, -0.007\] | 0.052         |
| Half-life            | Spearman   | +0.057 \[-0.016, +0.127\] | 1.000         | -0.060 \[-0.188, +0.071\] | 1.000         |
| Hepatocyte clearance | Spearman   | +0.010 \[-0.018, +0.047\] | 1.000         | -0.005 \[-0.072, +0.049\] | 1.000         |
| Microsome clearance  | Spearman   | -0.019 \[-0.047, +0.009\] | 1.000         | +0.001 \[-0.030, +0.040\] | 1.000         |
| LD50                 | MAE        | +0.003 \[-0.009, +0.018\] | 1.000         | -0.009 \[-0.021, +0.001\] | 1.000         |
| hERG                 | AUROC      | -0.002 \[-0.030, +0.027\] | 1.000         | -0.003 \[-0.024, +0.020\] | 1.000         |
| AMES                 | AUROC      | -0.012 \[-0.017, -0.006\] | 0.011         | -0.005 \[-0.010, -0.000\] | 0.784         |
| DILI                 | AUROC      | -0.014 \[-0.062, +0.034\] | 1.000         | -0.024 \[-0.052, +0.001\] | 1.000         |

Effects in Table 3 are direction-normalized so positive values favor
QRC; brackets show paired 95% scaffold-bootstrap intervals. Holm
correction covers the 22 endpoints within each base. All three
Holm-significant results favor the orthogonal map: AMES on ExtraTrees
(AUROC difference -0.0115, Holm p=0.011), VDss on ExtraTrees (Spearman
difference -0.1127, Holm p=0.042), and Solubility on CatBoost (MAE
difference -0.0268, Holm p=0.011). No endpoint is significantly
positive.

## 5.2 Endpoint-Level Gating

Validation gating set the QRC weight to zero in 47/110 selections on
ExtraTrees and 55/110 selections on CatBoost. Gated QRC versus the
identically gated orthogonal map favored QRC at 11 endpoints and the
orthogonal branch at 11 on ExtraTrees; CatBoost favored QRC at 4, the
orthogonal branch at 17, and tied at 1 on CatBoost. Neither pair
produced a Holm-significant positive endpoint. Exploratory equivalence
covered 8 and 10 endpoints, respectively, but several of those results
reflect both branches being returned to the base model and are not
evidence of a quantum contribution.

Table 4. Representative behavior of validation gating.

|          |              |            |                       |                               |            |
|----------|--------------|------------|-----------------------|-------------------------------|------------|
| **Base** | **Endpoint** | **Metric** | **QRC gate weights**  | **Gated QRC-Orth \[95% CI\]** | **Holm p** |
| ET       | Half-life    | Spearman   | 0/0.5/1/0.5/1         | +0.062 \[+0.001, +0.117\]     | 0.940      |
| ET       | PPBR         | MAE        | 0.75/0.75/0.25/1/0.75 | -0.153 \[-0.260, -0.046\]     | 0.242      |
| ET       | AMES         | AUROC      | 0.5/0/0.25/0/0        | -0.001 \[-0.002, -0.000\]     | 0.940      |
| CB       | Half-life    | Spearman   | 0/0/0/0/0             | +0.000 \[+0.000, +0.000\]     | 1.000      |
| CB       | PPBR         | MAE        | 0.25/0/0/0/0          | -0.023 \[-0.045, -0.002\]     | 0.510      |
| CB       | Solubility   | MAE        | 0.25/0.25/0/0/0.25    | -0.001 \[-0.004, +0.002\]     | 1.000      |

The small-effect endpoints show that gating limits negative transfer
without creating new extrapolation ability. On ExtraTrees, Half-life
improved by 0.0616 after gating but had Holm p=0.94; PPBR remained
-0.1531. On CatBoost, all five seeds set the QRC weight to zero for
Half-life, producing exactly zero difference; Solubility selected zero
in three of five splits and retained a difference of -0.0010.

## 5.3 Additional Comparisons

Table 5. Direction counts and Holm-significant counts across endpoints.

|                       |                |               |                   |                   |
|-----------------------|----------------|---------------|-------------------|-------------------|
| **Contrast**          | **QRC better** | **QRC worse** | **Holm positive** | **Holm negative** |
| ET: QRC − orth        | 6              | 16            | 0                 | 2                 |
| CB: QRC − orth        | 3              | 19            | 0                 | 1                 |
| ET: QRC − Fourier     | 3              | 19            | 0                 | 1                 |
| CB: QRC − Fourier     | 3              | 19            | 0                 | 1                 |
| ET: QRC − base        | 6              | 16            | 0                 | 2                 |
| CB: QRC − base        | 4              | 18            | 0                 | 5                 |
| ET: gated QRC − orth  | 11             | 11            | 0                 | 0                 |
| CB: gated QRC − orth  | 4              | 17            | 0                 | 0                 |
| ET: QRC + orth − orth | 12             | 10            | 0                 | 0                 |
| CB: QRC + orth − orth | 6              | 14            | 0                 | 0                 |

QRC versus random Fourier features also produced 3 QRC-favoring and 19
control-favoring endpoint estimates on each base. Relative to the
residual-free base, 6/16 ExtraTrees and 4/18 CatBoost endpoint estimates
favored QRC, with 2 and 5 Holm-significant negative endpoints,
respectively. Metrics with different units were not averaged across
endpoints.

Pairing each QRC map index with the corresponding real-orthogonal map
produced visible within-endpoint variation but no stable positive task
subset. Full per-map metrics and predictions are included in the
reproduction package.

Allowing QRC and the orthogonal branch to enter together, with two
scalar weights selected on validation, produced 12 QRC-favoring/10
control-favoring estimates versus identically gated orthogonal features
on ExtraTrees and 6/14 with 2 ties on CatBoost. No endpoint was
Holm-significantly positive. Against the residual-free base, the
combined model was 10 better/12 worse on ExtraTrees, including one
positive and one negative significant endpoint, and 7 better/14 worse/1
tied on CatBoost without a significant improvement. Joint gating did not
provide transferable QRC complementarity.

The finite-shot panel covered BBB, hERG, Caco2, LD50, PPBR, DILI, CYP2D6
inhibition, and VDss. Each Pauli readout was independently simulated
with 1,024, 4,096, and 16,384 shots, and residual heads were retrained
on the sampled features. QRC versus gated orthogonal features was 5/3 on
ExtraTrees at all shot budgets and 2/6, 1/7, and 1/7 on CatBoost.
Increasing shots moved the CatBoost direction counts toward those
observed under exact simulation rather than revealing a shot-dependent
benefit.

## 5.4 Low-Data Scaling

To test the regime in which QRC has the clearest theoretical motivation,
we used the same eight representative endpoints at 5%, 10%, 20%, 40%,
and 100% of the outer training data. Each subset contained at least 96
records so that three inner scaffold folds remained estimable; actual
sample counts are recorded for every result. Subsets were drawn only
from outer training data, while validation and test membership remained
fixed.

The number of endpoints where ungated QRC beat the orthogonal map was
2/8, 0/8, 1/8, 0/8, and 2/8 on ExtraTrees and 1/8, 0/8, 1/8, 0/8, and
1/8 on CatBoost. Validation gating reduced degradation and reached 6/8
positive endpoints on ExtraTrees at 20% training, but the corresponding
CatBoost count was 4/8; no other scale produced a synchronized positive
shift across bases. Gated results indicate risk control, not a low-data
quantum advantage. Endpoint curves are shown in Supplementary Figure S1.

## 5.5 Independent External Endpoints

External validation used the ToxTree hERG test collection and the B3DB
BBB classification set \[29,30\]. hERG used the original binary cutoff
PIC50 &gt;= 4.5; after removing canonical identities present in TDC hERG
training or test data, 293 molecules remained. For B3DB, provider
BBB+/BBB- labels were used; after removing canonical TDC BBB overlaps,
2,317 molecules remained. DeepChem ESOL shared almost all canonical
molecules with TDC AqSolDB, leaving only 18 non-overlapping records, and
was excluded.

On external hERG, gated QRC minus gated orthogonal AUROC was +0.0112 for
ExtraTrees (95% CI \[-0.0029, 0.0246\], Holm p=0.200) and +0.0402 for
CatBoost (\[0.0221, 0.0591\], Holm p=0.002). On B3DB BBB, the same
effect was -0.0046 for ExtraTrees (\[-0.0076, -0.0019\], Holm p=0.002)
and -0.0034 for CatBoost (\[-0.0065, -0.0006\], Holm p=0.016). Joint
gating showed the same split: CatBoost was +0.0298 on hERG and negative
with Holm significance on BBB for both bases. The coexistence of a hERG
signal and BBB negative transfer implies source dependence rather than a
general transferable advantage. Full external intervals are shown in
Supplementary Figure S2.

Figure 3 decomposes the hERG and B3DB differences. For CatBoost/hERG,
gated QRC minus the residual-free base was +0.0285 AUROC (95% CI
\[0.0137, 0.0437\]), whereas gated orthogonal minus the base was -0.0117
(\[-0.0216, -0.0011\]); the +0.0402 primary difference combines a QRC
gain with an orthogonal decrement. The hERG QRC-minus-orthogonal AUPRC
difference was +0.0304, with Brier-score and log-loss improvements of
+0.0038 and +0.0363. Both hERG branches remained poorly calibrated, with
slopes of approximately 0.15-0.26. In B3DB, QRC minus orthogonal AUPRC
was -0.0047 for ExtraTrees and -0.0061 for CatBoost, and Brier-score and
log-loss differences did not favor QRC. Full values are reported in
Supplementary Tables S7 and S8.

The continuous-label rank transfer produced an unadjusted CatBoost/hERG
pIC50 Spearman difference of +0.043. This difference did not survive
Holm correction across 12 comparisons and did not replicate for BBB
logBB. Because it ranks predictions from binary-trained models, it is
not an independently trained regression evaluation; the B3DB continuous
subset is 86.8% positive.

<img src="outputs\Revised_Manuscript_Media\media\image3.png" title="External hERG and B3DB effect decomposition and CatBoost calibration curves." style="width:6.25in;height:5.22431in" alt="External hERG and B3DB effect decomposition and CatBoost calibration curves." />

Figure 3. External classification decomposition and calibration. (A-B)
AUROC differences for gated QRC versus base, gated orthogonal versus
base, and gated QRC versus gated orthogonal; positive values favor the
first method. (C-D) Five-seed mean CatBoost calibration curves using
prediction quintiles; the dashed diagonal is perfect calibration.
Decomposition explains the primary comparison and does not replace the
prespecified external AUROC test.

## 5.6 Simulated Decoherence

As a controlled noise stress test, we added local single-qubit
depolarizing noise with probabilities 0.001, 0.005, and 0.010 and fixed
4,096 shots on the same eight endpoints. Symmetric depolarizing
multiplies Z expectations by lambda=1-4p/3 and ZZ expectations by
lambda^2; residual heads were retrained on the noisy features. The model
excludes gate-specific error, leakage, crosstalk, and hardware
connectivity and tests sensitivity to controlled readout attenuation
only.

Across all three noise levels, QRC versus gated orthogonal features
remained 5/3 on ExtraTrees and 1/7 on CatBoost. Against the
residual-free base, the counts were 3/5 for ExtraTrees and 2/6 for
CatBoost. Increasing the depolarizing probability from 0.001 to 0.010
produced no directional reversal. Supplementary Figure S3 records the
sensitivity.

## 5.7 Bounded Reservoir-Family Search

To address the possibility that only one reservoir was tested, we
prespecified five fixed parameter families: baseline, weak, strong,
short, and long. Each family contained five independent quantum maps. We
also constructed five real-orthogonal candidate groups of five
independent maps each. Every candidate formed a five-map residual
ensemble, and TDC validation selected its gate weight. QRC and the
orthogonal family had equal candidate and map budgets before testing.

For the eight representative endpoints, validation selected QRC and the
orthogonal search at four endpoints each on ExtraTrees. On CatBoost, it
selected QRC at two endpoints, the orthogonal search at five, and
recorded one tie. No endpoint was Holm-significantly positive. The
baseline QRC setting remained the most frequently selected configuration
(15/40 on ExtraTrees and 25/40 on CatBoost), indicating that the broader
family did not reveal a new stable signal. Against the residual-free
base, the direction counts were 4/4 on ExtraTrees and 2/5/1 on CatBoost;
VDss was significantly worse on both bases. These results weaken
under-tuning as an explanation for the null finding.

<img src="outputs\Revised_Manuscript_Media\media\image4.png" title="Endpoint-level paired differences of ungated QRC versus matched orthogonal quadratic features across all 22 TDC ADMET endpoints." style="width:6.22014in;height:6.65347in" alt="Endpoint-level paired differences of ungated QRC versus matched orthogonal quadratic features across all 22 TDC ADMET endpoints." />

Figure 4. Endpoint-level differences of ungated QRC versus the matched
real-orthogonal map. Classification metrics use absolute units, MAE uses
a relative percentage of the reference MAE, and Spearman uses absolute
units. Intervals are 95% scaffold-cluster bootstrap intervals; red
indicates Holm significance.

## 5.8 Independent Continuous hERG Regression

To avoid treating rank preservation from a binary classifier as
continuous-value prediction, we added a fixed ToxTree hERG pIC50
regression. After removing TDC overlap, the source Dev-set was split by
Bemis-Murcko scaffold into 6,895 training and 985 validation molecules.
The source Test-set was filtered to remove TDC overlaps and scaffolds
shared with the external Dev-set, retaining 214 test molecules in 155
scaffolds. QRC, orthogonal quadratic, random Fourier, and linear
residual heads followed the TDC protocol. External test labels were not
used to select map seeds, PCA dimension, regularization, or
hyperparameters.

Across five model seeds, no comparison showed a confirmed QRC increment.
QRC minus orthogonal Spearman was +0.0229 on ExtraTrees (95% CI
\[-0.0121, 0.0608\]) and +0.0093 on CatBoost (\[-0.0168, 0.0325\]); QRC
minus the CatBoost base was +0.0292 (\[-0.0034, 0.0604\]). MAE
differences were close to zero. No comparison was significant after Holm
correction across the 12 metric, base, and contrast tests. The cohort is
independent of TDC labels, but 214 test molecules in 155 scaffolds limit
statistical power. Full results are shown in Supplementary Figure S4 and
Supplementary Table S10.

## **5.9 Circuit-Level Aer Audit**

We also examined circuit-specific readout degradation with explicit
Qiskit circuits: 32-dimensional amplitude preparation, an eight-step
Lie-Trotter fixed-Hamiltonian evolution, and all-qubit Z-basis
measurement. The panel covered eight representative endpoints, 32
stratified test states per endpoint, and five reservoir maps; transpiled
circuits had depth 81 and about 136 operations. Aer density-matrix
simulation included one- and two-qubit gate depolarizing errors plus
independent readout flips.

Relative to exact matrix readouts, normalized RMSE was 0.189-0.199,
0.337-0.351, and 0.551-0.569 at low, medium, and high error,
respectively. Signal slopes were approximately 0.81, 0.66, and 0.45,
whereas Spearman correlations remained 0.9974-0.9986, 0.9916-0.9958, and
0.9742-0.9866. The noiseless Trotterized RMSE was 0.0058-0.0070. Circuit
errors mainly contracted readout amplitude while retaining substantial
relative ordering; they did not add new advantage evidence. This is a
readout-fidelity audit, not end-to-end retraining on noisy features.
Full results are reported in Supplementary Figure S5 and Supplementary
Table S11.

## 5.10 Benchmark Calibration and Source Diagnostics

The known-signal calibration separated the three feature families. For
QRC-derived targets, QRC minus orthogonal test performance was +0.302 on
ExtraTrees and +0.190 on CatBoost, and the expected QRC family ranked
first in 150/150 simulations (100.0%) for both bases. For
orthogonal-derived targets, the same contrast reversed to -0.332 and
-0.238, and the expected orthogonal family ranked first in 149/150
simulations (99.3%) for ExtraTrees and 149/150 (99.3%) for CatBoost. For
null targets, two-sided paired permutation tests were significant in
7/150 simulations (4.7%) on ExtraTrees and 3/150 (2.0%) on CatBoost.

Effect decomposition identified endpoints where an apparent
QRC-versus-base gain did not remain after the matched orthogonal
contribution was removed. Among the six ExtraTrees endpoints with a
positive QRC-versus-base point estimate, two had a non-positive
QRC-specific effect; on CatBoost, three of four such endpoints were
neutralized. When both branches were selected on validation, QRC beat
the orthogonal map on 13/22 ExtraTrees and 12/22 CatBoost endpoints, a
near-balanced result rather than a cross-base advantage.

Feature-capacity diagnostics indicated that the QRC branch was not
advantaged by higher-dimensional test features. The mean test effective
rank over 15 readouts was 14.10 for QRC versus 14.62 for the orthogonal
control on ExtraTrees, and 12.82 versus 14.25 on CatBoost. Linear
centered-kernel alignment between the five-map mean QRC and orthogonal
features was 0.20 and 0.30, respectively, showing distinct geometries at
comparable output and fitted-parameter budgets.

External stratification did not follow a monotonic similarity gradient.
For CatBoost/hERG, QRC-specific AUROC changed from +0.003 in Q1 to
+0.037, +0.070, and +0.013 across Q2-Q4; the Q3 interval \[+0.011,
+0.128\] excluded zero. ExtraTrees showed a different pattern, with
QRC-specific effects of -0.064, -0.059, +0.055, and -0.006 across Q1-Q4;
the Q3 interval was \[+0.018, +0.092\]. B3DB showed no consistently
positive quartile. The hERG signal was localized and source-specific
rather than a simple function of nearest-TDC similarity.

# 6 Discussion

## 6.1 What the Constrained Quadratic Map Explains

With real amplitude inputs, every Z or ZZ expectation after fixed
evolution is a real symmetric quadratic form. Training-side
standardization is affine, so the linear readout combines these forms
and adds a fixed offset. Given the fitted parameters, the QRC residual
can be reproduced by a real quadratic form and a constant on the
normalized 32-dimensional latent input. This statement applies to that
latent space, not to the raw molecular graph. All five QRC readout
matrices had rank 15 and a median condition number of 1.210; the
real-orthogonal readout matrices had rank 15 and condition number 1.000.
On held-out molecular features, effective rank was 14.10 versus 14.62 on
ExtraTrees and 12.82 versus 14.25 on CatBoost, with linear
centered-kernel alignments of 0.20 and 0.30. The branches had equal
output and fitted-parameter budgets, different geometry, and comparable
but not identical effective feature capacity.

The real-orthogonal quadratic map had lower point-estimate error on
16/22 ExtraTrees endpoints and 19/22 CatBoost endpoints. Averaging five
random realizations did not support the hypothesis that the fixed Ising
reservoir geometry is better suited to ADMET than a general quadratic
map. This agrees with a recent cross-target QML benchmark in which
localized candidate signals did not produce a global advantage \[27\].
The conclusion is limited to the current five-qubit amplitude encoding,
readout, and exact simulation \[12,13,28\].

## 6.2 When Gating Reduces Degradation

The benefit of gating mainly comes from stopping harmful residuals, not
from discovering transferable quantum corrections. CatBoost selected
zero QRC weight in half of all endpoint-split decisions, and 17 endpoint
estimates remained lower than the identically gated orthogonal branch.
Several endpoints had near-zero differences within the exploratory
equivalence margins, but this is consistent with the quantum branch
being suppressed and cannot replace a test of positive superiority.
Gating is a risk-control rule and not a molecule-level confidence
estimate.

## 6.3 What the Strong Base and External Cohorts Reveal

The strong-base comparison provides a direct stress test.
MapLight-CatBoost outperformed Morgan-ExtraTrees on 21/22 endpoints, but
QRC's relative advantage did not persist on the stronger base.
Validation gating, finite shots, low-data scaling, and simulated noise
did not reveal a transferable quantum correction. The circuit audit
likewise showed readout attenuation without new advantage evidence.

The external results support only a source-specific candidate on hERG.
The same direction appeared in pIC50 rank transfer and independent
regression, but neither survived the joint multiplicity correction. B3DB
logBB was near zero and B3DB BBB classification degraded significantly,
so the hERG result cannot be generalized across sources. These findings
support testing future quantum encodings on a strong classical base with
matched input, capacity, and candidate budgets; they do not establish a
general ADMET descriptor.

## 6.4 Chemical-Space and Source Dependence

A descriptive chemical-space audit tested whether cohort differences
could reflect source proximity. Both cohorts were free of exact
canonical identities from the corresponding TDC archive. For hERG, 23 of
293 molecules (7.8%) retained a Bemis-Murcko scaffold present in TDC
train/validation data; the median nearest Morgan Tanimoto similarity
(radius 2, 2048 bits) was 0.234 and the 90th percentile was 0.423. For
B3DB BBB, 562 of 2,317 molecules (24.3%) shared a TDC train/validation
scaffold, with a median nearest similarity of 0.346 and a 90th
percentile of 0.722. B3DB contained 48.9% positives versus 76.4% in the
full TDC BBB archive, whereas hERG contained 76.4% versus 68.9% in TDC.
The two cohorts differed from their TDC sources in both chemical
proximity and label composition.

Stratifying the held-out predictions did not support a simple
scaffold-overlap or similarity explanation for the hERG signal. For
CatBoost, the hERG gated-QRC minus gated-orthogonal effect was -0.0026
AUROC among the 23 molecules with a shared train/validation scaffold and
+0.0452 among the 270 molecules with a novel scaffold. The earlier
top-quartile split gave +0.0196 in the highest-similarity group and
+0.0494 in the other three quartiles. The finer quartile analysis was
non-monotonic: CatBoost and ExtraTrees were positive in Q3 but not in
every adjacent quartile. B3DB effects were negative across
shared-scaffold, novel-scaffold, and most similarity strata. Full source
audits are reported in Supplementary Tables S5, S6, and S16. These
descriptive strata locate where an effect appears; they do not control
source, assay batch, or label definition and cannot establish a causal
chemical mechanism.

## **6.5 Interpretation and Reuse**

A low-dimensional fixed quantum reservoir has its clearest theoretical
rationale for tasks with limited training data, strong local nonlinear
interactions, and classical kernels that do not adequately cover the
chemical distribution. The global TDC ADMET endpoints generally contain
larger and more heterogeneous label collections, the regime in which the
present design showed no stable gain. The low-data curves likewise did
not show a synchronized positive shift across bases. This observation
does not rule out angle encodings, task-conditioned amplitude encodings,
trainable circuits, larger reservoirs, or different readout strategies;
each must be reassessed against strong bases and independent source
cohorts.

Neither the hERG candidate nor the B3DB negative transfer establishes a
mechanistic or general quantum effect. The reviewed QML-ADMET studies
use different fixed reservoirs, Hamiltonian-derived features,
quantum-inspired preprocessing, circuit search, or jointly trained
residuals. Their task counts, controls, and external validation settings
do not support like-for-like equivalence. Table 1 summarizes the design
differences, and Supplementary Table S4 provides the expanded
comparison. The study contributes a reusable minimum evaluation
protocol: prespecify the primary comparator, match candidate and map
budgets, infer with scaffold clusters, correct across endpoints,
interpret equivalence separately from superiority, and report both
cross-base and cross-source results.

For computational context, exact state-vector simulation of five qubits
is not a quantum-speedup demonstration and provides no hardware runtime
estimate. The scale was chosen to construct an exact, equal-readout
quadratic control and to avoid confounding circuit expressivity with
physical noise. The results do not support a quantum runtime advantage
and cannot be used to infer the feasibility of larger reservoirs,
fault-tolerant quantum computing, or a specific hardware topology; these
are separate experimental questions.

To make the conclusions directly reusable, Table 6 converts the
matched-control principles above into minimum reporting requirements.
The table is an evaluation checklist for evidence comparability and
transfer; it is not a predetermined claim about other quantum
architectures.

Table 6. Minimum matched-evaluation requirements for fixed-circuit QML
molecular-property studies.

|                                                                                               |                                               |
|-----------------------------------------------------------------------------------------------|-----------------------------------------------|
| **Requirement and implementation**                                                            | **Primary evidence**                          |
| Same 32D input, 15 Pauli readouts, and linear residual head                                   | Figure 1; Proposition 1; Table 3              |
| Matched randomness: five independent maps per family and five scaffold splits                 | Methods 4.2; Table 3                          |
| Two strong classical bases: Morgan-ExtraTrees and MapLight-CatBoost                           | Table 2; Table 3                              |
| Scaffold-clustered inference with Holm and TOST                                               | Section 3; Figure 4; Table 5                  |
| Independent sources: ToxTree hERG and B3DB BBB, including continuous-label checks             | Figure 3; Tables S7-S10, S16                  |
| Report all endpoint effects, gate choices, low-data, shots, noise, and family search          | Tables 3-5, S12-S16; Figures S1-S10           |
| Claim boundaries: exact simulation, circuit-level noise, and hardware are reported separately | Methods 4.2, 4.4; Limitations; Figures S5-S10 |

# 7 Limitations

Three evaluation limits constrain generalization. The public TDC test
sets may have been reused by earlier studies and are not prospective
cohorts; scaffold splits reduce, but do not eliminate, near analogues
across laboratories, time, and chemical series. The low-data analysis
covers eight endpoints, and its 96-record minimum changes the effective
fraction for the smallest endpoints. The primary external comparison
contains two classification cohorts that differ in assay source and
label construction \[3-5\].

The execution boundary is equally explicit. Exact state-vector
calculation isolates the fixed circuit's expressive behavior but does
not evaluate physical gate error, readout crosstalk, connectivity, or
scheduling. Finite-shot analysis samples each Pauli expectation
independently. The simplified depolarizing model omits gate-specific
error, leakage, crosstalk, and physical scheduling. The Qiskit/Aer audit
adds transpiled gate depolarization and readout flips, but uses fixed
synthetic error parameters and does not retrain the full predictor on
circuit-noisy features. Trainable circuits, task-conditioned amplitude
encoding, and other PCA dimensions were not evaluated.

The auxiliary analyses have narrower scope. Continuous-label transfer
ranks outputs from binary-trained models and is not an independently
trained regression. The separate pIC50 regression uses 214 test
molecules in 155 scaffolds under a fixed protocol and has limited
statistical power. B3DB logBB was available for only 613/2,317
non-overlapping molecules and was strongly class-enriched. The
chemical-space figure uses a linear fingerprint projection and three
basic descriptors, not a complete applicability-domain model, and TOST
margins are exploratory benchmark thresholds rather than clinical or
regulatory limits \[21\]. Random-map sensitivity covers five
realizations per family. The known-signal calibration uses synthetic
targets drawn from the tested feature families; it establishes
detectability for those designs, not coverage of every possible
nonlinear signal. The reported comparison applies to five-qubit
amplitude encoding, a fixed Hamiltonian reservoir, 15 Pauli readouts, a
linear residual head, and exact simulation; other encodings, trainable
circuits, larger reservoirs, and physical hardware require independent
evaluation.

# 8 Conclusion

Across 22 official TDC ADMET endpoints, fixed five-qubit reservoir
residuals showed no stable increment over real-orthogonal quadratic maps
with the same readout dimension, fitted-parameter budget, and map
budget. This result held on both Morgan-ExtraTrees and the stronger
MapLight-CatBoost base. Validation gating reduced harmful residuals but
did not produce a stable advantage over gated classical controls. Joint
gating, low-data scaling, finite shots, and simulated decoherence did
not reverse the result. External hERG produced a CatBoost-specific
candidate signal, whereas B3DB BBB showed significant negative transfer.
Continuous-label transfer and independent pIC50 regression showed only
uncorrected weak CatBoost/hERG directions, and neither had a
corresponding BBB signal. Known-signal calibration recovered the
synthetic QRC and classical targets, and null false-positive rates
remained at or below 5%.

The study's main contribution is a calibrated matched-evaluation
workflow that distinguishes ordinary quadratic effects,
reservoir-specific candidate effects, and source dependence. The hERG
signal is a bounded candidate, not a demonstrated mechanism of
cardiotoxicity, and the B3DB result does not show that quantum methods
are universally ineffective. The conclusion applies to the tested
five-qubit amplitude-encoded, fixed-Hamiltonian reservoir with 15 Pauli
readouts, a linear residual head, and exact simulation; other encodings,
trainable circuits, larger reservoirs, and physical hardware require
independent evaluation.

# Data and Code Availability

The official TDC archive is available as Harvard Dataverse file 4426004
with SHA-256
bd0005246cb6f1672333c28ad202112a8bf071ab65d847848715030308faf1f1.
External hERG data are from Zenodo 5807719 and BBB data from B3DB.
Source, label rules, deduplication, and overlap audits are included in
the reproduction package. The MapLight reference and MIT license are
retained, and upstream data licenses are listed with the archived
materials.

The reproduction package contains processing scripts, five scaffold
splits, five random maps per family, base configurations, all
split-level predictions, gating, finite-shot, low-data, external
decomposition and calibration, continuous-label transfer, independent
pIC50 regression, simplified and circuit-level noise, bounded-family,
TOST-sensitivity, effect-decomposition, capacity, and source-gradient
results, statistical scripts, figure-generation code, and environment
locks. The versioned code and result index are at
https://github.com/575914291-source/qrc-admet-matched-evaluation.
Official test labels were used only for scoring after configuration lock
and were not used for training, map generation, joint weights, or
gating.

# References

1\. Huang K, Fu T, Gao W, et al. Therapeutics Data Commons: Machine
Learning Datasets and Tasks for Drug Discovery and Development. NeurIPS
Datasets and Benchmarks, 2021.
https://datasets-benchmarks-proceedings.neurips.cc/paper/2021/hash/4c56ff4ce4aaf9573aa5dff913df997a-Abstract-round1.html

2\. Therapeutics Data Commons. ADMET Benchmark Group.
https://tdcommons.ai/benchmark/admet\_group/overview/

3\. Yang K, Swanson K, Jin W, et al. Analyzing Learned Molecular
Representations for Property Prediction. Journal of Chemical Information
and Modeling, 2019. https://doi.org/10.1021/acs.jcim.9b00237

4\. Sheridan R P. Time-Split Cross-Validation as a Method for Estimating
the Goodness of Prospective Prediction. Journal of Chemical Information
and Modeling, 2013. https://doi.org/10.1021/ci400084k

5\. Koleiev I, Stratiichuk R, Shevchuk N, et al. An End-User Audit of
Reproducibility, Data Leakage, and Overfitting of the Top-Ranked ADMET
Prediction Models in TDC Leaderboards. Journal of Chemical Information
and Modeling, 2026. https://doi.org/10.1021/acs.jcim.6c00819

6\. Notwell J H, Wood M W. ADMET property prediction through
combinations of molecular fingerprints. arXiv preprint, 2023.
https://arxiv.org/abs/2310.00174

7\. Kamuntavičius G, Paquet T, Bastas O, et al. Benchmarking ML in ADMET
predictions: the practical impact of feature representations in
ligand-based models. Journal of Cheminformatics, 2025.
https://doi.org/10.1186/s13321-025-01041-0

8\. Beaulieu D, Kornjača M, Krunic Z, et al. Robust Quantum Reservoir
Learning for Molecular Property Prediction. Journal of Chemical
Information and Modeling, 2025. https://doi.org/10.1021/acs.jcim.5c00958

9\. Benson B M, Byler K, Petroff A, Keinan S, Shipman W J.
Quantum-Inspired Hamiltonian Feature Extraction for ADMET Prediction: A
Simulation Study. arXiv preprint, 2026. https://arxiv.org/abs/2603.03109

10\. Mansour B, Takahashi D K, Rafaelyan G. ADMET Property Prediction
with Quantum-Inspired Preprocessing. bioRxiv preprint, 2026.
https://doi.org/10.64898/2026.06.30.735582

11\. Zheng K, Fu T, Liang Z. QCS-ADME: Quantum Circuit Search for Drug
Property Prediction with Imbalanced Data and Regression Adaptation.
Quantum Machine Intelligence, 2026.
https://doi.org/10.1007/s42484-026-00369-6

12\. Jia C, Ma Y, Wang Y, Guo C. Quantum-Circuit Residuals for Receptor
Functional Potency Prediction: Predictive Gains and Quadratic Structure.
arXiv preprint, 2026. https://arxiv.org/abs/2610.13037

13\. Bowles J, Ahmed S, Schuld M. Better than classical? The subtle art
of benchmarking quantum machine learning models. arXiv preprint, 2024.
https://arxiv.org/abs/2403.07059

14\. Wolpert D H. Stacked Generalization. Neural Networks, 1992.
https://doi.org/10.1016/S0893-6080(05)80023-1

15\. van der Laan M J, Polley E C, Hubbard A E. Super Learner.
Statistical Applications in Genetics and Molecular Biology, 2007.
https://doi.org/10.2202/1544-6115.1309

16\. Shi Y, Luo H, Liu F, Zhao S. Ark-ADMET: endpoint-specific selection
of molecular representations and hyperparameters for gradient-boosted
ADMET models under the Therapeutics Data Commons benchmark protocol.
bioRxiv preprint, 2026. https://doi.org/10.64898/2026.10.28.762420

17\. Fredsgaard L, Andersen M R, Schmidt M N. Calibrated Uncertainty
Quantification on TDC ADMET: What Can Be Resolved Across 22 Datasets?
arXiv preprint, 2026. https://arxiv.org/abs/2611.09373

18\. Field C A, Welsh A H. Bootstrapping Clustered Data. Journal of the
Royal Statistical Society: Series B, 2007.
https://doi.org/10.1111/j.1467-9868.2007.00593.x

19\. Winkler A M, Webster M A, Vidaurre D, Nichols T E, Smith S M.
Multi-level block permutation. NeuroImage, 2015.
https://doi.org/10.1016/j.neuroimage.2015.05.092

20\. Holm S. A Simple Sequentially Rejective Multiple Test Procedure.
Scandinavian Journal of Statistics, 1979.
https://www.jstor.org/stable/4615733

21\. Lakens D. Equivalence Tests: A Practical Primer for t Tests,
Correlations, and Meta-Analyses. Social Psychological and Personality
Science, 2017. https://doi.org/10.1177/1948550617697177

22\. Bemis G W, Murcko M A. The Properties of Known Drugs. 1. Molecular
Frameworks. Journal of Medicinal Chemistry, 1996.
https://doi.org/10.1021/jm9602928

23\. Geurts P, Ernst D, Wehenkel L. Extremely randomized trees. Machine
Learning, 2006. https://doi.org/10.1007/s10994-006-6226-1

24\. Rahimi A, Recht B. Random Features for Large-Scale Kernel Machines.
NeurIPS, 2007.
https://papers.nips.cc/paper\_files/paper/2007/hash/013a006f03dbc5392effeb8f18fda755-Abstract.html

25\. maplightrx. MapLight-TDC: reference implementation, commit c249378.
GitHub, accessed 2026-11-25. https://github.com/maplightrx/MapLight-TDC

26\. Prokhorenkova L, Gusev G, Vorobev A, Dorogush A V, Gulin A.
CatBoost: unbiased boosting with categorical features. NeurIPS, 2018.
https://proceedings.neurips.cc/paper/2018/hash/14491b756b3a51daac41c24863285549-Abstract.html

27\. Garg S, Garg S. Benchmarking Classical and Quantum Machine Learning
for Potency Prediction across Ten Therapeutically Relevant Targets. ACS
Medicinal Chemistry Letters, 2026.
https://doi.org/10.1021/acsmedchemlett.5c00724

28\. Wang L, Zhang D, Wang C, et al. Coherent Floquet quantum reservoirs
for molecular property prediction. arXiv:2609.11071, 2026.
https://arxiv.org/abs/2609.11071

29\. Arab I, Barakat K. ToxTree: descriptor-based machine learning
models for both hERG and Nav1.5 cardiotoxicity liability predictions.
arXiv:2112.13467, 2021. https://arxiv.org/abs/2112.13467; dataset:
https://doi.org/10.5281/zenodo.5807719

30\. Meng F, Xi Y, Huang J, Ayers P W. A curated diverse molecular
database of blood-brain barrier permeability with chemical descriptors.
Scientific Data, 2021. https://doi.org/10.1038/s41597-021-01069-5

31\. Robinson M C, Glen R C, Lee A A. Validating the validation:
reanalyzing a large-scale comparison of deep learning and machine
learning models for bioactivity prediction. Journal of Computer-Aided
Molecular Design, 2020. https://doi.org/10.1007/s10822-019-00274-0
