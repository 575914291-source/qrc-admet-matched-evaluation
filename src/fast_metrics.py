from __future__ import annotations

import math

import numpy as np
from numba import njit, prange


@njit(cache=True)
def _average_ranks(values: np.ndarray) -> np.ndarray:
    count = values.shape[0]
    order = np.argsort(values)
    ranks = np.empty(count, dtype=np.float64)
    start = 0
    while start < count:
        end = start + 1
        current = values[order[start]]
        while end < count and values[order[end]] == current:
            end += 1
        average = (start + 1 + end) / 2.0
        for position in range(start, end):
            ranks[order[position]] = average
        start = end
    return ranks


@njit(cache=True)
def auc(truth: np.ndarray, prediction: np.ndarray) -> float:
    ranks = _average_ranks(prediction)
    positives = 0
    positive_rank_sum = 0.0
    for index in range(truth.shape[0]):
        if truth[index] > 0.5:
            positives += 1
            positive_rank_sum += ranks[index]
    negatives = truth.shape[0] - positives
    if positives == 0 or negatives == 0:
        return np.nan
    return (
        positive_rank_sum - positives * (positives + 1) / 2.0
    ) / (positives * negatives)


@njit(cache=True)
def average_precision(truth: np.ndarray, prediction: np.ndarray) -> float:
    positives = 0
    for index in range(truth.shape[0]):
        if truth[index] > 0.5:
            positives += 1
    if positives == 0:
        return np.nan
    order = np.argsort(-prediction)
    true_positive = 0
    false_positive = 0
    previous_true_positive = 0
    result = 0.0
    start = 0
    count = prediction.shape[0]
    while start < count:
        end = start + 1
        current = prediction[order[start]]
        while end < count and prediction[order[end]] == current:
            end += 1
        for position in range(start, end):
            index = order[position]
            if truth[index] > 0.5:
                true_positive += 1
            else:
                false_positive += 1
        precision = true_positive / (true_positive + false_positive)
        result += precision * (
            (true_positive - previous_true_positive) / positives
        )
        previous_true_positive = true_positive
        start = end
    return result


@njit(cache=True)
def spearman(truth: np.ndarray, prediction: np.ndarray) -> float:
    truth_rank = _average_ranks(truth)
    prediction_rank = _average_ranks(prediction)
    truth_mean = 0.0
    prediction_mean = 0.0
    count = truth.shape[0]
    for index in range(count):
        truth_mean += truth_rank[index]
        prediction_mean += prediction_rank[index]
    truth_mean /= count
    prediction_mean /= count
    covariance = 0.0
    truth_variance = 0.0
    prediction_variance = 0.0
    for index in range(count):
        truth_delta = truth_rank[index] - truth_mean
        prediction_delta = prediction_rank[index] - prediction_mean
        covariance += truth_delta * prediction_delta
        truth_variance += truth_delta * truth_delta
        prediction_variance += prediction_delta * prediction_delta
    denominator = math.sqrt(truth_variance * prediction_variance)
    if denominator == 0.0:
        return np.nan
    return covariance / denominator


@njit(cache=True)
def mean_absolute_error(truth: np.ndarray, prediction: np.ndarray) -> float:
    result = 0.0
    for index in range(truth.shape[0]):
        result += abs(truth[index] - prediction[index])
    return result / truth.shape[0]


@njit(cache=True)
def _metric(metric_code: int, truth: np.ndarray, prediction: np.ndarray) -> float:
    if metric_code == 0:
        return auc(truth, prediction)
    if metric_code == 1:
        return average_precision(truth, prediction)
    if metric_code == 2:
        return spearman(truth, prediction)
    if metric_code == 3:
        return mean_absolute_error(truth, prediction)
    return np.nan


@njit(parallel=True, cache=True)
def bootstrap_effect_distribution(
    metric_code: int,
    truth: np.ndarray,
    method_predictions: np.ndarray,
    reference_predictions: np.ndarray,
    sample_indices: np.ndarray,
    sample_lengths: np.ndarray,
) -> np.ndarray:
    """Compute paired multi-seed effects for each bootstrap resample."""
    replicate_count = sample_indices.shape[0]
    seed_count = method_predictions.shape[1]
    result = np.empty(replicate_count, dtype=np.float64)
    for replicate in prange(replicate_count):
        length = sample_lengths[replicate]
        indices = sample_indices[replicate, :length]
        sampled_truth = truth[indices]
        total = 0.0
        for seed in range(seed_count):
            method_value = _metric(
                metric_code, sampled_truth, method_predictions[indices, seed]
            )
            reference_value = _metric(
                metric_code, sampled_truth, reference_predictions[indices, seed]
            )
            if metric_code == 3:
                total += reference_value - method_value
            else:
                total += method_value - reference_value
        result[replicate] = total / seed_count
    return result


@njit(parallel=True, cache=True)
def permutation_effect_distribution(
    metric_code: int,
    truth: np.ndarray,
    method_predictions: np.ndarray,
    reference_predictions: np.ndarray,
    row_flips: np.ndarray,
) -> np.ndarray:
    """Compute paired multi-seed effects under per-cluster label swaps."""
    replicate_count = row_flips.shape[0]
    seed_count = method_predictions.shape[1]
    sample_count = truth.shape[0]
    result = np.empty(replicate_count, dtype=np.float64)
    for replicate in prange(replicate_count):
        permuted_method = np.empty(
            (sample_count, seed_count), dtype=np.float64
        )
        permuted_reference = np.empty(
            (sample_count, seed_count), dtype=np.float64
        )
        for sample in range(sample_count):
            if row_flips[replicate, sample]:
                for seed in range(seed_count):
                    permuted_method[sample, seed] = reference_predictions[sample, seed]
                    permuted_reference[sample, seed] = method_predictions[sample, seed]
            else:
                for seed in range(seed_count):
                    permuted_method[sample, seed] = method_predictions[sample, seed]
                    permuted_reference[sample, seed] = reference_predictions[sample, seed]
        total = 0.0
        for seed in range(seed_count):
            method_value = _metric(
                metric_code, truth, permuted_method[:, seed]
            )
            reference_value = _metric(
                metric_code, truth, permuted_reference[:, seed]
            )
            if metric_code == 3:
                total += reference_value - method_value
            else:
                total += method_value - reference_value
        result[replicate] = total / seed_count
    return result


def metric_value(metric: str, truth: np.ndarray, prediction: np.ndarray) -> float:
    truth = np.ascontiguousarray(truth, dtype=np.float64)
    prediction = np.ascontiguousarray(prediction, dtype=np.float64)
    if metric == "AUROC":
        value = auc(truth, prediction)
    elif metric == "AUPRC":
        value = average_precision(truth, prediction)
    elif metric == "Spearman":
        value = spearman(truth, prediction)
    elif metric == "MAE":
        value = mean_absolute_error(truth, prediction)
    else:
        raise ValueError(metric)
    if not np.isfinite(value):
        raise ValueError(f"Undefined {metric}")
    return float(value)

