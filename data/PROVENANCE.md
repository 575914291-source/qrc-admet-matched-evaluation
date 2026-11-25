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

