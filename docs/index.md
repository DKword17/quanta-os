# Quanta OS 架构文档索引

## 内核 (C 微核)

| 文件 | 功能 | 状态 |
|------|------|------|
| `kernel/boot.c` | 引导流程：硬件发现 → 校准 → 自映射 → 自演化 | 🟡 骨架 |
| `kernel/gate_discovery.c` | 原生门集发现、DRAG 脉冲、GRAPE 优化 | 🟡 骨架 |
| `kernel/topology_mapper.c` | SABRE 拓扑映射、SWAP 路由 | 🟡 骨架 |
| `kernel/Makefile` | 构建系统，目标 ≤64KB | ✅ 完成 |
| `kernel/linker.ld` | 独立微核链接脚本 | ✅ 完成 |

## 自演化引擎 (Python)

| 文件 | 功能 | 状态 |
|------|------|------|
| `evolution-engine/vqc_compiler.py` | 变分量子编译器，OpenQASM → 脉冲 | 🟡 骨架 |
| `evolution-engine/pulse_optimizer.py` | SPSA/GRAPE 脉冲优化、自校准库 | 🟡 骨架 |
| `evolution-engine/self_evolve.py` | 三层自演化主循环 | 🟡 骨架 |

## FPGA 控制 (Verilog)

| 文件 | 功能 | 状态 |
|------|------|------|
| `fpga/pulse_gen.v` | 4 通道任意波形发生器，1 GS/s | 🟡 骨架 |
| `fpga/readout_ddc.v` | 读出数字下变频、CIC 抽取 | 🟡 骨架 |
| `fpga/build.tcl` | Vivado 构建脚本 | ✅ 完成 |

## 软实验环境 (Python)

| 文件 | 功能 | 状态 |
|------|------|------|
| `simulator/noise_channel.py` | 噪声模拟、拓扑生成器 | 🟡 骨架 |
| `simulator/experiment_runner.py` | 实验编排、自演化验证 | 🟡 骨架 |

## 设计决策记录

### 为什么 C 而不是 Rust？
- 目标二进制 ≤64KB，Rust 标准库二进制至少 200KB+
- 可直接烧入 FPGA 软核或 MCU，无运行时依赖
- 与现有 FPGA 工具链 (Vivado) 无缝对接

### 为什么 Python 做进化引擎？
- 开发迭代速度 > 执行速度（量子编译器本身就是离线的）
- 后续可以用 CUDA 加速热路径（跟 CMP 40HX 搭配）

### 为什么 Apache 2.0？
- 专利保护对量子计算领域至关重要
- 社区友好，商业可用
- 与主流量子 SDK (Qiskit, Cirq) 许可证兼容
