from __future__ import annotations

import hashlib
from pathlib import Path

from src.config import PROJECT_ROOT


OUTPUT_ROOT = PROJECT_ROOT / "outputs"
CHECKSUM_FILE = OUTPUT_ROOT / "交付文件SHA256.txt"
FILES = (
    "论文修订稿_v2_TDC完整实验.docx",
    "论文修订稿_v2_TDC完整实验.pdf",
    "Matched_Evaluation_Fixed_Quantum_Reservoir_TDC_ADMET.docx",
    "Matched_Evaluation_Fixed_Quantum_Reservoir_TDC_ADMET.pdf",
    "Supplementary_Material_JCAMD.docx",
    "Supplementary_Material_JCAMD.pdf",
    "JCheminformatics_Submission/Manuscript.docx",
    "JCheminformatics_Submission/Additional_file_1.pdf",
    "JCheminformatics_Submission/Figure_1.pdf",
    "JCheminformatics_Submission/Figure_2.pdf",
    "JCheminformatics_Submission/Figure_3.pdf",
    "JCheminformatics_Submission/Figure_4.pdf",
    "JCheminformatics_Submission/Cover_Letter_Draft.docx",
    "补充材料_qrc_admet_代码与结果_最终.zip",
    "补充材料_qrc_admet_代码与结果_最终.zip.sha256",
    "qrc_admet_reproduction_v1.2.0.zip",
    "qrc_admet_reproduction_v1.2.0.zip.sha256",
    "Supplementary_File_Hashes.csv",
    "实验结论摘要.md",
    "投稿可行性预审.md",
    "HIGHLIGHTS.md",
    "COVER_LETTER.md",
    "SUBMISSION_STRATEGY.md",
    "Figure1_Study_Design.pdf",
    "Figure2_Chemical_Space.pdf",
    "Figure3_External_Validation.pdf",
    "Figure4_Primary_Effects.pdf",
    "Supplementary_FigureS4_External_Regression.pdf",
    "补充图S1_低数据曲线.pdf",
    "补充图S2_外部端点效应.pdf",
    "补充图S3_模拟噪声敏感性.pdf",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    lines = []
    for name in FILES:
        path = OUTPUT_ROOT / name
        if not path.exists():
            raise FileNotFoundError(path)
        lines.append(f"{sha256(path)}  {name}")
    CHECKSUM_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(CHECKSUM_FILE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
