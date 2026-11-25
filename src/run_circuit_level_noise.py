from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import PauliEvolutionGate, StatePreparation
from qiskit.quantum_info import Operator, SparsePauliOp
from qiskit.synthesis import LieTrotter
from qiskit_aer import AerSimulator
from qiskit_aer.library import SaveProbabilities
from qiskit_aer.noise import NoiseModel, depolarizing_error

from src.config import CIRCUIT_TASKS, PROJECT_ROOT, RESULTS_ROOT
from src.reservoir import quadratic_features, qrc_readouts


OUTPUT_ROOT = RESULTS_ROOT / "circuit_level_noise"
PREPARED_ROOT = PROJECT_ROOT / "data" / "circuit_noise" / "prepared"
TROTTER_REPS = 8
EVOLUTION_TIME = 0.5
NOISE_PROFILES = {
    "low": {
        "one_qubit_depolarizing": 0.0005,
        "two_qubit_depolarizing": 0.005,
        "readout_flip": 0.005,
    },
    "medium": {
        "one_qubit_depolarizing": 0.001,
        "two_qubit_depolarizing": 0.010,
        "readout_flip": 0.010,
    },
    "high": {
        "one_qubit_depolarizing": 0.002,
        "two_qubit_depolarizing": 0.020,
        "readout_flip": 0.020,
    },
}


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _noise_model(profile: dict[str, float]) -> NoiseModel:
    model = NoiseModel()
    one_qubit = depolarizing_error(profile["one_qubit_depolarizing"], 1)
    two_qubit = depolarizing_error(profile["two_qubit_depolarizing"], 2)
    model.add_all_qubit_quantum_error(
        one_qubit,
        [
            "u1",
            "u2",
            "u3",
            "rx",
            "ry",
            "rz",
            "sx",
            "x",
        ],
    )
    model.add_all_qubit_quantum_error(two_qubit, ["cx", "rzz"])
    return model


def _readout_values(probabilities: np.ndarray) -> np.ndarray:
    probabilities = np.asarray(probabilities, dtype=float)
    probabilities = probabilities / probabilities.sum()
    basis = np.arange(1 << 5, dtype=np.int64)
    values = []
    for qubit in range(5):
        bits = (basis >> (4 - qubit)) & 1
        values.append(float(probabilities @ (1 - 2 * bits)))
    for first in range(5):
        bits_first = (basis >> (4 - first)) & 1
        for second in range(first + 1, 5):
            bits_second = (basis >> (4 - second)) & 1
            values.append(
                float(
                    probabilities
                    @ ((1 - 2 * bits_first) * (1 - 2 * bits_second))
                )
            )
    return np.asarray(values, dtype=float)


def _pauli_hamiltonian(readout) -> SparsePauliOp:
    if readout.hamiltonian is None:
        raise RuntimeError("QRC readout has no Hamiltonian")
    return SparsePauliOp.from_operator(Operator(readout.hamiltonian))


def _circuit(
    latent: np.ndarray, hamiltonian: SparsePauliOp
) -> QuantumCircuit:
    circuit = QuantumCircuit(5)
    circuit.append(StatePreparation(latent, normalize=True), range(5))
    circuit.append(
        PauliEvolutionGate(
            hamiltonian,
            time=EVOLUTION_TIME,
            synthesis=LieTrotter(reps=TROTTER_REPS),
        ),
        range(5),
    )
    circuit.append(SaveProbabilities(5, label="probs"), range(5))
    return circuit


def _run_probabilities(
    backend: AerSimulator, circuits: list[QuantumCircuit]
) -> list[np.ndarray]:
    result = backend.run(circuits, shots=1).result()
    return [
        np.real(result.data(index)["probs"]).astype(float)
        for index in range(len(circuits))
    ]


