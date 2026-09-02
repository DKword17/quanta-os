# Quanta OS — 通用量子计算机操作系统

**[Bootstrap · 自组织 · 自演化]**

Quanta OS 是一个面向**所有量子计算架构**的底层操作系统。它兼容市面上每一种量子处理器，为每种架构提供通用版和专用版内核，并通过自演化引擎在运行时持续优化性能。

完整架构与规范参见 [docs/architecture_overview.md](docs/architecture_overview.md) 与 [docs/v2_design_spec.md](docs/v2_design_spec.md)。

---

## 支持的架构

| 架构 | 物理原理 | 代表厂商 | 运行温度 | 门速度 | 最大规模 |
|------|---------|---------|---------|-------|---------|
| **超导 (Superconducting)** | Josephson 结 + 微波脉冲 | IBM, Google, Rigetti, **本源量子, 国盾量子** | ~10-20 mK | ~40 ns | 1121 qubits |
| **离子阱 (Trapped Ion)** | 囚禁离子 + 激光/微波 | IonQ, Quantinuum, **启科量子** | 室温 (~300K) | ~200 μs | 56 qubits |
| **光量子 (Photonic)** | 光子/压缩态 + 光学元件 | Xanadu, PsiQuantum, **图灵量子, 玻色量子** | 室温 | ~ns | 1000+ modes |
| **中性原子 (Neutral Atom)** | 光镊 + Rydberg 阻塞 | QuEra, Pasqal, Atom Computing | ~10 μK | ~1 μs | 500+ qubits |
| **硅基自旋 (Silicon Spin)** | 量子点/施主自旋 | Intel, Diraq, Equal1 | ~50-500 mK | ~40 ns | 12 qubits |
| **金刚石 NV 色心** | 氮空位中心自旋 | Quantum Brilliance, **国仪量子** | **室温** | ~200 ns | 50 qubits |
| **拓扑 (Topological)** | Majorana 零模 | Microsoft Station Q | ~10 mK | ~ns(理论) | 实验阶段 |

新增后端只需实现对应 `BackendSpec` 并注册到入口即可。

---

## 顶层架构

```
┌───────────────────────────────────────────────────────────────┐
│                    Level 2: 量子自演化引擎                      │
│   Variational Quantum Compiler ←→ Architecture-aware         │
│   Pulse Optimizer (SPSA/GRAPE)  ←→ Backend Plugins           │
│   Self-Evolution Loop           ←→ Noise Adaptation          │
├───────────────────────────────────────────────────────────────┤
│                    Level 1: 古典微核 (≤64KB)                   │
│   Auto-detection / Backend Selection                          │
│   Calibration (Rabi, T1/T2*, Randomized Benchmarking)         │
│   Topology Self-Mapping (SABRE, Floyd-Warshall)               │
│   Real-time Control (FPGA pulse / Laser / MW)                 │
├───────────────────────────────────────────────────────────────┤
│                    Level 0: 硬件抽象层                          │
│  超导 │ 离子阱 │ 光量子 │ 中性原子 │ 硅自旋 │ NV色心 │ 拓扑     │
└───────────────────────────────────────────────────────────────┘
```

---

## 项目结构

```
quanta-os/
├── quanta_os.py                  统一入口（QOS API + CLI）
├── kernel/                       编译 / 调度 / 校准 / 协议 + 微核 HAL
│   ├── circuit_compiler.py       QASM 3.0 → 7 架构编译流水线
│   ├── calibration_protocol.py   超导 qubit 校准（T1 / T2* / RB / 漂移校正）
│   ├── resource_scheduler.py     多程序资源调度器（兼容性打包）
│   ├── zmq_protocol.py           ZMQ + JSON 自研协议层
│   ├── fourier_adaptive.py       自适应量子傅里叶变换（AQFT）
│   ├── backend_selector.c        自动后端选择
│   ├── coupling_map.c            耦合图 + BFS 路由 / Floyd-Warshall
│   ├── rt_control.c              实时脉冲控制（FPGA DAC/ADC）
│   └── hal/
│       ├── origin_wukong_bridge.py   本源悟空 180 处理器桥接
│       └── *.h                      7 架构硬件抽象接口
│
├── evolution_engine/            自演化引擎（Python）
│   ├── vqc_compiler.py           变分量子编译器
│   ├── pulse_optimizer.py        脉冲自优化（SPSA / GRAPE）
│   ├── self_evolve.py            三层自演化主循环
│   └── backends/
│       ├── superconducting_backend.py
│       └── __init__.py           离子阱 / 光量子 / 中性原子 / 硅自旋 / NV / 拓扑
│
├── simulator/                    软实验环境
│   ├── noise_channel.py          通用噪声模型 + 拓扑生成器
│   ├── experiment_runner.py      实验编排平台
│   └── architectures/            各架构噪声模型
│
├── fpga/                         FPGA 控制
│   ├── pulse_gen.v               通用脉冲发生器
│   ├── readout_ddc.v             读出下变频
│   └── build.tcl
│
├── tests/                        全面集成测试（14 用例）
├── docs/                         文档
│   ├── architecture_overview.md  顶层架构总览（QOS-ARCH-001）
│   ├── origin_pilotos_comparison.md
│   ├── v2_design_spec.md         v2 设计规范
│   ├── architectures/            各架构详解
│   └── archive/                  归档（法语算法 / 研究 / v1 规范）
│
├── .gitignore
├── LICENSE                       Apache 2.0
└── README.md
```

