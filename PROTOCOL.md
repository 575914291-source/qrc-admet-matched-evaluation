# Frozen TDC ADMET evaluation protocol

## Scope

The paper evaluates fixed five-qubit reservoir residuals on the 22 endpoints
in the public TDC ADMET Group. The primary source is Harvard Dataverse file
4426004 with SHA-256
`bd0005246cb6f1672333c28ad202112a8bf071ab65d847848715030308faf1f1`.

The supplied competition files are not used as labels. They contain a blind
test set and a cleaned multi-task table. Those files may only support the
verified molecular feature cache when the raw SMILES exactly match the public
TDC archive.

## Splits

For every endpoint, the official `test.csv` remains fixed and is used only for
final evaluation. The official `train_val.csv` is split five times using the
PyTDC scaffold implementation with seeds 1 through 5 and fractions
0.875/0.125/0. The scaffold grouping is the RDKit Bemis-Murcko scaffold without
chirality. All acyclic molecules share the empty-scaffold group.

No canonical molecule or scaffold may cross train, validation, or test.

## Bases

Two classical bases are evaluated independently:

1. `extra_trees`: 512-bit radius-2 Morgan bits with 128 ExtraTrees trees,
   minimum leaf size 2, and square-root feature subsampling.
2. `catboost`: the corrected MapLight 2,563-feature representation with 240
   CatBoost iterations, depth 6, and learning rate 0.06. Count fingerprints are
   generated with `int32`, repairing the upstream `int8` overflow.

Three scaffold folds are formed inside each outer training set. Their
predictions create the out-of-fold offsets. Each base is then refit on the
outer training set for validation and test predictions.

## Branch features

The standardized base features are projected to 32 dimensions by PCA fitted on
the outer training set. Five independent maps are evaluated in every family:

1. fixed five-qubit transverse-field ring-Ising reservoir;
2. real orthogonal quadratic readout with the same 15 observables;
3. random Fourier features with 15 cosine features.

Each branch uses a standardized linear residual head. Classification heads use
a logistic offset model with L2 1; regression heads use ridge with alpha 10.
All families receive the same input, readout dimension, map count, and head
capacity.

The reservoir Hamiltonian and all random maps are built with seeds
20261101 through 20261105. Branch predictions are averaged in residual space
over the five maps. This avoids giving either family an extra
validation-selection opportunity.

## Gate

For each endpoint, base, split seed, and family, a scalar weight is selected
from `{0, 0.25, 0.5, 0.75, 1}` by validation performance. Ties choose the
smaller weight. The test labels never enter fitting, map generation, or gating.

## Metrics and inference

The official endpoint metric is AUROC, AUPRC, MAE, or Spearman correlation.
Effects are direction-normalized so positive values always favour the first
method.

The primary comparison is QRC against the real orthogonal quadratic map at
weight 1. Secondary comparisons use random Fourier features, no residual, and
the same validation gate.

An additional complementarity analysis allows QRC and the real-orthogonal
branch to enter together. Two scalar weights are selected on validation from a
5-by-5 grid; ties prefer the smaller total correction and then the smaller QRC
weight.

Finite-shot sensitivity uses eight pre-specified endpoints: BBB, hERG, Caco2,
LD50, PPBR, DILI, CYP2D6 inhibition, and VDss. Each Pauli expectation is
independently sampled from a binomial model with 1,024, 4,096, or 16,384 shots.
The residual heads are retrained on the sampled features. This analysis does
not model hardware decoherence, gate error, readout crosstalk, or a hardware
measurement schedule.

The low-data curve uses the same eight endpoints and target training fractions
of 5%, 10%, 20%, 40%, and 100%. A minimum effective subset of 96 observations
is used so that three scaffold OOF folds remain estimable on the smallest
endpoints. Actual training counts are recorded for every split and fraction.
The complete training row uses the main exact-simulation result rather than
retraining it.

