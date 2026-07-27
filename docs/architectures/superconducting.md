# 超导量子芯片架构

## 技术原理

超导量子比特基于 **Josephson 结**（SIS tunnel junction），利用超导电路的量子化能级作为 qubit。通过微波脉冲操控，通过谐振腔读出。

## 代表芯片

| 厂商 | 芯片 | Qubits | Topology | T1 | 保真度 |
|------|------|--------|----------|-----|-------|
| IBM | Eagle r3 | 127 | Heavy-Hex | 150μs | 99.7% |
| IBM | Heron r1 | 133 | Heavy-Hex | 200μs | 99.8% |
| IBM | Condor | 1121 | Heavy-Hex | 100μs | 99.5% |
| Google | Sycamore | 53 | Grid 9×6 | 50μs | 99.5% |
| Google | Willow | 105 | Grid | 100μs | 99.7% |
| Rigetti | Ankaa-3 | 84 | Square | 50μs | 99.5% |
| 本源量子 | Wukong | 72 | Heavy-Hex | 80μs | 99.3% |
| 国盾量子 | QKD-72 | 72 | Square | 60μs | 98.8% |

## Quanta OS 专用优化

- **DRAG 脉冲** — Derivative Removal by Adiabatic Gate，抑制泄漏到 |2⟩
- **CR 脉冲** — Cross-Resonance 实现 CNOT（IBM 标准方案）
- **Heavy-Hex 映射** — 专用拓扑映射器，最小化 SWAP 插入
- **3D 读出多路复用** — 频分复用同时读出多 qubit
- **实时 QEC** — Surface code 循环，周期 ~1μs

## 运行环境

- 稀释制冷机: ~10-20 mK
- 微波线缆: 50Ω 同轴
- 磁场屏蔽: μ-metal + 超导磁屏蔽
- FPGA 控制: 1 GS/s AWG, 14-bit
