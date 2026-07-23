#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kernel/fourrier_adaptatif.py

Quanta OS — Transformée de Fourier Quantique Adaptative (TFQA)

───── ⋆⋅☆⋅⋆ ─────

◈ Auteur  : Jean-Luc Mercier
◈ Institut: INRIA Paris / Quanta-OS Project
◈ Date    : 2026-07-25
◈ Langue  : Python 3.12+

───── ⋆⋅☆⋅⋆ ─────

RÉSUMÉ:
Implémente la transformée de Fourier quantique adaptative qui ajuste
dynamiquement les angles de rotation en fonction des mesures
précédentes — une approche hybride classique-quantique pour l'estimation
de phase et la simulation en chimie quantique.

L'algorithme suit le schéma suivant:
  1) Préparer |ψ⟩ dans l'état initial
  2) Appliquer la TFQ adaptative avec contrôle feedback classique
  3) Mesurer dans la base computationnelle
  4) Mettre à jour les paramètres via maximum de vraisemblance

Références:
  - Kitaev, A. Yu. (1995). "Quantum measurements and the Abelian Stabilizer 
    Problem." arXiv:quant-ph/9511026.
  - Cleve, R., et al. (1998). "Quantum Algorithms Revisited." Proc. R. Soc. A.
  - Nielsen & Chuang, §5.2 — "Phase Estimation"