External validation uses the ToxTree hERG test collection (Zenodo 5807719),
with the provider's binary cutoff PIC50 >= 4.5, and the B3DB BBB classification
dataset. Canonical non-isomeric molecule identities present in either TDC
train/validation or test are removed before evaluation. ESOL is excluded
because 1,097 of its 1,115 unique molecules overlap TDC AqSolDB, leaving only
18 non-overlapping records. External labels are not used for training or gate
selection.

The saved binary-model predictions are also ranked against available continuous
labels without retraining: hERG PIC50 for all 293 retained molecules and B3DB
logBB for 613 of the 2,317 retained molecules. The continuous B3DB subset is
strongly enriched for BBB-positive compounds (86.8%). Three contrasts are
reported per base and task: gated QRC versus gated orthogonal, joint
QRC-plus-orthogonal versus gated orthogonal, and gated QRC versus the base.
Inference uses the same scaffold-clustered paired bootstrap and permutation
implementation, and Holm correction spans all 12 exploratory comparisons. This
analysis measures whether a classifier preserves continuous ranking
information; it is not an independently trained regression cohort and is not
used for model selection.

External binary diagnostics decompose gated QRC minus base, gated orthogonal
minus base, and gated QRC minus gated orthogonal. AUPRC, Brier score, log loss,
calibration slope, calibration intercept, and quintile calibration curves are
computed from the existing five-seed predictions. These diagnostics are
descriptive and do not replace the prespecified external AUROC family.

Chemical-space visualization uses Morgan radius-2 1024-bit fingerprints on a
random set of 3,000 unique TDC molecules, 500 B3DB molecules, and all 293 hERG
molecules. The projection is 20-component truncated SVD, standardization, and
two-component PCA. Molecular weight, cLogP, and TPSA are calculated with RDKit
for all unique TDC, hERG, and B3DB molecules.

An independent continuous-regression sensitivity study uses the ToxTree hERG
`PIC50` labels. Canonical identities overlapping TDC hERG are removed. The
source-defined Dev-set is split 87.5/12.5 by Bemis-Murcko scaffold into 6,895
training and 985 validation molecules. From the source Test-set we remove both
TDC-overlapping identities and any scaffold represented in the external
Dev-set or in the TDC hERG archive, leaving 214 test molecules in 155
scaffolds. Model and branch hyperparameters remain fixed to the TDC protocol
and the external labels are not used for map or hyperparameter selection. Five
model seeds are evaluated; Spearman correlation on pIC50 is the primary metric
and MAE is secondary. Inference uses paired scaffold bootstrap/permutation and
Holm correction across all 12 metric/base/contrast tests. This cohort is
independent of TDC labels, but it is a supplementary external experiment rather
than part of the frozen 22-endpoint TDC benchmark.

Noise sensitivity adds a local single-qubit depolarizing model with p in
{0.001, 0.005, 0.010} and 4,096 shots. Symmetric depolarizing scales a Z
expectation by `lambda = 1 - 4p/3` and a ZZ expectation by `lambda^2`. Residual
heads are retrained on the noisy features. This is a controlled simulation and
does not model gate-specific error, readout crosstalk, leakage, or hardware
connectivity.

The bounded reservoir-family search compares five prespecified QRC parameter
settings against five real-orthogonal candidate groups. Each candidate is a
five-map ensemble. Selection uses TDC validation only, and the test set is used
only for final scoring. This gives the quantum and classical families the same
number of candidate ensembles.

Confidence intervals use 1,000 paired bootstrap resamples of official test
scaffolds. Main tests use 1,999 paired scaffold permutations and Holm correction
across the 22 endpoints. Exploratory equivalence tests use 0.01 absolute units
for AUROC, AUPRC, and Spearman, and 2% of the base MAE for MAE. These margins
are practical benchmark tolerances, not clinical decision thresholds.
TOST sensitivity repeats equivalence classification at absolute margins 0.005,
0.01, and 0.02 and MAE-relative margins 1%, 2%, and 4%, with Holm correction
across the 22 endpoints within each base and margin.

