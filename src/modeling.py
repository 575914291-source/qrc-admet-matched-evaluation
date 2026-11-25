from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, log_expit
from scipy.stats import spearmanr
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import average_precision_score, mean_absolute_error, roc_auc_score
from sklearn.model_selection import GroupKFold, StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import GATE_WEIGHTS, LOG_TARGET_TASKS, MAP_SEEDS
from src.reservoir import (
    diagnostics,
    qrc_readouts,
    quadratic_features,
    random_fourier_features,
    real_orthogonal_readouts,
)


@dataclass
class TargetTransformer:
    task: str
    offset: float
    scaler: StandardScaler

    @classmethod
    def fit(cls, task: str, y: np.ndarray) -> "TargetTransformer":
        offset = float(min(np.min(y), 0.0))
        values = np.asarray(y, dtype=float) - offset
        if task in LOG_TARGET_TASKS:
            values = np.log10(values + 1.0)
        scaler = StandardScaler().fit(values.reshape(-1, 1))
        return cls(task=task, offset=offset, scaler=scaler)

    def transform(self, y: np.ndarray) -> np.ndarray:
        values = np.asarray(y, dtype=float) - self.offset
        if self.task in LOG_TARGET_TASKS:
            values = np.log10(values + 1.0)
        return self.scaler.transform(values.reshape(-1, 1)).reshape(-1)

    def inverse_transform(self, y: np.ndarray) -> np.ndarray:
        values = self.scaler.inverse_transform(np.asarray(y).reshape(-1, 1)).reshape(-1)
        if self.task in LOG_TARGET_TASKS:
            values = np.power(10.0, values) - 1.0
        return values + self.offset


def score(metric: str, truth: np.ndarray, prediction: np.ndarray) -> float:
    if metric == "AUROC":
        return float(roc_auc_score(truth, prediction))
    if metric == "AUPRC":
        return float(average_precision_score(truth, prediction))
    if metric == "MAE":
        return float(mean_absolute_error(truth, prediction))
    if metric == "Spearman":
        value = spearmanr(truth, prediction).statistic
        if not np.isfinite(value):
            raise ValueError("Undefined Spearman correlation")
        return float(value)
    raise ValueError(f"Unsupported metric: {metric}")


def direction(metric: str) -> float:
    return -1.0 if metric == "MAE" else 1.0


def logit(probability: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(probability, dtype=float), 1e-7, 1.0 - 1e-7)
    return np.log(clipped) - np.log1p(-clipped)


def _inner_splits(
    kind: str,
    y: np.ndarray,
    groups: np.ndarray,
    seed: int,
) -> list[tuple[np.ndarray, np.ndarray]]:
    positions = np.arange(len(y))
    if kind == "classification":
        for offset in range(100):
            splitter = StratifiedGroupKFold(
                n_splits=3, shuffle=True, random_state=seed + offset
            )
            splits = list(splitter.split(positions, y, groups))
            if all(
                len(np.unique(y[train])) == 2 and len(np.unique(y[valid])) == 2
                for train, valid in splits
            ):
                return splits
        raise RuntimeError("Could not construct class-complete scaffold OOF folds")
    splitter = GroupKFold(n_splits=3)
    return list(splitter.split(positions, y, groups))


def _base_model(
    base: str,
    kind: str,
    seed: int,
    threads: int,
):
    if base == "extra_trees":
        from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor

        if kind == "classification":
            return ExtraTreesClassifier(
                n_estimators=128,
                min_samples_leaf=2,
                max_features="sqrt",
                random_state=seed,
                n_jobs=1,
            )
        return ExtraTreesRegressor(
            n_estimators=128,
            min_samples_leaf=2,
            max_features="sqrt",
            random_state=seed,
            n_jobs=1,
        )

    if base == "catboost":
        from catboost import CatBoostClassifier, CatBoostRegressor

        parameters = dict(
            iterations=240,
            depth=6,
            learning_rate=0.06,
            random_seed=seed,
            thread_count=threads,
            verbose=False,
            allow_writing_files=False,
        )
        if kind == "classification":
            return CatBoostClassifier(
                **parameters,
                loss_function="Logloss",
                boosting_type="Plain",
                border_count=128,
            )
        return CatBoostRegressor(**parameters, loss_function="MAE", task_type="CPU")
    raise ValueError(f"Unknown base model: {base}")


