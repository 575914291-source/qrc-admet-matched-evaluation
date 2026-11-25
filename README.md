# QRC-ADMET matched evaluation

Code and locked result artefacts for the study **Matched Evaluation of Fixed
Quantum Reservoir Residuals on TDC ADMET with Random Realizations and Strong
Baselines**.

Repository: <https://github.com/575914291-source/qrc-admet-matched-evaluation>

Frozen submission snapshot:
<https://github.com/575914291-source/qrc-admet-matched-evaluation/releases/tag/v1.2.0>

The study tests whether a fixed five-qubit quantum reservoir adds predictive
information beyond equal-input, equal-capacity classical nonlinear maps on the
22 official TDC ADMET endpoints. It includes two classical bases, five
scaffold-level train/validation splits, five independent random maps per
family, endpoint-level validation gating, multiple-testing correction,
equivalence analysis, finite-shot and depolarizing-noise sensitivity checks,
an external hERG cohort, an external B3DB blood-brain-barrier cohort, and a
descriptive chemical-space audit. A separate exploratory analysis ranks the
binary-model outputs against continuous pIC50 and logBB labels available in
those external sources; it is explicitly not treated as an independently
trained regression cohort.

## What is included

- Official TDC archive and the exact files used for evaluation.
- Corrected MapLight feature-building code and source-licence attribution.
- Five scaffold train/validation splits per endpoint.
- QRC, real-orthogonal quadratic, and random Fourier residual branches.
- All split-level predictions, metrics, audit checks, and statistical scripts.
- External-data preparation, exact-overlap removal, scaffold overlap, and
  nearest-neighbour similarity audits.
- Scaffold-clustered continuous-label rank-transfer analysis with Holm
  correction across all exploratory contrasts.
- Four main figures covering study design, chemical space, external
  decomposition/calibration, and endpoint-level primary effects.
- Submission-ready Chinese and English manuscripts and supplementary figures.

The 473 MB dense MapLight feature cache is intentionally excluded from Git.
`src.build_features` rebuilds it from the official TDC archive. Split-level
`.npz` predictions are retained so reported results can be audited without
rerunning model training.

## Environment

The tested environment is Python 3.11 with the versions in
[`requirements.txt`](requirements.txt). A minimal setup is:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On Linux or macOS, activate with `source .venv/bin/activate`.

## Verify the committed results

From the repository root:

```powershell
python -m unittest discover -s tests -v
python -m src.audit_runs
python -m src.audit_finite_shot
python -m src.audit_low_data
python -m src.audit_external
python -m src.analyze_continuous_transfer
python -m src.analyze_chemical_space
python -m src.analyze_external_diagnostics
python -m src.analyze_tost_sensitivity
python -m src.report_external_regression
python -m src.audit_external_regression
python -m src.make_manuscript_assets
python -m src.build_design_figure
python -m src.build_extended_tables
python -m src.build_extended_figures
python -m src.build_jc_submission
python -m src.audit_noise
python -m src.audit_tuned_qrc
python -m src.domain_audit
python -m src.package_submission
python -m src.update_delivery_checksums
```

These commands verify 220 primary endpoint runs, 80 finite-shot files (240
results), 80 low-data files (400 fraction results), 20 external runs, 80 noise
files (240 results), 80 bounded-family-search runs, 10 independent continuous
regression runs, the chemical-space audit, and the continuous-label transfer
audit. They require the released result artefacts but not the dense feature
cache.

## Reproduce from raw data

```powershell
python -m src.build_features --workers 4
python -m src.run_benchmark prepare
python -m src.run_benchmark run --workers 4 --threads 4
python -m src.audit_runs
python -m src.run_benchmark report
python -m src.run_finite_shot --workers 4
python -m src.audit_finite_shot
python -m src.run_low_data --workers 4
python -m src.audit_low_data
python -m src.run_external_validation --workers 3
python -m src.report_external
python -m src.audit_external
python -m src.analyze_continuous_transfer
python -m src.analyze_chemical_space
python -m src.analyze_external_diagnostics
python -m src.analyze_tost_sensitivity
python -m src.run_external_regression --bases extra_trees catboost --seeds 1 2 3 4 5
python -m src.report_external_regression
python -m src.audit_external_regression
python -m src.run_noise --workers 4
python -m src.audit_noise
python -m src.run_tuned_qrc --workers 4
python -m src.report_tuned_qrc
python -m src.audit_tuned_qrc
python -m src.domain_audit
python -m src.make_manuscript_assets
python -m src.build_design_figure
python -m src.build_extended_tables
python -m src.build_extended_figures
python -m src.update_paper
python -m src.update_paper_en
python -m src.build_supplement
python -m src.build_jc_submission
python -m src.package_submission
python -m src.update_delivery_checksums
```

