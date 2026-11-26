# QMI submission migration plan

Status: prepare only. Submit only after the JCIM decision and only after a
substantive QML-oriented rewrite.

## 1. Target identity

### Working title

Matched Benchmarking of Fixed Quantum Reservoir Features Against Classical
Quadratic Controls for Molecular Property Prediction

### Primary claim

Under a common numerical budget, a fixed five-qubit stateless quantum feature
map does not show a stable increment over matched real-quadratic controls on 22
ADMET endpoints, two classical bases, multiple random maps, and independent
molecular-source cohorts.

## 2. Section migration from the JCIM version

| JCIM section | QMI treatment |
|---|---|
| Title and abstract | Rebuild around QML benchmarking, matched controls, and readout limitations. Keep the same result numbers. |
| Introduction | Lead with QRC/QELM expressivity, data encodings, readout decodability, and matched evaluation. Move QSAR framing to the motivation. |
| Related work | Expand QRC/QELM, Pauli-transfer, readout orientation, equivalence testing, and QML reporting. Compress ADMET model history. |
| Data and splits | Keep TDC, scaffold splits, and leakage controls, but move endpoint-by-endpoint chemistry detail to supplementary material. |
| Quantum feature section | Move earlier and expand the finite-shot, fixed-Hamiltonian, 15-readout, and stateless-QELM definition. |
| Classical controls | Keep Morgan-ExtraTrees and MapLight-CatBoost, but present them as strong prediction pipelines attached to matched feature families. |
| Primary results | Lead with QRC versus matched quadratic maps across endpoints and bases. Summarize the 22-endpoint table in one figure and keep full tables in supplement. |
| Gating and extra analyses | Retain as robustness tests, not as the main narrative. |
| External cohorts | Present as distribution-shift probes; reduce chemical-space description in the main text. |
| Discussion | Center on feature geometry, effective rank, readout access, and simulation boundaries. Move detailed chemistry interpretation to supplement. |
| Limitations | Keep five-qubit/exact-simulation/readout boundaries prominent. Do not claim general failure of QRC or QML. |
| Conclusion | Frame the contribution as a QML benchmark and reproducible evaluation protocol for molecular tasks. |

## 3. Abstract blueprint

1. One-sentence problem: QRC gains are sensitive to classical tuning,
   randomness, readout choice, and task structure.
2. Design: fixed stateless five-qubit feature map, matched quadratic and
   Fourier controls, two bases, five scaffold splits, five maps.
3. Main result: no stable quantum increment across 22 ADMET endpoints.
4. Robustness: gating, low data, finite shots, noise, family search, and
   external transfer.
5. Interpretation: source-local hERG signal and negative BBB transfer do not
   support a general advantage.
6. Contribution and boundary: quantum benchmark and evaluation protocol, limited
   to the tested amplitude encoding, Pauli readout, and simulation.

## 4. Material to retain

- All 45 references and the verified citation scope.
- The exact 22-endpoint counts and all effect sizes.
- The Proposition 1 quadratic representation.
- The distinction between nominal readout dimension and task-relevant
  decodability.
- Five-map and five-split randomness controls.
- Known-signal calibration and null false-positive results.
- Qiskit/Aer readout-fidelity results and finite-shot analyses.

## 5. Material to move or compress

- Long TDC endpoint descriptions: keep only enough to interpret the 22-task
  scope; move the rest to supplement.
- Detailed chemical-space summary: retain one compact paragraph and cite the
  supplementary audit.
- QSAR-practice guidance: condense into the final Discussion paragraph.

## 6. Recommended strengthening without rerunning the full benchmark

Priority 1: an interaction-free or product-state Hamiltonian ablation on the
eight representative endpoints, keeping the same PCA input, five random maps,
15 Pauli readouts, and linear head. This distinguishes entanglement or
interaction effects from generic nonlinear feature expansion.

Priority 2: a readout-orientation sensitivity analysis on a small endpoint
subset. Reuse existing feature generation where possible and state clearly that
the full readout search was not performed.

If neither analysis is possible, keep the present readout limitation and do not
claim that the Hamiltonian or entanglement was isolated.

## 7. Reuse and compliance

Figures, tables, and predictions may be reused because they describe the same
study. Text, title, abstract, and discussion must be substantially rewritten for
the QMI readership. Do not submit while JCIM is under review and disclose prior
review history where the submission system requests it.
