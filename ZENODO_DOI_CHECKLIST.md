# Zenodo DOI checklist

The Journal of Computer-Aided Molecular Design submission includes an archived
software identifier for the code and outputs supporting the paper. The GitHub
tag is useful, but a Zenodo DOI is the stronger persistent identifier to place
in the submitted "Availability of data and materials" section.

## Preferred GitHub integration

1. Sign in to Zenodo with the GitHub account that owns the repository.
2. Open Zenodo account settings and enable the repository
   `575914291-source/qrc-admet-matched-evaluation`.
3. Create a new GitHub release only after the final author list, funding
   statement, and paper version are frozen.
4. Zenodo will archive the release and issue a DOI.
5. Add the DOI badge and DOI URL to `README.md`, `CITATION.cff`, and the paper's
   availability statement.
6. Create a new release only for substantive new versions; avoid repeatedly
   replacing an existing version.

## Manual upload alternative

Upload `qrc_admet_reproduction_v1.5.1.zip` as a software deposit with:

- Title: QRC-ADMET matched evaluation
- Upload type: Software
- Version: 1.5.1
- Licence: MIT for original software
- Creators: full author names and ORCID identifiers
- Keywords: ADMET; quantum reservoir computing; matched controls;
  reproducibility; Therapeutics Data Commons; negative results
- Related identifier: the GitHub repository and corresponding release

## Text to insert after a DOI is assigned

> Project name: QRC-ADMET matched evaluation. Project home:
> https://github.com/575914291-source/qrc-admet-matched-evaluation. Archived
> version: v1.5.1, DOI: https://doi.org/10.5281/zenodo.XXXXXXX. Operating
> systems: Windows, Linux, or macOS. Programming language: Python 3.11.
> Dependencies: requirements.txt. Licence: MIT for original code and
> documentation; upstream data and third-party licences are listed in
> DATA_LICENSES.md. No additional restriction applies to non-academic use of
> the original code.

Do not insert a fabricated DOI. The placeholder `zenodo.XXXXXXX` must be
replaced only after Zenodo issues the record.