Every stage is resumable. Existing split files are skipped unless the relevant
runner receives `--overwrite`.

## Main code map

- `PROTOCOL.md`: frozen data, split, model, gating, and inference decisions.
- `src/data.py`: official TDC loading, checksums, feature-cache validation, and
  scaffold split logic.
- `src/build_features.py`: rebuilds the corrected MapLight feature cache.
- `src/reservoir.py`: exact five-qubit state-vector readouts, finite-shot
  sampling, depolarizing attenuation, and classical controls.
- `src/modeling.py`: base models, scaffold out-of-fold offsets, residual heads,
  gating, and predictions.
- `src/run_benchmark.py`: resumable endpoint-by-split primary experiment.
- `src/report.py`: metrics, paired inference, Holm correction, TOST, tables,
  and figures.
- `src/run_external_validation.py`: external hERG and B3DB evaluation.
- `src/analyze_continuous_transfer.py`: exploratory rank transfer against
  available external pIC50 and logBB labels.
- `src/run_external_regression.py`: scaffold-disjoint ToxTree pIC50 regression
  with fixed TDC model hyperparameters.
- `src/report_external_regression.py` and
  `src/audit_external_regression.py`: paired inference and integrity checks for
  the continuous external cohort.
- `src/domain_audit.py`: exact overlap, Murcko-scaffold overlap,
  nearest-neighbour similarity, and descriptive subgroup audit.
- `src/analyze_chemical_space.py`: RDKit descriptor distributions and
  fingerprint projection for the study cohorts.
- `src/analyze_external_diagnostics.py`: effect decomposition, AUPRC, Brier,
  log loss, and calibration for the released external predictions.
- `src/analyze_tost_sensitivity.py`: TOST counts under tight, primary, and wide
  equivalence margins.
- `src/build_extended_tables.py` and `src/build_extended_figures.py`: manuscript
  tables and the added publication figures.
- `src/build_design_figure.py`: study-design schematic.
- `src/build_jc_submission.py`: journal-formatted manuscript, additional file,
  separate figure files, and cover-letter draft for Journal of Cheminformatics.
- `src/audit_*.py`: independent checks of the released result artefacts.
- `templates/source_manuscript.docx`: source document used by the manuscript
  generator, retained so the submitted DOCX can be rebuilt portably.

## Data provenance and licences

- TDC ADMET archive: Harvard Dataverse file `4426004`, SHA-256
  `bd0005246cb6f1672333c28ad202112a8bf071ab65d847848715030308faf1f1`.
- hERG external collection: Zenodo record `5807719`, CC BY 4.0.
- B3DB: CC0 1.0; the provider licence is retained with the data.
- MapLight reference implementation: retained in `third_party/` under its MIT
  licence.

See [`DATA_LICENSES.md`](DATA_LICENSES.md) and the provenance files under
[`data/`](data/) before redistributing derived files.

## Journal submission

The Journal of Cheminformatics-formatted manuscript, additional file, separate
figures, and cover-letter draft are generated by
`python -m src.build_jc_submission`. Remaining author-specific actions and the
Zenodo DOI workflow are listed in
[`JCI_SUBMISSION_CHECKLIST.md`](JCI_SUBMISSION_CHECKLIST.md) and
[`ZENODO_DOI_CHECKLIST.md`](ZENODO_DOI_CHECKLIST.md).

## Figure generation

The study-design figure was initially laid out with the
`academic-figures` workflow from Scientific Agent Skills and is regenerated in
this repository by `src/build_design_figure.py`. The remaining figures are
generated by the local Matplotlib scripts listed above.

> Kassis T, Agarwal V, He Y, Patel D, Brueckner A M. Scientific Agent Skills:
> A Library of Procedural Knowledge for Research Agents. arXiv:2609.00065,
> 2026. <https://arxiv.org/abs/2609.00065>

## Reproduction contract

The public official test sets are reused across model comparisons and are not
prospective validation cohorts. The reported inference is paired by test
scaffold. Exact simulation is used deliberately to isolate circuit
expressivity; finite-shot and depolarizing analyses are sensitivity checks,
not physical-hardware validation.

The continuous-label analysis ranks outputs from models trained on binary TDC
labels. Its hERG component covers the full 293-molecule external cohort, while
logBB is available for only 613 of 2,317 B3DB molecules and is strongly
class-enriched. It is exploratory and cannot replace a regression model trained
and evaluated on an independent continuous endpoint.

The central conclusion is bounded to the tested five-qubit amplitude encoding,
fixed Hamiltonian reservoir, 15 Pauli readouts, linear residual head, and exact
state-vector simulation. It is not a general claim about every quantum machine
learning architecture.

## Licence

Original code and documentation are released under the MIT License. Data and
third-party components retain their source licences.
