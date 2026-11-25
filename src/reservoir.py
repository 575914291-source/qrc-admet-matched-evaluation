from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import expm
from scipy.stats import ortho_group


@dataclass(frozen=True)
class ReadoutMap:
    name: str
    seed: int
    matrices: np.ndarray
    unitary: np.ndarray | None = None


def _pauli_operators(n_qubits: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    identity = np.eye(2, dtype=complex)
    x = np.asarray([[0, 1], [1, 0]], dtype=complex)
    z = np.asarray([[1, 0], [0, -1]], dtype=complex)
    operators = []
    for local in (identity, x, z):
        value = np.asarray([[1.0]], dtype=complex)
        for _ in range(n_qubits):
            value = np.kron(value, local)
        operators.append(value)
    return operators


def _single_qubit_operator(
    local_operator: np.ndarray, qubit: int, n_qubits: int
) -> np.ndarray:
    identity = np.eye(2, dtype=complex)
    value = np.asarray([[1.0]], dtype=complex)
    for current in range(n_qubits):
        value = np.kron(value, local_operator if current == qubit else identity)
    return value


def _observables(n_qubits: int) -> np.ndarray:
    z = np.asarray([[1, 0], [0, -1]], dtype=float)
    values = []
    for first in range(n_qubits):
        operator = _single_qubit_operator(z, first, n_qubits)
        values.append(np.real_if_close(operator).real)
    for first in range(n_qubits):
        for second in range(first + 1, n_qubits):
            operator = _single_qubit_operator(z, first, n_qubits) @ _single_qubit_operator(
                z, second, n_qubits
            )
            values.append(np.real_if_close(operator).real)
    return np.asarray(values, dtype=float)


def qrc_readouts(
    seed: int,
    n_qubits: int = 5,
    field_x: float = 0.4,
    field_z: float = 0.7,
    coupling: float = 0.25,
    evolution_time: float = 0.5,
) -> ReadoutMap:
    if n_qubits != 5:
        raise ValueError("The frozen paper protocol uses five qubits")
    rng = np.random.default_rng(seed)
    dimension = 1 << n_qubits
    pauli_x = np.asarray([[0, 1], [1, 0]], dtype=complex)
    pauli_z = np.asarray([[1, 0], [0, -1]], dtype=complex)

    hamiltonian = np.zeros((dimension, dimension), dtype=complex)
    for qubit in range(n_qubits):
        hamiltonian += (
            rng.normal() * field_x * _single_qubit_operator(pauli_x, qubit, n_qubits)
        )
        hamiltonian += (
            rng.normal() * field_z * _single_qubit_operator(pauli_z, qubit, n_qubits)
        )
    for qubit in range(n_qubits):
        other = (qubit + 1) % n_qubits
        strength = rng.normal() * coupling
        hamiltonian += strength * (
            _single_qubit_operator(pauli_z, qubit, n_qubits)
            @ _single_qubit_operator(pauli_z, other, n_qubits)
        )
    if not np.allclose(hamiltonian, hamiltonian.conj().T):
        raise RuntimeError("The reservoir Hamiltonian is not Hermitian")

    unitary = expm(-1j * evolution_time * hamiltonian)
    observables = _observables(n_qubits)
    matrices = np.real(
        np.einsum(
            "ca,jcd,db->jab",
            unitary.conj(),
            observables,
            unitary,
            optimize=True,
        )
    )
    matrices = 0.5 * (matrices + np.swapaxes(matrices, 1, 2))
    return ReadoutMap("qrc", seed, matrices, unitary=unitary)


def real_orthogonal_readouts(seed: int, n_qubits: int = 5) -> ReadoutMap:
    if n_qubits != 5:
        raise ValueError("The frozen paper protocol uses five qubits")
    dimension = 1 << n_qubits
    orthogonal = ortho_group.rvs(
        dimension, random_state=np.random.default_rng(seed)
    )
    observables = _observables(n_qubits)
    matrices = np.einsum(
        "ca,jcd,db->jab", orthogonal, observables, orthogonal, optimize=True
    )
    return ReadoutMap("real_orthogonal", seed, matrices, unitary=orthogonal)


def _normalize_latent(latent: np.ndarray) -> np.ndarray:
    values = np.asarray(latent, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 32:
        raise ValueError(f"latent must have shape (n, 32), got {values.shape}")
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    result = np.zeros_like(values)
    nonzero = norms[:, 0] > 1e-12
    result[nonzero] = values[nonzero] / norms[nonzero]
    result[~nonzero, 0] = 1.0
    return result


def quadratic_features(latent: np.ndarray, readout: ReadoutMap) -> np.ndarray:
    normalized = _normalize_latent(latent)
    return np.einsum(
        "ni,jik,nk->nj", normalized, readout.matrices, normalized, optimize=True
    ).astype(np.float64)


def random_fourier_features(
    latent: np.ndarray, seed: int, n_features: int = 15
) -> np.ndarray:
    normalized = _normalize_latent(latent)
    rng = np.random.default_rng(seed)
    frequencies = rng.normal(size=(normalized.shape[1], n_features))
    phases = rng.uniform(0.0, 2.0 * np.pi, size=n_features)
    return np.cos(normalized @ frequencies + phases)


def shot_sampled_qrc_features(
    latent: np.ndarray,
    readout: ReadoutMap,
    shots: int,
    seed: int,
) -> np.ndarray:
    """Estimate each Pauli readout from an independent finite-shot experiment.

    The current study samples the 15 Z/ZZ expectation values independently.
    This models a fixed-shot budget per observable rather than a hardware
    measurement schedule that reuses one computational-basis sample.
    """
    if shots <= 0:
        raise ValueError("shots must be positive")
    ideal = quadratic_features(latent, readout)
    probabilities = np.clip((1.0 + ideal) / 2.0, 0.0, 1.0)
    rng = np.random.default_rng(seed)
    successes = rng.binomial(shots, probabilities)
    return (2.0 * successes / shots) - 1.0


def depolarized_qrc_features(
    latent: np.ndarray,
    readout: ReadoutMap,
    probability: float,
    shots: int | None = None,
    seed: int = 0,
) -> np.ndarray:
    """Apply symmetric single-qubit depolarizing noise to Pauli readouts.

    A single-qubit depolarizing channel with total probability p multiplies
    each Pauli expectation by lambda = 1 - 4p/3. Z readouts receive one factor;
    two-qubit ZZ readouts receive two independent factors.
    """
    if not 0.0 <= probability < 0.75:
        raise ValueError("depolarizing probability must be in [0, 0.75)")
    features = quadratic_features(latent, readout)
    scale = 1.0 - 4.0 * probability / 3.0
    result = features.copy()
    result[:, :5] *= scale
    result[:, 5:] *= scale * scale
    if shots is not None:
        probabilities = np.clip((1.0 + result) / 2.0, 0.0, 1.0)
        rng = np.random.default_rng(seed)
        successes = rng.binomial(shots, probabilities)
        result = (2.0 * successes / shots) - 1.0
    return result


def diagnostics(readout: ReadoutMap) -> dict[str, object]:
    flattened = readout.matrices.reshape(readout.matrices.shape[0], -1)
    singular = np.linalg.svd(flattened, compute_uv=False)
    tolerance = singular[0] * max(flattened.shape) * np.finfo(float).eps
    return {
        "name": readout.name,
        "seed": readout.seed,
        "rank": int(np.sum(singular > tolerance)),
        "singular_values": [float(value) for value in singular],
        "condition_number": float(singular[0] / singular[-1]),
    }

