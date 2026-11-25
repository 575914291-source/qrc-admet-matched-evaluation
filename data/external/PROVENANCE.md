# External validation data

## hERG

- Source: ToxTree hERG dataset, Zenodo record 5807719.
- URL: `https://doi.org/10.5281/zenodo.5807719`
- License: CC BY 4.0.
- Upstream CRLF download SHA-256:
  `f028e0dbdc46fd587e3f75e296e06922387e3e5dc7288837d7e0da40ecbcc80b`.
- Tracked LF-normalized SHA-256:
  `cb031f5c230d992a1ec48d7ee46689dfee1a2667edfcba0e84ff9b2845e104cb`.
- The line-ending normalization does not change parsed records.
- Original split: 8,380 development molecules and 499 test molecules.
- Endpoint adaptation: `PIC50 >= 4.5` indicates hERG blockade, following the
  binary cutoff described in the ToxTree manuscript.
- After canonical deduplication and removal of exact TDC hERG overlaps: 293
  external molecules.
- Supplementary continuous-regression study: source `Dev-set` molecules are
  used for training and validation after canonical deduplication and removal
  of exact TDC hERG overlaps. Source `Test-set` molecules are held out, with
  canonical TDC overlaps and scaffolds shared with the external `Dev-set`
  removed. Test scaffolds represented anywhere in the TDC hERG archive are
  removed as a stricter structural-independence check. Final counts are 6,895
  train, 985 validation, and 214 test molecules (155 test scaffolds). No
  external labels were used to tune the reservoir seeds, PCA dimension,
  residual-head penalties, or base-model hyperparameters.

## Blood-brain barrier

- Source: B3DB classification dataset.
- URL: `https://github.com/theochem/B3DB`
- License: CC0 1.0, retained in `B3DB_LICENSE.txt`.
- SHA-256:
  `47a160aea1551423ead2aab70b301fb1646aea03cf151fd614eb37c78fa55b82`.
- Labels: provider-supplied `BBB+` and `BBB-`.
- After canonical deduplication and removal of exact TDC BBB overlap: 2,317
  external molecules.

## Excluded solubility audit

DeepChem's Delaney/ESOL table was inspected but not used. Of 1,115 unique
canonical molecules, 1,097 overlap TDC AqSolDB; only 18 non-overlapping
molecules remain. This is too small and not chemically independent enough for
meaningful external validation.

