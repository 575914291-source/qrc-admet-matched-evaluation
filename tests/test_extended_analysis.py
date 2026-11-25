from __future__ import annotations

import json
import unittest
from pathlib import Path

import pandas as pd
from docx import Document


ROOT = Path(__file__).resolve().parents[1]
TABLE_ROOT = ROOT / "results" / "manuscript" / "tables"
FIGURE_ROOT = ROOT / "results" / "manuscript" / "figures"


class ExtendedAnalysisTests(unittest.TestCase):
    def test_endpoint_and_prior_tables_are_complete(self):
        endpoint = pd.read_csv(TABLE_ROOT / "endpoint_characteristics.csv")
        hierarchy = pd.read_csv(TABLE_ROOT / "analysis_hierarchy.csv")
        prior = pd.read_csv(TABLE_ROOT / "prior_qml_comparison.csv")
        self.assertEqual(len(endpoint), 22)
        self.assertEqual(endpoint.endpoint.nunique(), 22)
        self.assertEqual(len(hierarchy), 7)
        self.assertEqual(len(prior), 7)

    def test_external_diagnostics_cover_all_cohorts(self):
        summary = pd.read_csv(
            ROOT / "results" / "external_diagnostics" / "summary.csv"
        )
        calibration = pd.read_csv(
            ROOT / "results" / "external_diagnostics" / "calibration_metrics.csv"
        )
        self.assertEqual(len(summary), 48)
        self.assertEqual(len(calibration), 8)
        self.assertEqual(set(summary.task), {"herg", "bbb_martins"})
        self.assertTrue(
            ((calibration.calibration_slope > 0) & (calibration.calibration_slope < 2)).all()
        )

    def test_tost_and_external_regression_are_complete(self):
        tost = pd.read_csv(
            ROOT / "results" / "report" / "tost_sensitivity_summary.csv"
        )
        regression = pd.read_csv(
            ROOT / "results" / "external_regression" / "comparisons.csv"
        )
        self.assertEqual(len(tost), 6)
        self.assertEqual(len(regression), 12)
        self.assertEqual(regression.n_test.nunique(), 1)
        self.assertEqual(int(regression.n_test.iloc[0]), 214)

    def test_main_figures_exist(self):
        expected = {
            "figure1_design.png",
            "figure2_chemical_space.png",
            "figure3_external_diagnostics.png",
            "figure4_primary_effects.png",
            "figureS4_external_regression.png",
            "figureS5_circuit_noise.png",
        }
        actual = {path.name for path in FIGURE_ROOT.glob("*.png")}
        self.assertTrue(expected.issubset(actual))

    def test_jc_submission_package_is_formatted(self):
        root = ROOT / "outputs" / "JCAMD_Submission"
        expected = {
            "Manuscript.docx",
            "Additional_file_1.pdf",
            "Figure_1.pdf",
            "Figure_2.pdf",
            "Figure_3.pdf",
            "Figure_4.pdf",
            "Cover_Letter_Draft.docx",
        }
        self.assertTrue(expected.issubset({path.name for path in root.iterdir()}))
        document = Document(root / "Manuscript.docx")
        self.assertTrue(document.sections[0]._sectPr.xpath("./w:lnNumType"))
        self.assertGreaterEqual(
            document.styles["Normal"].paragraph_format.line_spacing,
            1.9,
        )
        shaded = sum(
            1
            for table in document.tables
            for row in table.rows
            for cell in row.cells
            if cell._tc.xpath("./w:tcPr/w:shd")
        )
        self.assertEqual(shaded, 0)
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        self.assertIn("Availability of data and materials", text)
        self.assertIn("Additional file 1", text)
        self.assertNotIn("[Author", text)

    def test_circuit_level_noise_results_are_complete(self):
        summary = pd.read_csv(
            ROOT / "results" / "circuit_level_noise" / "summary.csv"
        )
        self.assertEqual(len(summary), 32)
        self.assertEqual(summary.task.nunique(), 8)
        self.assertEqual(
            set(summary.profile),
            {"ideal_circuit", "noisy_low", "noisy_medium", "noisy_high"},
        )
        ideal = summary[summary.profile == "ideal_circuit"]
        self.assertTrue((ideal.spearman > 0.9995).all())
        high = summary[summary.profile == "noisy_high"]
        self.assertTrue((high.signal_slope < 0.5).all())
        audit = json.loads(
            (
                ROOT
                / "results"
                / "audit"
                / "circuit_level_noise_audit.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(audit["status"], "passed")

    def test_calibration_and_attribution_are_complete(self):
        calibration = pd.read_csv(
            ROOT / "results" / "calibration" / "summary.csv",
            keep_default_na=False,
            na_values=[""],
        )
        self.assertEqual(len(calibration), 6)
        self.assertTrue(
            (
                calibration.loc[
                    calibration.scenario == "qrc_signal",
                    "qrc_minus_orthogonal_mean",
                ]
                > 0
            ).all()
        )
        self.assertTrue(
            (
                calibration.loc[
                    calibration.scenario == "classical_signal",
                    "qrc_minus_orthogonal_mean",
                ]
                < 0
            ).all()
        )
        null = calibration[calibration.scenario == "null"]
        self.assertTrue((null.null_false_positive_rate <= 0.05).all())

        effects = pd.read_csv(
            ROOT / "results" / "effect_decomposition" / "effects_by_split.csv"
        )
        self.assertEqual(len(effects), 220)
        self.assertLess(float(effects.identity_error.abs().max()), 1e-10)

        selection = json.loads(
            (
                ROOT / "results" / "map_selection" / "summary.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(selection["runs"], 220)

        capacity = json.loads(
            (
                ROOT / "results" / "capacity_diagnostics" / "summary.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(capacity["runs"], 3300)

        gradient = pd.read_csv(
            ROOT / "results" / "source_gradient" / "summary.csv"
        )
        self.assertEqual(len(gradient), 24)
        audit = json.loads(
            (
                ROOT
                / "results"
                / "audit"
                / "extended_evaluation_audit.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(audit["status"], "passed")

    def test_manuscript_audit_passed(self):
        audit = json.loads(
            (ROOT / "outputs" / "MANUSCRIPT_QA.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(audit["status"], "passed")
        self.assertEqual(audit["main"]["tables"], 6)
        self.assertEqual(audit["main"]["figures"], 4)
        self.assertEqual(audit["supplement"]["tables"], 17)
        self.assertEqual(audit["supplement"]["figures"], 10)


if __name__ == "__main__":
    unittest.main()
