from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from src.config import GATE_WEIGHTS, MAP_SEEDS, RESULTS_ROOT, SPLIT_SEEDS, TASK_BY_NAME
from src.data import SMILES_TO_SCAFFOLD, load_task_frames, make_split, write_json
from src.modeling import (
    branch_predictions,
    fit_base_predictions,
    latent_features,
    predictions_from_delta,
    score,
    select_gate,
)
from src.run_benchmark import _task_matrix, log, run_path


FRACTIONS = (0.05, 0.10, 0.20, 0.40, 1.00)
MIN_SUBSET = 96
PANEL = (
    "bbb_martins",
    "herg",
    "caco2_wang",
    "ld50_zhu",
    "ppbr_az",
    "dili",
    "cyp2d6_veith",
    "vdss_lombardo",
)
OUTPUT_ROOT = RESULTS_ROOT / "low_data"


def output_path(base: str, task: str, split_seed: int):
    return OUTPUT_ROOT / base / task / f"split_{split_seed}.json"


def _subset_indices(
    truth: np.ndarray,
    kind: str,
    requested_fraction: float,
    seed: int,
) -> np.ndarray:
    count = len(truth)
    target = min(count, max(MIN_SUBSET, int(round(count * requested_fraction))))
    if target >= count:
        return np.arange(count, dtype=np.int64)
    positions = np.arange(count)
    rng = seed
    if kind == "classification":
        labels = truth.astype(int)
    else:
        quantiles = np.quantile(truth, [0.2, 0.4, 0.6, 0.8])
        labels = np.digitize(truth, quantiles)
    counts = np.bincount(labels)
    if np.min(counts[counts > 0]) < 2:
        return np.sort(
            np.random.default_rng(rng).choice(positions, size=target, replace=False)
        )
    selected, _ = train_test_split(
        positions,
        train_size=target,
        random_state=rng,
        stratify=labels,
    )
    return np.sort(selected.astype(np.int64))


def _combined_gate(
    kind: str,
    metric: str,
    truth: np.ndarray,
    base: np.ndarray,
    qrc_delta: np.ndarray,
    orth_delta: np.ndarray,
) -> tuple[float, float]:
    sign = -1.0 if metric == "MAE" else 1.0
    best = (0.0, 0.0, -np.inf, 0.0)
    for orth_weight in GATE_WEIGHTS:
        for qrc_weight in GATE_WEIGHTS:
            prediction = predictions_from_delta(
                kind,
                base,
                qrc_weight * qrc_delta + orth_weight * orth_delta,
                1.0,
            )
            value = sign * score(metric, truth, prediction)
            total = qrc_weight + orth_weight
            if value > best[2] + 1e-12 or (
                np.isclose(value, best[2], atol=1e-12, rtol=0)
                and (total < best[3] or (total == best[3] and qrc_weight < best[0]))
            ):
                best = (qrc_weight, orth_weight, value, total)
    return best[0], best[1]


