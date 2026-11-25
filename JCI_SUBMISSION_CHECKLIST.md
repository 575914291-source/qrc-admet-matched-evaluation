# Journal of Cheminformatics submission checklist

The journal guidelines checked on 2026-11-25 require double-line spacing,
continuous line and page numbering, editable manuscript files, no manual page
breaks, unshaded tables, separate figure files, and a structured data/software
availability statement.

## Generate the formatting package

From the repository root:

```powershell
python -m src.build_jc_submission
```

The generated files are written to
`outputs/JCheminformatics_Submission/`:

- `Manuscript.docx`: editable submission manuscript with continuous line
  numbers, double-spaced body text, no manual page breaks, and unshaded tables.
- `Additional_file_1.pdf`: supplementary material, below the journal's 20 MB
  per-file limit.
- `Figure_1.pdf` through `Figure_4.pdf`: separate figure files, each below the
  10 MB per-file limit.
- `Cover_Letter_Draft.docx`: current cover letter converted to DOCX.

## Author information still required

- Full names and email addresses of every author.
- Affiliations and ORCID identifiers.
- Author contributions.
- Funding statement.
- Competing-interests statement.
- Confirmation that all authors approved submission.
- Name and date of the version being submitted.
- Any preferred or excluded reviewers.

## Data and software statement

The final "Availability of data and materials" section should provide:

- Project name: QRC-ADMET matched evaluation.
- Project home:
  https://github.com/575914291-source/qrc-admet-matched-evaluation
- Archived version identifier: GitHub release `v1.3.0` at
  https://github.com/575914291-source/qrc-admet-matched-evaluation/releases/tag/v1.3.0
- Operating systems: Windows, Linux, or macOS.
- Programming language: Python 3.11.
- Dependencies: `requirements.txt`.
- Licence: MIT for original code and documentation; upstream data and
  third-party terms are listed in `DATA_LICENSES.md`.
- Restrictions: none for the original code beyond the retained upstream data
  licences.

For a persistent DOI, connect the GitHub release to Zenodo and replace the
GitHub-only archived-version identifier with the resulting DOI before final
submission.

## Files to upload

1. `Manuscript.docx`.
2. `Additional_file_1.pdf`.
3. `Figure_1.pdf` to `Figure_4.pdf`.
4. Completed cover letter.

The journal permits a review PDF in addition to editable source files, but the
editable DOCX remains mandatory. The current 17-page typeset PDF is a review or
preprint version, not the journal-formatted manuscript.

## Final checks

- Remove every author-info placeholder.
- Confirm the archived version and URL resolve publicly.
- Confirm the additional file and every figure is cited in sequence.
- Confirm reference numbers and supplementary table/figure references.
- Run `python -m unittest discover -s tests -v`.
- Run the GitHub Actions workflow successfully.
