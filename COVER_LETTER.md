Dear Editor,

We submit our manuscript, "Matched Evaluation of Fixed Quantum Reservoir Residuals
on TDC ADMET with Random Realizations and Strong Baselines," for consideration
as a research article.

Quantum reservoir features have been proposed as compact nonlinear molecular
representations, but their incremental value over carefully matched classical
maps remains unclear. The study makes three contributions. First, it derives
that fixed five-qubit QRC with diagonal Pauli readouts and a linear head is a
constrained real quadratic feature map. Second, it evaluates this map on all 22
official TDC ADMET endpoints against equal-capacity real-orthogonal and random
Fourier controls, using five scaffold splits and two classical bases. Third, it
reports joint gating, low-data, finite-shot, simulated-depolarizing, bounded
reservoir-family search, and external hERG/B3DB BBB analyses under a fixed test
protocol.

The revised manuscript now includes four main figures: the matched evaluation
design, chemical-space and applicability-domain context, external effect
decomposition with calibration, and the 22-endpoint primary-effect forest.
External AUPRC, Brier score, log loss, multiplicity sensitivity, and an
independent continuous pIC50 regression are reported as boundary checks rather
than as evidence of a general quantum advantage.

The revised manuscript now also includes a known-signal benchmark calibration:
the matched workflow recovered synthetic QRC-specific and classical quadratic
targets in at least 99.3% of simulations, while null false-positive rates were
2.0-4.7%. Selection-aware map comparison, matched-effect decomposition,
effective-rank and CKA diagnostics, and nearest-TDC similarity gradients are
provided as supplementary analyses.

No endpoint remained significantly better than the matched controls after Holm
correction. Apparent gains on the weaker ExtraTrees base did not persist on the
stronger MapLight-CatBoost base. External validation revealed a source-dependent
positive signal on hERG but significant negative transfer on BBB. These results
provide a reproducible boundary for claims about fixed quantum reservoir features
in ADMET prediction and offer a useful matched-control protocol for future QML
studies. An additional exploratory continuous-label analysis found a
CatBoost-specific hERG ranking signal before, but not after, conservative
multiplicity correction; it did not replicate on B3DB logBB and is reported
explicitly as a ranking-transfer analysis rather than an independent regression
cohort. A separate scaffold-disjoint ToxTree pIC50 regression also produced no
significant QRC advantage after correction across the complete exploratory
comparison family. An explicit Qiskit/Aer circuit audit added transpiled gate
depolarization and readout-flip errors; rank preservation remained high, but
readout amplitudes contracted substantially and no hardware-robustness claim is
made.

The manuscript includes public-data provenance, a full experiment audit,
split-level predictions, and a reproduction package. Versioned code and result
indexes are available at
https://github.com/575914291-source/qrc-admet-matched-evaluation. It has not
been published or submitted concurrently elsewhere. We believe it fits the
journal's interest in computational methods, reproducible benchmarks, and
rigorous evaluation in drug discovery.

Sincerely,

[Author names and affiliations]

