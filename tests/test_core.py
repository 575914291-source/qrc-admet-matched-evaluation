from __future__ import annotations

import unittest
import json

import numpy as np
import pandas as pd

from src.config import GATE_WEIGHTS, RESULTS_ROOT
from src.data import load_task_frames, make_split
from src.modeling import logit
from src.fast_metrics import metric_value as fast_metric
from src.reservoir import (
    qrc_readouts,
    quadratic_features,
    random_fourier_features,
    real_orthogonal_readouts,
    depolarized_qrc_features,
    shot_sampled_qrc_features,
)


class ReservoirTests(unittest.TestCase):
    def test_readout_shapes_and_symmetry(self) -> None:
        latent = np.random.default_rng(7).normal(size=(11, 32))
        for readout in (qrc_readouts(3), real_orthogonal_readouts(3)):
            self.assertEqual(readout.matrices.shape, (15, 32, 32))
            self.assertTrue(
                np.allclose(readout.matrices, np.swapaxes(readout.matrices, 1, 2))
            )
            features = quadratic_features(latent, readout)
            self.assertEqual(features.shape, (11, 15))
            self.assertTrue(np.isfinite(features).all())
        self.assertEqual(random_fourier_features(latent, 5).shape, (11, 15))

    def test_zero_latent_uses_computational_basis(self) -> None:
        latent = np.zeros((2, 32))
        qrc = quadratic_features(latent, qrc_readouts(9))
        orth = quadratic_features(latent, real_orthogonal_readouts(9))
        self.assertTrue(np.isfinite(qrc).all())
        self.assertTrue(np.isfinite(orth).all())
        readout = qrc_readouts(9)
        self.assertIsNotNone(readout.hamiltonian)
        self.assertTrue(np.allclose(readout.hamiltonian, readout.hamiltonian.conj().T))

    def test_finite_shot_features_converge(self) -> None:
        latent = np.random.default_rng(12).normal(size=(20, 32))
        readout = qrc_readouts(4)
        ideal = quadratic_features(latent, readout)
        sampled = shot_sampled_qrc_features(
            latent, readout, shots=200_000, seed=13
        )
        self.assertTrue(np.max(np.abs(ideal - sampled)) < 0.02)

    def test_depolarizing_readout_scaling(self) -> None:
        latent = np.random.default_rng(15).normal(size=(20, 32))
        readout = qrc_readouts(6)
        ideal = quadratic_features(latent, readout)
        unchanged = depolarized_qrc_features(latent, readout, 0.0)
        noisy = depolarized_qrc_features(latent, readout, 0.01)
        self.assertTrue(np.allclose(ideal, unchanged))
        self.assertTrue(np.all(np.abs(noisy[:, :5]) <= np.abs(ideal[:, :5]) + 1e-12))
        self.assertTrue(np.all(np.abs(noisy[:, 5:]) <= np.abs(ideal[:, 5:]) + 1e-12))


class DataTests(unittest.TestCase):
    def test_official_row_counts_and_disjoint_scaffolds(self) -> None:
        frames = load_task_frames("ames")
        self.assertEqual(len(frames.train_val), 5821)
        self.assertEqual(len(frames.test), 1457)
        train, valid, test = make_split(frames, 1)
        self.assertGreater(len(train), 0)
        self.assertGreater(len(valid), 0)
        self.assertEqual(len(test), 1457)


class ModelingTests(unittest.TestCase):
    def test_logit_bounds(self) -> None:
        values = logit(np.asarray([0.0, 0.5, 1.0]))
        self.assertTrue(np.isfinite(values).all())
        self.assertAlmostEqual(values[1], 0.0)

    def test_gate_grid(self) -> None:
        self.assertEqual(GATE_WEIGHTS, (0.0, 0.25, 0.5, 0.75, 1.0))

    def test_fast_metrics_against_sklearn(self) -> None:
        from sklearn.metrics import (
            average_precision_score,
            mean_absolute_error,
            roc_auc_score,
        )
        from scipy.stats import spearmanr

        rng = np.random.default_rng(91)
        truth_binary = rng.integers(0, 2, size=500)
        truth_regression = rng.normal(size=500)
        prediction = rng.normal(size=500)
        self.assertAlmostEqual(
            fast_metric("AUROC", truth_binary, prediction),
            roc_auc_score(truth_binary, prediction),
            places=12,
        )
        self.assertAlmostEqual(
            fast_metric("AUPRC", truth_binary, prediction),
            average_precision_score(truth_binary, prediction),
            places=12,
        )
        self.assertAlmostEqual(
            fast_metric("MAE", truth_regression, prediction),
            mean_absolute_error(truth_regression, prediction),
            places=12,
        )
        self.assertAlmostEqual(
            fast_metric("Spearman", truth_regression, prediction),
            spearmanr(truth_regression, prediction).statistic,
            places=12,
        )


class ContinuousTransferTests(unittest.TestCase):
    def test_exploratory_contrasts_complete(self) -> None:
        root = RESULTS_ROOT / "external_continuous"
        comparisons = pd.read_csv(root / "comparisons.csv")
        self.assertEqual(len(comparisons), 12)
        self.assertEqual(
            set(comparisons["task"]), {"herg", "bbb_martins"}
        )
        self.assertEqual(
            set(comparisons["base"]), {"extra_trees", "catboost"}
        )
        self.assertTrue(
            set(comparisons["continuous_label"]) == {"PIC50", "logBB"}
        )
        self.assertTrue(
            (
                (comparisons["ci_low"] <= comparisons["effect_spearman"])
                & (comparisons["effect_spearman"] <= comparisons["ci_high"])
            ).all()
        )

    def test_continuous_transfer_audit_states_scope(self) -> None:
        audit = json.loads(
            (RESULTS_ROOT / "external_continuous" / "audit.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(audit["status"], "passed")
        self.assertEqual(
            audit["analysis_type"],
            "exploratory_continuous_label_ranking_transfer",
        )
        self.assertEqual(audit["tasks"]["herg"]["continuous_available"], 293)
        self.assertEqual(
            audit["tasks"]["bbb_martins"]["continuous_available"], 613
        )
        self.assertIn(
            "not an independently trained regression cohort",
            audit["interpretation_limit"],
        )

    def test_external_regression_split_is_scaffold_disjoint(self) -> None:
        from src.run_external_regression import prepare_regression_frames

        train, valid, test = prepare_regression_frames()
        self.assertEqual((len(train), len(valid), len(test)), (6895, 985, 214))
        self.assertEqual(test["scaffold"].nunique(), 155)
        self.assertFalse(
            set(train["canonical_smiles"]) & set(valid["canonical_smiles"])
        )
        self.assertFalse(
            set(train["canonical_smiles"]) & set(test["canonical_smiles"])
        )
        self.assertFalse(set(valid["canonical_smiles"]) & set(test["canonical_smiles"]))
        self.assertFalse(set(train["scaffold"]) & set(valid["scaffold"]))
        self.assertFalse(set(train["scaffold"]) & set(test["scaffold"]))
        self.assertFalse(set(valid["scaffold"]) & set(test["scaffold"]))


if __name__ == "__main__":
    unittest.main()

