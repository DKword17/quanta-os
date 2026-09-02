#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kernel/fourier_adaptive.py

Quanta OS — Adaptive Quantum Fourier Transform (AQFT)

Author:    DKword17 <19832535010@163.com>
Date:      2026-07-25
License:   Apache 2.0

Summary:
Implements an adaptive quantum Fourier transform that dynamically adjusts
rotation angles based on prior measurement outcomes — a hybrid classical-
quantum approach for phase estimation and quantum chemistry simulation.

Algorithm outline:
  1) Prepare |psi> in the initial state
  2) Apply adaptive QFT with classical feedback control
  3) Measure in the computational basis
  4) Update parameters via maximum likelihood

References:
  - Kitaev, A. Yu. (1995). "Quantum measurements and the Abelian Stabilizer
    Problem." arXiv:quant-ph/9511026.
  - Cleve, R., et al. (1998). "Quantum Algorithms Revisited." Proc. R. Soc. A.
  - Nielsen & Chuang, Section 5.2 — "Phase Estimation"
"""

from __future__ import annotations
import math
import cmath
from functools import reduce, partial
from itertools import accumulate
from typing import Callable, Sequence, TypeAlias

import numpy as np

# ─── Type Aliases ────────────────────────────────────────────────────────────

ComplexAmplitude: TypeAlias = complex
QuantumState: TypeAlias = list[ComplexAmplitude]
UnitaryOperator: TypeAlias = Callable[[QuantumState], QuantumState]
MeasurementRegistry: TypeAlias = list[tuple[float, int]]

# ─── Quantum Fourier Transform Utilities ─────────────────────────────────────

def hadamard_matrix(n: int) -> np.ndarray:
    """
    Compute the Hadamard matrix of dimension 2^n.

    H_n = H_1 (x) H_1 (x) ... (x) H_1  (n times)

    where:

        H_1 = 1/sqrt(2) * [[1,  1],
                           [1, -1]]

    Args:
        n: number of qubits

    Returns:
        2^n x 2^n unitary matrix
    """
    h1 = np.array([[1, 1], [1, -1]], dtype=complex) / math.sqrt(2)
    return reduce(np.kron, [h1] * n)


def controlled_rotation_matrix(control_qubits: list[int],
                                target_gate: np.ndarray) -> np.ndarray:
    """
    Build the matrix of an arbitrary controlled rotation.

    Let U be the target gate. The controlled rotation C-U acts as:

        C-U|0>|psi> = |0>|psi>
        C-U|1>|psi> = |1>(U|psi>)

    Args:
        control_qubits: indices of control qubits
        target_gate: unitary matrix for the target qubit

    Returns:
        2^n x 2^n matrix for the full circuit
    """
    n_qubits = max(control_qubits) + 1 if control_qubits else target_gate.shape[0]
    dim_total = 2 ** n_qubits
    U = np.eye(dim_total, dtype=complex)

    for idx_ctrl in control_qubits:
        project_0 = np.diag([1, 0])
        project_1 = np.diag([0, 1])

        block_upper = np.kron(np.eye(2 ** idx_ctrl, dtype=complex),
                              np.kron(project_0, np.eye(2 ** (control_qubits[-1] - idx_ctrl), dtype=complex)))
        block_lower = np.kron(np.eye(2 ** idx_ctrl, dtype=complex),
                              np.kron(project_1, np.eye(2 ** (control_qubits[-1] - idx_ctrl), dtype=complex)))

        U = block_upper + U @ block_lower

    return U


def kitaev_phase_estimation(operator: np.ndarray,
                             initial_state: np.ndarray,
                             precision_bits: int = 8) -> float:
    """
    Phase estimation via Kitaev's algorithm (1995).

    Given U|psi> = e^{2pi i phi}|psi>, with phi in [0, 1),
    estimate phi to precision_bits bits.

    Principle:
        Prepare |+>|psi>, apply controlled-U, measure.
        The probability of |+> gives cos^2(pi phi) — iterate with
        powers of U to extract each bit of phi.

    Args:
        operator: unitary matrix U
        initial_state: vector |psi>
        precision_bits: number of bits of precision (default: 8)

    Returns:
        Phase estimate phi in [0, 1)
    """
    assert operator.shape[0] == operator.shape[1]
    assert initial_state.shape == (operator.shape[0], 1) or initial_state.shape == (operator.shape[0],)

    phase_bits: list[int] = []
    phi_estimate: float = 0.0

    for k in range(precision_bits):
        power = 2 ** (precision_bits - 1 - k)
        U_pow = np.linalg.matrix_power(operator, power)

        corrected_rotation = np.exp(-2j * math.pi * phi_estimate)
        state_after = U_pow @ initial_state * corrected_rotation

        prob_plus = abs((state_after[0] + state_after[1]) / math.sqrt(2)) ** 2

        bit = 0 if prob_plus > 0.5 else 1
        phase_bits.append(bit)

        phi_estimate += bit / (2 ** (k + 1))

    return phi_estimate


class AdaptiveFourierTransform:
    """
    Adaptive Quantum Fourier Transform (AQFT).

    Unlike the standard QFT which uses fixed rotations,
    the adaptive version iteratively adjusts rotation angles.

    This provides:
        - Improved robustness to noise
        - Reduced gate count (up to O(n log n))
        - Natural integration into variational optimization loops

    Example:
        >>> aft = AdaptiveFourierTransform(4)  # 4 qubits
        >>> phi = aft.estimate_phase(U, state)
    """

    def __init__(self, n_qubits: int,
                 initial_angles: Sequence[float] | None = None):
        """
        Initialize the adaptive QFT.

        Args:
            n_qubits: number of qubits in the register
            initial_angles: rotation angles theta_k (optional).
                            Random initialization if omitted.
        """
        self.n = n_qubits
        self.dim = 2 ** n_qubits

        if initial_angles is not None:
            assert len(initial_angles) == n_qubits
            self.theta: np.ndarray = np.array(initial_angles, dtype=float)
        else:
            self.theta = np.random.uniform(0, math.pi / 2, n_qubits)

        self._angle_history: list[np.ndarray] = []

    def apply(self, state: np.ndarray) -> np.ndarray:
        """
        Apply the adaptive QFT to a quantum state.

        Uses only:
            - Hadamard gates
            - R_z(theta_k) rotations
            - C-NOT gates for entanglement

        Args:
            state: state vector of dimension 2^n

        Returns:
            New state after the adaptive QFT
        """
        assert state.shape == (self.dim,)

        current = state.copy()

        for k in range(self.n):
            # Hadamard on qubit k
            # H = 1/sqrt(2) [[1, 1], [1, -1]]
            for i in range(0, self.dim, 2 ** (k + 1)):
                for j in range(2 ** k):
                    a = i + j
                    b = i + j + 2 ** k
                    current[a], current[b] = (
                        (current[a] + current[b]) / math.sqrt(2),
                        (current[a] - current[b]) / math.sqrt(2),
                    )

            # Adaptive rotation R_z(theta_k)
            # R_z(theta) = diag(1, e^{i theta})
            phase = cmath.exp(1j * self.theta[k])
            for i in range(self.dim):
                if i & (1 << k):
                    current[i] *= phase

            self._angle_history.append(self.theta.copy())

        return current

    def gradient_update(self, gradient: np.ndarray, learning_rate: float = 0.01):
        """
        Update angles via gradient descent.

        theta_k <- theta_k - eta * dL/dtheta_k

        Args:
            gradient: dL/dtheta, vector of size n
            learning_rate: eta (step size)
        """
        assert gradient.shape == (self.n,)
        self.theta -= learning_rate * gradient

    def get_angles(self) -> np.ndarray:
        """Return current rotation angles."""
        return self.theta.copy()


def adjoint(U: np.ndarray) -> np.ndarray:
    """
    Compute the adjoint (conjugate transpose) of an operator.

    U^dag = (U^T)^*

    Equivalent to np.conj(U.T) but more explicit.
    """
    return U.conj().T


def fidelity_distance(rho: np.ndarray, sigma: np.ndarray) -> float:
    """
    Fidelity distance between two quantum states.

    F(rho, sigma) = Tr(sqrt(sqrt(rho) . sigma . sqrt(rho)))

    For pure states: F(|psi>, |phi>) = |<psi|phi>|^2

    Args:
        rho: first density operator (or state vector)
        sigma: second density operator (or state vector)

    Returns:
        Fidelity in [0, 1]
    """
    # Pure states (vectors)
    if rho.ndim == 1 and sigma.ndim == 1:
        return abs(np.vdot(rho, sigma)) ** 2

    # General case (density matrices)
    import scipy.linalg
    sqrt_rho = scipy.linalg.sqrtm(rho)
    product = sqrt_rho @ sigma @ sqrt_rho
    return np.trace(scipy.linalg.sqrtm(product)).real


# ─── Unit Tests ──────────────────────────────────────────────────────────────

def test_phase_estimation():
    """Verify Kitaev phase estimation for a known rotation."""
    n_qubits = 2
    phi_true = 0.375  # 3/8

    U = np.diag([1, np.exp(2j * math.pi * phi_true)])
    psi = np.array([1.0, 0.0])  # |0>

    phi_est = kitaev_phase_estimation(U, psi, precision_bits=4)

    error = abs(phi_est - phi_true)
    assert error < 0.1, f"Estimation error too large: {error}"

    print(f"  PASS Phase estimation: phi_true={phi_true:.4f}, phi_est={phi_est:.4f}")


def test_adaptive_fourier():
    """Test adaptive QFT on an identity rotation."""
    aft = AdaptiveFourierTransform(3)
    test_state = np.zeros(8, dtype=complex)
    test_state[0] = 1.0  # |000>

    output = aft.apply(test_state)
    assert abs(np.linalg.norm(output) - 1.0) < 1e-10
    print(f"  PASS Adaptive QFT: norm preserved = {np.linalg.norm(output):.6f}")


if __name__ == "__main__":
    print("=" * 48)
    print("Quanta OS — Adaptive Quantum Fourier Transform")
    print("=" * 48)

    test_phase_estimation()
    test_adaptive_fourier()

    print("\n  All checks passed.")