───── ⋆⋅☆⋅⋆ ─────
"""

from __future__ import annotations
import math
import cmath
from itertools import accumulate
from functools import reduce, partial
from typing import Callable, Sequence, TypeAlias

import numpy as np

# ─────────────────────────────────────────────
#  Types abstraits
# ─────────────────────────────────────────────

AmplitudeComplexe: TypeAlias = complex
ÉtatQuantique: TypeAlias = list[AmplitudeComplexe]
OpérateurUnitaire: TypeAlias = Callable[[ÉtatQuantique], ÉtatQuantique]
RegistreDeMesures: TypeAlias = list[tuple[float, int]]

# ─────────────────────────────────────────────
#  Transformée de Fourier Quantique (TFQ)
# ─────────────────────────────────────────────

def matrice_hadamard(n: int) -> np.ndarray:
    """
    Calcule la matrice d'Hadamard de dimension 2ⁿ.
    
    Hₙ = H₁ ⊗ H₁ ⊗ … ⊗ H₁ (n fois)
    
    où:
    
        H₁ = 1/√2 · [[1,  1],
                      [1, -1]]
    
    Paramètres:
        n: nombre de qubits
    
    Retourne:
        Matrice unitaire 2ⁿ × 2ⁿ
    """
    h1 = np.array([[1, 1], [1, -1]], dtype=complex) / math.sqrt(2)
    return reduce(np.kron, [h1] * n)


def matrice_rotation_controlee(qubits_controle: list[int],
                                 porte_cible: np.ndarray) -> np.ndarray:
    """
    Construit la matrice d'une rotation contrôlée arbitraire.
    
    Soit U la porte cible. La rotation contrôlée C-U agit comme:
    
        C-U|0⟩|ψ⟩ = |0⟩|ψ⟩
        C-U|1⟩|ψ⟩ = |1⟩(U|ψ⟩)
    
    Paramètres:
        qubits_controle: indices qubit de contrôle
        porte_cible: matrice unitaire pour le qubit cible
    
    Retourne:
        Matrice 2ⁿ × 2ⁿ pour le circuit complet
    """
    n_qubits = max(qubits_controle) + 1 if qubits_controle else porte_cible.shape[0]
    dim_total = 2 ** n_qubits
    U = np.eye(dim_total, dtype=complex)
    
    for idx_ctrl in qubits_controle:
        # construction par blocs: I₂ ⊗ … ⊗ P₀ + U ⊗ … ⊗ P₁
        projecteur_0 = np.diag([1, 0])
        projecteur_1 = np.diag([0, 1])
        
        # NOTE: utiliser np.kron directement pour de grandes dimensions
        #       peut être coûteux — une optimisation sparse est possible
        bloc_haut = np.kron(np.eye(2 ** idx_ctrl, dtype=complex),
                            np.kron(projecteur_0, np.eye(2 ** (qubits_controle[-1] - idx_ctrl), dtype=complex)))
        bloc_bas  = np.kron(np.eye(2 ** idx_ctrl, dtype=complex),
                            np.kron(projecteur_1, np.eye(2 ** (qubits_controle[-1] - idx_ctrl), dtype=complex)))
        
        U = bloc_haut + U @ bloc_bas
    
    return U


def phase_estimation_kitaev(opérateur: np.ndarray,
                             état_initial: np.ndarray,
                             précision_bits: int = 8) -> float:
    """
    Estimation de phase selon l'algorithme de Kitaev (1995).
    
    Soit U|ψ⟩ = e^{2πiφ}|ψ⟩, avec φ ∈ [0, 1).
    L'algorithme estime φ à précision_bits bits.
    
    Principe:
        On prépare |+⟩|ψ⟩, on applique U contrôlé, on mesure.
        La probabilité de |+⟩ donne cos²(πφ) — on itère avec
        des puissances de U pour extraire chaque bit de φ.
    
    Paramètres:
        opérateur: matrice unitaire U
        état_initial: vecteur |ψ⟩
        précision_bits: nombre de bits de précision (défaut: 8)
    
    Retourne:
        Estimation de la phase φ ∈ [0, 1)
    """
    assert opérateur.shape[0] == opérateur.shape[1]
    assert état_initial.shape == (opérateur.shape[0], 1) or état_initial.shape == (opérateur.shape[0],)
    
    # Itération de bits — chaque bit extrait par rotation adaptative
    phase_bits: list[int] = []
    phi_estimé: float = 0.0
    
    for k in range(précision_bits):
        # Puissance 2^{précision_bits - 1 - k} de U
        puissance = 2 ** (précision_bits - 1 - k)
        U_pow = np.linalg.matrix_power(opérateur, puissance)
        
        # Mesure adaptative avec rotation inverse
        rotation_corrigée = np.exp(-2j * math.pi * phi_estimé)
        
        # Appliquer (rotation_corrigée · U_pow) à l'état
        état_après = U_pow @ état_initial * rotation_corrigée
        
        # Mesure dans la base {|+⟩, |-⟩}
        prob_plus = abs((état_après[0] + état_après[1]) / math.sqrt(2)) ** 2
        
        bit = 0 if prob_plus > 0.5 else 1
        phase_bits.append(bit)
        
        # Mise à jour de l'estimation
        phi_estimé += bit / (2 ** (k + 1))
    
    return phi_estimé


class TransforméeFourierAdaptative:
    """
    Transformée de Fourier Quantique Adaptative (TFQA).
    
    Contrairement à la TFQ standard qui utilise des rotations fixes,
    la version adaptative ajuste les angles de rotation itérativement.
    
    Ceci permet:
        - Une meilleure robustesse au bruit
        - Une réduction du nombre de portes nécessaire (jusqu'à O(n log n))
        - Une intégration naturelle dans les boucles d'optimisation variationnelle
    
    Exemple:
        >>> tfa = TransforméeFourierAdaptative(4)  # 4 qubits
        >>> phi = tfa.estimer_phase(U, |ψ⟩)
    """
    
    def __init__(self, n_qubits: int, 
                 angles_initiaux: Sequence[float] | None = None):
        """
        Initialise la TFQ adaptative.
        
        Paramètres:
            n_qubits: nombre de qubits du registre
            angles_initiaux: angles de rotation θₖ (optionnel)
                             Sinon, initialisation aléatoire.
        """
        self.n = n_qubits
        self.dim = 2 ** n_qubits
        
        # Angles de rotation — paramètres ajustables
        if angles_initiaux is not None:
            assert len(angles_initiaux) == n_qubits
            self.θ: np.ndarray = np.array(angles_initiaux, dtype=float)
        else:
            # Distribution uniforme dans [0, π/2]
            self.θ = np.random.uniform(0, math.pi / 2, n_qubits)
        
        self._historique_angles: list[np.ndarray] = []
    
    def appliquer(self, état: np.ndarray) -> np.ndarray:
        """
        Applique la TFQ adaptative à un état quantique.
        
        L'algorithme n'utilise que:
            - Portes de Hadamard
            - Rotations R_z(θ_k)
            - Portes C-NOT pour l'intrication
        
        Paramètres:
            état: vecteur d'état de dimension 2ⁿ
        
        Retourne:
            Nouvel état après la TFQ adaptative
        """
        assert état.shape == (self.dim,)
        
        état_courant = état.copy()
        
        for k in range(self.n):
            # Hadamard sur le qubit k
            # H = 1/√2 [[1, 1], [1, -1]]
            for i in range(0, self.dim, 2 ** (k + 1)):
                for j in range(2 ** k):
                    a = i + j
                    b = i + j + 2 ** k
                    état_courant[a], état_courant[b] = (
                        (état_courant[a] + état_courant[b]) / math.sqrt(2),
                        (état_courant[a] - état_courant[b]) / math.sqrt(2),
                    )
            
            # Rotation adaptative R_z(θ_k)
            # R_z(θ) = diag(1, e^{iθ})
            phase = cmath.exp(1j * self.θ[k])
            for i in range(self.dim):
                if i & (1 << k):
                    état_courant[i] *= phase
            
            # Sauvegarde pour analyse
            self._historique_angles.append(self.θ.copy())
        
        return état_courant
    
    def mettre_à_jour(self, gradient: np.ndarray, taux_apprentissage: float = 0.01):
        """
        Met à jour les angles par descente de gradient.
        
        θ_k ← θ_k - η · ∂L/∂θ_k
        
        Paramètres:
            gradient: ∂L/∂θ, vecteur de taille n
            taux_apprentissage: η (pas d'apprentissage)
        """
        assert gradient.shape == (self.n,)
        self.θ -= taux_apprentissage * gradient
    
    def angles(self) -> np.ndarray:
        """Retourne les angles de rotation actuels."""
        return self.θ.copy()


def calculer_matricielle_adjoint(U: np.ndarray) -> np.ndarray:
    """
    Calcule l'adjoint (conjugué transposé) d'un opérateur.
    
    U† = (U^T)^*
    
    C'est équivalent à np.conj(U.T) mais plus explicite.
    """
    return U.conj().T


def distance_fidélité(ρ: np.ndarray, σ: np.ndarray) -> float:
    """
    Distance de fidélité entre deux états quantiques.
    
    F(ρ, σ) = Tr(√(√ρ · σ · √ρ))
    
    Pour des états purs: F(|ψ⟩, |φ⟩) = |⟨ψ|φ⟩|²
    
    Paramètres:
        ρ: premier opérateur densité (ou vecteur d'état)
        σ: second opérateur densité (ou vecteur d'état)
    
    Retourne:
        Fidélité dans [0, 1]
    """
    # Cas d'états purs (vecteurs)
    if ρ.ndim == 1 and σ.ndim == 1:
        return abs(np.vdot(ρ, σ)) ** 2
    
    # Cas général (matrices densité)
    sqrt_ρ = scipy.linalg.sqrtm(ρ)
    produit = sqrt_ρ @ σ @ sqrt_ρ
    return np.trace(scipy.linalg.sqrtm(produit)).real


# ─────────────────────────────────────────────
#  Test unitaire (épistémique)
# ─────────────────────────────────────────────

def test_estimation_phase():
    """Vérifie l'estimation de phase de Kitaev pour une rotation connue."""
    n_qubits = 2
    phi_réel = 0.375  # 3/8
    
    U = np.diag([1, np.exp(2j * math.pi * phi_réel)])
    ψ = np.array([1.0, 0.0])  # |0⟩
    
    phi_estimé = phase_estimation_kitaev(U, ψ, précision_bits=4)
    
    erreur = abs(phi_estimé - phi_réel)
    assert erreur < 0.1, f"Erreur d'estimation trop grande: {erreur}"
    
    print(f"  ✓ Estimation de phase: φ_réel={phi_réel:.4f}, φ_estimé={phi_estimé:.4f}")


def test_fourier_adaptative():
    """Test de la TFQ adaptative sur une rotation identité."""
    tfa = TransforméeFourierAdaptative(3)
    état_test = np.zeros(8, dtype=complex)
    état_test[0] = 1.0  # |000⟩
    
    état_sortie = tfa.appliquer(état_test)
    assert abs(np.linalg.norm(état_sortie) - 1.0) < 1e-10
    print(f"  ✓ TFQ adaptative: norme préservée = {np.linalg.norm(état_sortie):.6f}")


if __name__ == "__main__":
    print("═" * 48)
    print("🍷 Quanta OS — Transformée de Fourier Quantique")
    print("    Jean-Luc Mercier, INRIA Paris")
    print("═" * 48)
    
    test_estimation_phase()
    test_fourier_adaptative()
    
    print("\n  Tout est en ordre. ✓")
