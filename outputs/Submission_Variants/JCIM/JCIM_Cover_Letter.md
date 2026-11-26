# JCIM Cover Letter

Dear Editor,

We submit our manuscript, "Matched Evaluation of Fixed Quantum Reservoir Features for TDC ADMET Prediction: A Signal-Calibrated Benchmark with Random Realizations and Strong Baselines," for consideration as a research article in the Journal of Chemical Information and Modeling.

Quantum reservoir features are often presented as compact nonlinear molecular representations, but their incremental value relative to strong classical representations and matched nonlinear controls has not been evaluated consistently across public ADMET endpoints. The manuscript treats this as a chemical-information problem rather than a quantum-advantage demonstration.

The study makes three contributions. First, it positions the fixed five-qubit molecular feature map as the stateless QRC/QELM limit and shows that its Pauli readouts form a constrained real-quadratic family. Second, it compares this family with controls matched in input dimension, nominal readout dimension, fitted-parameter count, random-map budget, and tuning budget across all 22 official TDC ADMET endpoints, two classical bases, five scaffold splits, and multiple random maps. Third, it uses low-data, finite-shot, simulated-noise, bounded-family, external-transfer, continuous-label, independent pIC50, calibration, and chemical-space analyses to delimit the result.

No endpoint remained significantly better than its matched real-orthogonal control after Holm correction. Apparent gains on the weaker ExtraTrees base did not persist on MapLight-CatBoost. External transfer produced a source-local hERG candidate signal but significant negative transfer on B3DB BBB. Known-signal calibration recovered QRC-derived and classical targets in 150/150 and 149/150 simulations, respectively, while null false-positive rates were 4.7% and 2.0%.

These results are useful to JCIM readers because they provide a reusable matched-evaluation protocol for claims about quantum-derived molecular descriptors. The conclusion is explicitly limited to the tested five-qubit amplitude encoding, fixed Hamiltonian reservoir, 15 Pauli readouts, linear residual head, and exact simulation. The work does not claim that other encodings, trainable circuits, larger reservoirs, or physical hardware are ineffective.

The submission includes public-data provenance, split-level predictions, model configurations, audit scripts, and an open reproduction package. The versioned code and result index are available at https://github.com/575914291-source/qrc-admet-matched-evaluation.

Sincerely,

[Author names, affiliations, and corresponding author]