def run_job(payload: tuple[str, str, int]) -> dict[str, object]:
    base, task, split_seed = payload
    destination = output_path(base, task, split_seed)
    if destination.exists():
        return json.loads(destination.read_text(encoding="utf-8"))

    spec = TASK_BY_NAME[task]
    frames = load_task_frames(task)
    train, valid, test = make_split(frames, split_seed)
    full_n = len(train)
    full_x = _task_matrix(base, train)
    full_y = train["Y"].to_numpy(dtype=float)
    valid_x_full = _task_matrix(base, valid)
    test_x_full = _task_matrix(base, test)
    valid_y = valid["Y"].to_numpy(dtype=float)
    test_y = test["Y"].to_numpy(dtype=float)
    results = []

    for fraction_index, fraction in enumerate(FRACTIONS):
        subset = _subset_indices(
            full_y,
            spec.kind,
            fraction,
            20270100 + split_seed * 100 + fraction_index,
        )
        subset_y = full_y[subset]
        subset_x = full_x[subset]
        metadata = {}
        if fraction == 1.0:
            full_metadata = json.loads(
                run_path(base, task, split_seed).with_suffix(".json").read_text(
                    encoding="utf-8"
                )
            )
            for method in (
                "qrc_ungated",
                "real_orthogonal_ungated",
                "random_fourier_ungated",
                "qrc_gated",
                "real_orthogonal_gated",
                "random_fourier_gated",
                "qrc_plus_orth",
            ):
                metadata[method] = full_metadata["method_scores"][method]["test"]
            metadata["gate_qrc"] = full_metadata["gate_weights"]["qrc"]
            metadata["gate_orth"] = full_metadata["gate_weights"]["real_orthogonal"]
            metadata["gate_qrc_plus_orth"] = full_metadata["gate_weights"]["combination_qrc"]
            metadata["gate_orth_in_joint"] = full_metadata["gate_weights"][
                "combination_orthogonal"
            ]
        else:
            subset_groups = np.asarray(
                [
                    SMILES_TO_SCAFFOLD[smiles]
                    for smiles in train.iloc[subset]["Drug"].astype(str)
                ]
            )
            base_output = fit_base_predictions(
                base=base,
                task=task,
                kind=spec.kind,
                train_x=subset_x,
                train_y=subset_y,
                valid_x=valid_x_full,
                test_x=test_x_full,
                groups=subset_groups,
                seed=split_seed,
                threads=4,
            )
            train_latent, valid_latent, test_latent = latent_features(
                subset_x, valid_x_full, test_x_full, seed=split_seed
            )
            branches, _ = branch_predictions(
                kind=spec.kind,
                train_latent=train_latent,
                valid_latent=valid_latent,
                test_latent=test_latent,
                train_y=subset_y,
                oof_base=base_output["oof"],
            )
            for family in (
                "qrc",
                "real_orthogonal",
                "random_fourier",
            ):
                metadata[f"{family}_ungated"] = score(
                    spec.metric,
                    test_y,
                    predictions_from_delta(
                        spec.kind,
                        base_output["test"],
                        branches[family]["test_delta"],
                        1.0,
                    ),
                )
                gate, _ = select_gate(
                    spec.kind,
                    spec.metric,
                    valid_y,
                    base_output["valid"],
                    branches[family]["valid_delta"],
                )
                metadata[f"{family}_gated"] = score(
                    spec.metric,
                    test_y,
                    predictions_from_delta(
                        spec.kind,
                        base_output["test"],
                        branches[family]["test_delta"],
                        gate,
                    ),
                )
                if family == "qrc":
                    metadata["gate_qrc"] = gate
                elif family == "real_orthogonal":
                    metadata["gate_orth"] = gate
            qrc_weight, orth_weight = _combined_gate(
                spec.kind,
                spec.metric,
                valid_y,
                base_output["valid"],
                branches["qrc"]["valid_delta"],
                branches["real_orthogonal"]["valid_delta"],
            )
            metadata["qrc_plus_orth"] = score(
                spec.metric,
                test_y,
                predictions_from_delta(
                    spec.kind,
                    base_output["test"],
                    qrc_weight * branches["qrc"]["test_delta"]
                    + orth_weight * branches["real_orthogonal"]["test_delta"],
                    1.0,
                ),
            )
            metadata["gate_qrc_plus_orth"] = qrc_weight
            metadata["gate_orth_in_joint"] = orth_weight

        result = {
            "base": base,
            "task": task,
            "metric": spec.metric,
            "kind": spec.kind,
            "split_seed": split_seed,
            "target_fraction": fraction,
            "n_train": int(len(subset)),
            "full_train_n": int(full_n),
            "effective_fraction": float(len(subset) / full_n),
            **metadata,
        }
        direction = -1.0 if spec.metric == "MAE" else 1.0
        result["qrc_minus_orth_ungated"] = direction * (
            result["qrc_ungated"] - result["real_orthogonal_ungated"]
        )
        result["qrc_minus_orth_gated"] = direction * (
            result["qrc_gated"] - result["real_orthogonal_gated"]
        )
        results.append(result)

    payload_result = {
        "base": base,
        "task": task,
        "split_seed": split_seed,
        "results": results,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    write_json(destination, payload_result)
    return payload_result


def summarize() -> None:
    rows = []
    for path in sorted(OUTPUT_ROOT.glob("*/*/split_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows.extend(payload["results"])
    if not rows:
        raise RuntimeError("No low-data results found")
    frame = pd.DataFrame(rows)
    frame.to_csv(
        OUTPUT_ROOT / "metrics_by_seed.csv",
        index=False,
        encoding="utf-8-sig",
    )
    aggregate = (
        frame.groupby(
            ["base", "task", "metric", "target_fraction", "n_train"],
            as_index=False,
        )
        .agg(
            qrc_ungated=("qrc_ungated", "mean"),
            orth_ungated=("real_orthogonal_ungated", "mean"),
            qrc_gated=("qrc_gated", "mean"),
            orth_gated=("real_orthogonal_gated", "mean"),
            qrc_minus_orth_ungated=("qrc_minus_orth_ungated", "mean"),
            qrc_minus_orth_gated=("qrc_minus_orth_gated", "mean"),
            qrc_gate_mean=("gate_qrc", "mean"),
        )
    )
    counts = (
        aggregate.groupby(["base", "target_fraction"], as_index=False)
        .agg(
            endpoints=("task", "nunique"),
            qrc_better_ungated=("qrc_minus_orth_ungated", lambda x: (x > 0).sum()),
            qrc_worse_ungated=("qrc_minus_orth_ungated", lambda x: (x < 0).sum()),
            qrc_better_gated=("qrc_minus_orth_gated", lambda x: (x > 0).sum()),
            qrc_worse_gated=("qrc_minus_orth_gated", lambda x: (x < 0).sum()),
        )
    )
    aggregate.to_csv(
        OUTPUT_ROOT / "endpoint_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    counts.to_csv(
        OUTPUT_ROOT / "direction_counts.csv",
        index=False,
        encoding="utf-8-sig",
    )
    print(counts.to_string(index=False))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args()
    if not args.summarize_only:
        jobs = [
            (base, task, seed)
            for base in ("extra_trees", "catboost")
            for task in PANEL
            for seed in SPLIT_SEEDS
        ]
        start = time.time()
        completed = 0
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(run_job, job): job for job in jobs}
            for future in as_completed(futures):
                payload = future.result()
                completed += 1
                log(
                    f"{completed}/{len(jobs)} low-data "
                    f"{payload['base']} {payload['task']} seed={payload['split_seed']}"
                )
        log(f"low-data jobs finished in {time.time() - start:.1f}s")
    summarize()
    return 0


if __name__ == "__main__":
    sys.exit(main())

