# Algorithmes Quantiques — Notes de Conception

## 1. Rotation contrôlée arbitraire

Soit U un opérateur unitaire. La rotation contrôlée C-U est définie par:

    C-U|0⟩|ψ⟩ = |0⟩|ψ⟩
    C-U|1⟩|ψ⟩ = |1⟩(U|ψ⟩)

## 2. Estimation de phase (Kitaev)

L'algorithme de Kitaev estime la phase φ d'un opérateur U|ψ⟩ = e^{2πiφ}|ψ⟩
en extrayant chaque bit de φ par mesure adaptative.

## 3. Distance de fidélité

    F(ρ, σ) = Tr(√(√ρ · σ · √ρ))

Pour des états purs: F(|ψ⟩, |φ⟩) = |⟨ψ|φ⟩|²
