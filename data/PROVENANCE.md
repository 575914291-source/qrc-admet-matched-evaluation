# Data provenance

## Primary evaluation data

- Source: Therapeutics Data Commons ADMET Group
- Archive provider: Harvard Dataverse
- File ID: 4426004
- URL: `https://dataverse.harvard.edu/api/access/datafile/4426004`
- SHA-256:
  `bd0005246cb6f1672333c28ad202112a8bf071ab65d847848715030308faf1f1`
- Official task directories: 22
- Official train+validation records: 65,430
- Official labelled test records: 16,379

The archive is retained in `data/archives/` and extracted under
`data/tdc_official/`. The five training/validation splits are generated from
`train_val.csv`; labels in `test.csv` are never used for fitting or selection.

## Molecular feature cache

The 46,202-molecule MapLight feature cache contains 2,563 features:
1,024 Morgan counts, 1,024 Avalon counts, 315 ErG values, and 200 RDKit
descriptors. It was regenerated with `int32` count conversion to correct an
`int8` overflow in the upstream implementation. The cache checksum and
molecule order are recorded in `data/cache/`.

The cache is label-free. No competition split files are used for the paper's
labels or evaluation.

## External validation sources

- hERG: Zenodo record `5807719`, CC BY 4.0. The upstream CRLF download used
  for the analysis has SHA-256
  `f028e0dbdc46fd587e3f75e296e06922387e3e5dc7288837d7e0da40ecbcc80b`.
  Git stores and distributes the same text with LF line endings under
  `data/external/hERG_Dataset.csv`; its canonical tracked hash is
  `cb031f5c230d992a1ec48d7ee46689dfee1a2667edfcba0e84ff9b2845e104cb`.
  The line-ending normalization does not change the parsed records.
- B3DB: CC0 1.0. The source table at
  `data/external/B3DB_classification.tsv` has SHA-256
  `47a160aea1551423ead2aab70b301fb1646aea03cf151fd614eb37c78fa55b82`.

The full hashes in the reproduction manifest refer to the Python-readable
tracked files. For hERG, the upstream-download and tracked-LF hashes are both
reported so that provenance remains verifiable across operating systems.