def _predict_base(model, kind: str, matrix: np.ndarray) -> np.ndarray:
    if kind == "classification":
        return np.asarray(model.predict_proba(matrix)[:, 1], dtype=float)
    return np.asarray(model.predict(matrix), dtype=float).reshape(-1)


def fit_base_predictions(
    base: str,
    task: str,
    kind: str,
    train_x: np.ndarray,
    train_y: np.ndarray,
    valid_x: np.ndarray,
    test_x: np.ndarray,
    groups: np.ndarray,
    seed: int,
    threads: int,
) -> dict[str, np.ndarray]:
    transformer = (
        TargetTransformer.fit(task, train_y)
        if kind == "regression" and base == "catboost"
        else None
    )
    fit_y = transformer.transform(train_y) if transformer is not None else train_y
    oof = np.full(len(train_y), np.nan, dtype=float)

    for fold, (fit_index, held_index) in enumerate(
        _inner_splits(kind, train_y, groups, seed)
    ):
        model = _base_model(base, kind, seed * 100 + fold, threads)
        model.fit(train_x[fit_index], fit_y[fit_index])
        prediction = _predict_base(model, kind, train_x[held_index])
        if transformer is not None:
            prediction = transformer.inverse_transform(prediction)
        oof[held_index] = prediction

    if not np.isfinite(oof).all():
        raise RuntimeError("OOF predictions contain missing or non-finite values")

    full_model = _base_model(base, kind, seed * 100 + 9, threads)
    full_model.fit(train_x, fit_y)
    valid_prediction = _predict_base(full_model, kind, valid_x)
    test_prediction = _predict_base(full_model, kind, test_x)
    if transformer is not None:
        valid_prediction = transformer.inverse_transform(valid_prediction)
        test_prediction = transformer.inverse_transform(test_prediction)
    return {
        "oof": oof,
        "valid": valid_prediction,
        "test": test_prediction,
    }


