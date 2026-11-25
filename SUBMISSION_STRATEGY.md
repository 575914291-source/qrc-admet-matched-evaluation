# JCAMD submission strategy

## Target

Primary target: **Journal of Computer-Aided Molecular Design (JCAMD)**,
Springer.

The manuscript is positioned as a reproducible, matched-control evaluation of
quantum molecular features for computer-aided molecular design. It is not
framed as a general test of whether quantum machine learning can work for
ADMET.

## Why the fit is credible

- JCAMD regularly publishes validation, benchmarking, and reanalysis papers.
- Robinson, Glen, and Lee previously used JCAMD to show that evaluation design
  can change conclusions in bioactivity-model comparisons.
- The manuscript contributes a prespecified workflow: matched candidate budgets,
  five random maps per family, two classical bases, scaffold-level inference,
  Holm correction, TOST interpretation, independent-source validation, and a
  released reproduction package.
- The result is deliberately bounded to five-qubit amplitude encoding, a fixed
  Hamiltonian reservoir, 15 Pauli readouts, a linear residual head, and exact
  state-vector simulation.

## Reviewer-facing framing

The strongest contribution statement is:

> A multi-base, matched-control audit found no robust cross-endpoint or
> cross-source incremental value for the tested fixed quantum-reservoir
> residuals. A local hERG signal and BBB negative transfer delimit the
> conclusion and motivate a reusable evaluation protocol for future QML-ADMET
> studies.

Do not describe QRC as globally inferior. Use the precise statement that the
tested system showed no robust transferable increment.

## Pre-submission status

- English manuscript and PDF are generated and layout-checked.
- Supplementary Material and PDF are generated.
- Four main figures cover design, chemical space, external decomposition and
  calibration, and endpoint-level primary effects.
- External AUPRC, Brier, log-loss, calibration, TOST sensitivity, and an
  independent continuous pIC50 regression are included as boundary analyses.
- Known-QRC, known-classical, and null calibration show that the matched
  evaluation recovers expected signals while keeping null false-positive rates
  near 5%.
- Selection-aware map comparisons, matched-effect decomposition, effective-rank
  and CKA diagnostics, and nearest-TDC source gradients delimit the local
  hERG signal.
- Full split-level predictions, statistical tables, audits, figures, and data
  provenance are included in the reproduction archive.
- Public code repository:
  <https://github.com/575914291-source/qrc-admet-matched-evaluation>
- Frozen code and result release:
  <https://github.com/575914291-source/qrc-admet-matched-evaluation/releases/tag/v1.5.1>
- CI checks include unit tests and independent result audits.

## Remaining author-supplied metadata

Before submission, insert:

- full author names, affiliations, ORCID identifiers, and corresponding author;
- acknowledgements and funding statement;
- author contributions and competing-interest declaration;
- any required CRediT taxonomy;
- final reference-formatting pass against the live JCAMD template;
- confirmation in the submission system that the subscription route is used
  and no mandatory APC is selected.

## Fee position

The journal is hybrid/subscription; the open-access APC is optional. A
subscription-route submission should avoid that APC, but page, colour, and
overlength charges must be checked in the live submission system before final
submission.

## Files to upload

1. `Matched_Evaluation_Fixed_Quantum_Reservoir_TDC_ADMET.docx`
2. `Matched_Evaluation_Fixed_Quantum_Reservoir_TDC_ADMET.pdf`
3. `Supplementary_Material_JCAMD.docx`
4. `Supplementary_Material_JCAMD.pdf`
5. `补充材料_qrc_admet_代码与结果_最终.zip`
6. `COVER_LETTER.md` converted to the journal's required format
7. Cover letter and highlights pasted into the submission form if requested

Use the GitHub link for the continuously versioned code and the ZIP for the
frozen submission snapshot.
