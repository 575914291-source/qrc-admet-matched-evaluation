from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = PROJECT_ROOT / "outputs"
OUTPUT_ZIP = OUTPUT_ROOT / "补充材料_qrc_admet_代码与结果_最终.zip"
VERSIONED_ZIP = OUTPUT_ROOT / "qrc_admet_reproduction_v1.3.0.zip"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def allowed(path: Path) -> bool:
    relative = path.relative_to(PROJECT_ROOT)
    text = relative.as_posix()
    stale_figures = {
        "results/manuscript/figures/forest_main.png",
        "results/manuscript/figures/forest_main.pdf",
        "results/manuscript/figures/figure4_external_diagnostics.png",
        "results/manuscript/figures/figure4_external_diagnostics.pdf",
    }
    if text in stale_figures:
        return False
    if text.startswith("outputs/JCheminformatics_Submission/"):
        return False
    if "__pycache__" in text or text.endswith(".pyc"):
        return False
    if text.endswith(".npy"):
        return False
    if text.startswith("outputs/") and text.endswith((".zip", ".sha256")):
        return False
    if text == "outputs/交付文件SHA256.txt":
        return False
    if text in {"data/cache/maplight.npy", "data/cache/morgan_512.npy"}:
        return False
    top_levels = {
        ".github",
        "src",
        "tests",
        "third_party",
        "templates",
        "results/report",
        "results/manuscript",
        "results/audit",
        "results/runs",
        "results/finite_shot",
        "results/low_data",
        "results/external_validation",
        "results/external_continuous",
        "results/external_diagnostics",
        "results/external_regression",
        "results/circuit_level_noise",
        "results/noise",
        "results/tuned_qrc",
        "results/combination",
        "results/domain_audit",
        "data/tdc_official",
        "data/archives",
        "data/external",
        "data/circuit_noise",
        "outputs",
    }
    if any(text == prefix or text.startswith(prefix + "/") for prefix in top_levels):
        return True
    return text in {
        "README.md",
        "PROTOCOL.md",
        "RESULTS.md",
        "PRE_SUBMISSION_REVIEW.md",
        "HIGHLIGHTS.md",
        "COVER_LETTER.md",
        "SUBMISSION_STRATEGY.md",
        "JCI_SUBMISSION_CHECKLIST.md",
        "ZENODO_DOI_CHECKLIST.md",
        "LICENSE",
        "DATA_LICENSES.md",
        "CITATION.cff",
        "requirements.txt",
        "requirements-qiskit.txt",
        "data/PROVENANCE.md",
        "data/cache/smiles.json",
        "data/cache/molecule_groups.json",
        "data/cache/maplight_complete.json",
        "data/cache/source_manifest.json",
    }


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    files = sorted(
        path
        for path in PROJECT_ROOT.rglob("*")
        if path.is_file() and allowed(path) and path != OUTPUT_ZIP
    )
    manifest = {
        "version": "1.3.0",
        "files": len(files),
        "source": "TDC ADMET Group / Harvard Dataverse file 4426004",
        "archive_sha256": sha256(
            PROJECT_ROOT
            / "data"
            / "archives"
            / "admet_group_4426004.zip"
        ),
        "manuscript": "论文修订稿_v2_TDC完整实验.docx",
        "repository": (
            "https://github.com/575914291-source/"
            "qrc-admet-matched-evaluation"
        ),
        "release": (
            "https://github.com/575914291-source/"
            "qrc-admet-matched-evaluation/releases/tag/v1.3.0"
        ),
    }
    manifest_bytes = (
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")

    with zipfile.ZipFile(
        OUTPUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in files:
            relative = path.relative_to(PROJECT_ROOT)
            archive.write(path, relative.as_posix())
        archive.writestr("SUBMISSION_MANIFEST.json", manifest_bytes)

    checksum = sha256(OUTPUT_ZIP)
    (OUTPUT_ZIP.with_suffix(".zip.sha256")).write_text(
        f"{checksum}  {OUTPUT_ZIP.name}\n", encoding="utf-8"
    )
    shutil.copy2(OUTPUT_ZIP, VERSIONED_ZIP)
    VERSIONED_ZIP.with_suffix(".zip.sha256").write_text(
        f"{checksum}  {VERSIONED_ZIP.name}\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "path": str(OUTPUT_ZIP),
                "files": len(files),
                "size": OUTPUT_ZIP.stat().st_size,
                "sha256": checksum,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