---

## 快速开始

运行时仅依赖 Python 3.10+ 与 [NumPy](https://numpy.org/)（硬件桥接可选 `pyzmq`）。

```bash
pip install numpy pyzmq

# 列出已知后端
python quanta_os.py list-backends
# → generic_simulator, wukong_180, quantinuum_h2, borealis

# 编译一个 QASM 电路（默认走内置示例）
python quanta_os.py compile circuit.qasm --backend generic_simulator

# qubit 校准
python quanta_os.py calibrate --qubit 0
```

Python API：

```python
from quanta_os import QOS

qos = QOS(backend="generic_simulator")

qasm = "OPENQASM 3.0; include \"stdgates.inc\"; qubit[2] q; h q[0]; cx q[0], q[1]; measure q[0]; measure q[1];"
result = qos.compile(qasm)
print(result.final_ops)          # 编译后的门操作序列
```

自演化 / 跨后端开发：

```python
from evolution_engine.self_evolve import SelfEvolutionEngine
from evolution_engine.backends import TrappedIonBackend, NVCenterBackend

# 自演化闭环
engine = SelfEvolutionEngine(n_qubits=8)
engine.run_evolution_cycle(n_iterations=20)
print(engine.get_system_report())

# 离子阱全连通后端
be = TrappedIonBackend(vendor="ionq", model="Forte")
print(be.spec)
```

软实验环境：

```bash
python simulator/experiment_runner.py
```

---

## 运行测试

无第三方测试框架依赖，可直接独立运行：

```bash
python tests/test_comprehensive_verification.py
python tests/test_compiler.py
```

若安装了 `pytest`，也可：

```bash
python -m pytest tests/ -v
```

当前 14 个用例覆盖：QASM 解析、门分解/优化、多后端编译、ZMQ 协议往返、T1/T2*/随机基准校准、后端选择与端到端流程。

---

## FPGA 微核

`fpga/` 内为 Verilog 实时控制原语（`pulse_gen.v` 脉冲发生器、`readout_ddc.v` 读出下变频），`build.tcl` 为工程脚本。使用 Vivado/Xilinx 工具链时以 `build.tcl` 驱动综合，或按需导入到你的上层工程。

---

## 维护者与所有权

- **DKword17** <19832535010@163.com> — 本项目**唯一**作者、版权人与维护者。

本项目（Quanta OS）全部代码、文档、历史均出自 DKword17 一人之手，Apache 2.0 授权（见 [LICENSE](LICENSE)）。每个源文件头部均带有版权与出处标记 `Copyright (c) 2026 DKword17`。

> **侵权警示**：Quanta OS 为原创自研系统。任何未经授权的再分发、剥离出处标记后宣称"自研"或转售的行为，均构成对版权人权利的侵害，版权人保留追究法律责任的权利。转载与复用请保留本源出处标记。

一切版本历史、代码署名均出自同一作者。分支与版本管理遵循「开发者即维护者」的单一作者约定。

---

## 路线图

- [x] 统一入口：QOS 面向对象 API + CLI
- [x] 编译流水线：QASM → 优化 → 拓扑映射 → 调度
- [x] 多后端：超导 / 离子阱 / 光量子 / 中性原子 / 硅自旋 / NV / 拓扑
- [x] 自演化引擎：VQC + 脉冲优化（SPSA/GRAPE）三层闭环
- [x] 校准协议：T1 / T2* / 随机基准测试 / 漂移校正
- [ ] 补全各架构专用微核（HAL C 实装）
- [ ] 多节点 / 分布式集群上的资源调度与容错
- [ ] 真实硬件（本源悟空 180）桥接端到端验证
- [ ] 更细粒度的噪声感知在线编译

---

## 许可证

Apache 2.0（见 [LICENSE](LICENSE)）