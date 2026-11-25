# External validation data

## hERG

- Source: ToxTree hERG dataset, Zenodo record 5807719.
- URL: `https://doi.org/10.5281/zenodo.5807719`
- License: CC BY 4.0.
- Original split: 8,380 development molecules and 499 test molecules.
- Endpoint adaptation: `PIC50 >= 4.5` indicates hERG blockade, following the
  binary cutoff described in the ToxTree manuscript.
- After canonical deduplication and removal of exact TDC hERG overlaps: 293
  external molecules.

## Blood-brain barrier

- Source: B3DB classification dataset.
- URL: `https://github.com/theochem/B3DB`
- License: CC0 1.0, retained in `B3DB_LICENSE.txt`.
- Labels: provider-supplied `BBB+` and `BBB-`.
- After canonical deduplication and removal of exact TDC BBB overlap: 2,317
  external molecules.

## Excluded solubility audit

DeepChem's Delaney/ESOL table was inspected but not used. Of 1,115 unique
canonical molecules, 1,097 overlap TDC AqSolDB; only 18 non-overlapping
molecules remain. This is too small and not chemically independent enough for
meaningful external validation.

