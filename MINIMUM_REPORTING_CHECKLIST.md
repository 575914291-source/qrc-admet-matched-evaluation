# Minimum reporting checklist for matched QML molecular benchmarks

This checklist distills the evaluation protocol used in the associated manuscript. It applies to fixed-circuit or fixed-feature quantum machine-learning benchmarks for molecular property prediction.

1. Report the same molecular input representation, readout dimension, and residual-head parameterization for quantum and classical branches.
2. Match the number of random maps or candidate feature families, including any ensembling budget.
3. Compare against at least two strong classical bases that differ in representation and model family.
4. Use scaffold-grouped train/validation/test evaluation and state whether exact identities or Murcko scaffolds are disjoint.
5. Account for repeated splits and random maps with paired cluster-level uncertainty estimates.
6. Correct endpoint-level tests for multiplicity and interpret superiority separately from practical equivalence.
7. Report external cohorts from at least two independent sources and state label-definition and prevalence differences.
8. Report unfavorable endpoints, zero/searched gate weights, failed positive controls, and all sensitivity analyses rather than a selected endpoint subset.
9. Separate exact state-vector or matrix results, circuit-level simulations, and physical-hardware evidence.
10. Release split-level predictions and enough code/configuration to audit every reported metric.

The manuscript also reports a descriptive chemical-space audit, continuous-label transfer, and an independent pIC50 regression. These are boundary analyses, not replacement criteria for the ten core requirements.