def run_task(
    task: str,
    max_states: int | None,
    profiles: tuple[str, ...],
) -> dict[str, object]:
    prepared = np.load(PREPARED_ROOT / f"{task}.npz", allow_pickle=False)
    latent = prepared["latent"]
    if max_states is not None:
        latent = latent[:max_states]
    truth = prepared["y"][: len(latent)]

    ideal_backend = AerSimulator(
        method="statevector", seed_simulator=20261201
    )
    exact_maps = []
    ideal_maps = []
    noisy_maps = {
        profile: [] for profile in profiles
    }
    gate_records = []
    started = time.time()

    for map_index, seed in enumerate(
        (20261101, 20261102, 20261103, 20261104, 20261105)
    ):
        readout = qrc_readouts(seed)
        hamiltonian = _pauli_hamiltonian(readout)
        exact = quadratic_features(latent, readout)
        circuits = [
            transpile(
                _circuit(state, hamiltonian),
                backend=ideal_backend,
                optimization_level=1,
                seed_transpiler=seed,
            )
            for state in latent
        ]
        gate_records.append(
            {
                "map_seed": seed,
                "depth": max(circuit.depth() for circuit in circuits),
                "size": max(circuit.size() for circuit in circuits),
                "operation_counts": {
                    key: max(
                        sum(
                            circuit.count_ops().get(key, 0)
                            for circuit in circuits
                        )
                        // len(circuits),
                        0,
                    )
                    for key in ("cx", "u1", "u2", "u3", "rzz")
                },
            }
        )
        ideal = [
            _readout_values(probabilities)
            for probabilities in _run_probabilities(ideal_backend, circuits)
        ]
        exact_maps.append(exact)
        ideal_maps.append(np.asarray(ideal))

        for profile_name in profiles:
            profile = NOISE_PROFILES[profile_name]
            backend = AerSimulator(
                method="density_matrix",
                noise_model=_noise_model(profile),
                seed_simulator=seed,
            )
            values = []
            readout_scale = 1.0 - 2.0 * profile["readout_flip"]
            for probabilities in _run_probabilities(backend, circuits):
                features = _readout_values(probabilities)
                features[:5] *= readout_scale
                features[5:] *= readout_scale * readout_scale
                values.append(features)
            noisy_maps[profile_name].append(np.asarray(values))

    exact_array = np.asarray(exact_maps)
    ideal_array = np.asarray(ideal_maps)
    destination = OUTPUT_ROOT / f"{task}.npz"
    arrays = {
        "truth": truth,
        "exact": exact_array,
        "ideal_circuit": ideal_array,
        **{
            f"noisy_{profile}": np.asarray(noisy_maps[profile])
            for profile in profiles
        },
    }
    np.savez_compressed(destination, **arrays)
    metadata = {
        "task": task,
        "states": int(len(latent)),
        "maps": 5,
        "trotter_reps": TROTTER_REPS,
        "evolution_time": EVOLUTION_TIME,
        "profiles": {
            name: NOISE_PROFILES[name] for name in profiles
        },
        "ideal_circuit_rmse_to_exact": float(
            np.sqrt(np.mean((ideal_array - exact_array) ** 2))
        ),
        "ideal_circuit_max_error": float(
            np.max(np.abs(ideal_array - exact_array))
        ),
        "gate_records": gate_records,
        "elapsed_seconds": time.time() - started,
    }
    _write_json(destination.with_suffix(".json"), metadata)
    return metadata


def run(
    tasks: tuple[str, ...],
    max_states: int | None,
    profiles: tuple[str, ...],
) -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for task in tasks:
        metadata = run_task(task, max_states, profiles)
        print(json.dumps(metadata, indent=2), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", nargs="+", default=list(CIRCUIT_TASKS))
    parser.add_argument("--max-states", type=int)
    parser.add_argument(
        "--profiles",
        nargs="+",
        choices=tuple(NOISE_PROFILES),
        default=tuple(NOISE_PROFILES),
    )
    args = parser.parse_args()
    run(tuple(args.tasks), args.max_states, tuple(args.profiles))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