def latent_features(
    train_x: np.ndarray,
    valid_x: np.ndarray,
    test_x: np.ndarray,
    seed: int,
    n_components: int = 32,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    pipeline = make_pipeline(
        SimpleImputer(strategy="median", keep_empty_features=True),
        StandardScaler(),
        PCA(n_components=n_components, random_state=seed),
    )
    train_latent = pipeline.fit_transform(train_x)
    valid_latent = pipeline.transform(valid_x)
    test_latent = pipeline.transform(test_x)
    return train_latent, valid_latent, test_latent


class LogisticOffsetHead:
    def __init__(self, l2: float = 1.0) -> None:
        self.l2 = float(l2)
        self.coefficient: np.ndarray | None = None
        self.intercept: float = 0.0

    def fit(self, features: np.ndarray, truth: np.ndarray, offset: np.ndarray) -> None:
        x = np.asarray(features, dtype=float)
        y = np.asarray(truth, dtype=float)
        offset = np.asarray(offset, dtype=float)

        def objective(parameters: np.ndarray) -> tuple[float, np.ndarray]:
            coefficient = parameters[:-1]
            intercept = parameters[-1]
            logits = offset + x @ coefficient + intercept
            loss = (
                np.sum(np.logaddexp(0.0, logits) - y * logits)
                + 0.5 * self.l2 * coefficient @ coefficient
            )
            residual = expit(logits) - y
            gradient = np.empty_like(parameters)
            gradient[:-1] = x.T @ residual + self.l2 * coefficient
            gradient[-1] = np.sum(residual)
            return float(loss), gradient

        initial = np.zeros(x.shape[1] + 1, dtype=float)
        result = minimize(
            objective,
            initial,
            jac=True,
            method="L-BFGS-B",
            options={"maxiter": 1000, "ftol": 1e-10, "gtol": 1e-7},
        )
        if not result.success:
            raise RuntimeError(f"Logistic residual head failed: {result.message}")
        self.coefficient = result.x[:-1]
        self.intercept = float(result.x[-1])

    def predict_delta(self, features: np.ndarray) -> np.ndarray:
        if self.coefficient is None:
            raise RuntimeError("Head is not fitted")
        return np.asarray(features, dtype=float) @ self.coefficient + self.intercept


def _fit_branch_delta(
    kind: str,
    train_features: np.ndarray,
    valid_features: np.ndarray,
    test_features: np.ndarray,
    train_y: np.ndarray,
    train_offset: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    scaler = StandardScaler().fit(train_features)
    train_features = scaler.transform(train_features)
    valid_features = scaler.transform(valid_features)
    test_features = scaler.transform(test_features)
    if kind == "classification":
        head = LogisticOffsetHead(l2=1.0)
        head.fit(train_features, train_y, train_offset)
        return (
            head.predict_delta(valid_features),
            head.predict_delta(test_features),
        )
    target = train_y - train_offset
    head = Ridge(alpha=10.0, fit_intercept=True)
    head.fit(train_features, target)
    return head.predict(valid_features), head.predict(test_features)


def branch_predictions(
    kind: str,
    train_latent: np.ndarray,
    valid_latent: np.ndarray,
    test_latent: np.ndarray,
    train_y: np.ndarray,
    oof_base: np.ndarray,
) -> tuple[
    dict[str, dict[str, np.ndarray]],
    dict[str, list[dict[str, object]]],
]:
    offset = logit(oof_base) if kind == "classification" else oof_base
    valid_maps: dict[str, np.ndarray] = {}
    test_maps: dict[str, np.ndarray] = {}
    map_diagnostics: dict[str, list[dict[str, object]]] = {}

    for family in ("qrc", "real_orthogonal"):
        valid_values = []
        test_values = []
        map_diagnostics[family] = []
        for seed in MAP_SEEDS:
            readout = (
                qrc_readouts(seed)
                if family == "qrc"
                else real_orthogonal_readouts(seed)
            )
            train_features = quadratic_features(train_latent, readout)
            valid_features = quadratic_features(valid_latent, readout)
            test_features = quadratic_features(test_latent, readout)
            valid_delta, test_delta = _fit_branch_delta(
                kind,
                train_features,
                valid_features,
                test_features,
                train_y,
                offset,
            )
            valid_values.append(valid_delta)
            test_values.append(test_delta)
            map_diagnostics[family].append(diagnostics(readout))
        valid_maps[family] = np.column_stack(valid_values)
        test_maps[family] = np.column_stack(test_values)

    map_diagnostics["random_fourier"] = []
    valid_values = []
    test_values = []
    for seed in MAP_SEEDS:
        train_features = random_fourier_features(train_latent, seed)
        valid_features = random_fourier_features(valid_latent, seed)
        test_features = random_fourier_features(test_latent, seed)
        valid_delta, test_delta = _fit_branch_delta(
            kind,
            train_features,
            valid_features,
            test_features,
            train_y,
            offset,
        )
        valid_values.append(valid_delta)
        test_values.append(test_delta)
    valid_maps["random_fourier"] = np.column_stack(valid_values)
    test_maps["random_fourier"] = np.column_stack(test_values)

    output: dict[str, dict[str, np.ndarray]] = {}
    for family in valid_maps:
        output[family] = {
            "valid_delta_maps": valid_maps[family],
            "test_delta_maps": test_maps[family],
            "valid_delta": valid_maps[family].mean(axis=1),
            "test_delta": test_maps[family].mean(axis=1),
        }
    return output, map_diagnostics


def predictions_from_delta(
    kind: str, base_prediction: np.ndarray, delta: np.ndarray, alpha: float
) -> np.ndarray:
    if kind == "classification":
        return expit(logit(base_prediction) + alpha * delta)
    return base_prediction + alpha * delta


def select_gate(
    kind: str,
    metric: str,
    truth: np.ndarray,
    valid_base: np.ndarray,
    valid_delta: np.ndarray,
) -> tuple[float, float]:
    best_weight = 0.0
    best_value = -np.inf
    sign = direction(metric)
    for weight in GATE_WEIGHTS:
        prediction = predictions_from_delta(kind, valid_base, valid_delta, weight)
        value = sign * score(metric, truth, prediction)
        if value > best_value + 1e-12:
            best_value = value
            best_weight = float(weight)
    return best_weight, sign * best_value

