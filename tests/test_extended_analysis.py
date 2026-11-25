from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd


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
        self.assertEqual(len(hierarchy), 6)
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
        }
        actual = {path.name for path in FIGURE_ROOT.glob("*.png")}
        self.assertTrue(expected.issubset(actual))


if __name__ == "__main__":
    unittest.main()
