# Quanta OS v1 — 设计规范

## 发行版定位

**自适应 · 自组织 · 自构建 — 基础量子计算研究平台**

v1 的目标是提供一个**可用的量子计算机操作系统**，允许研究人员在此平台上进行更高级的开发和研究。它不是一个理论框架，而是一个可部署、可运行的系统。

---

## 核心架构

```
┌──────────────────────────────────────────────────────────────────┐
│                    用户层 (User Space)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ QOS Shell    │  │ QOS API      │  │ Research Toolchain   │  │
│  │ (量子CLI)    │  │ (Python SDK) │  │ (实验编排/可视化)    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
├─────────┼─────────────────┼──────────────────────┼──────────────┤
│         │     系统层 (System Services)            │              │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌──────────┴───────────┐  │
│  │ Quantum      │  │ Quantum      │  │ Resource &           │  │
│  │ Compiler     │  │ Simulator    │  │ Scheduler            │  │
│  │ Service      │  │ Service      │  │ Service              │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Calibration  │  │ Error        │  │ Topology             │  │
│  │ Service      │  │ Mitigation   │  │ Mapper               │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
├──────────────────────────────────────────────────────────────────┤
│                    内核层 (Kernel Space)                          │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │               Quanta Microkernel (≤64KB)                    │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │  │
│  │  │HW Detect │ │ Pulse    │ │ Readout  │ │Real-time Ctl │  │  │
│  │  │& Select  │ │ Sched    │ │ Engine   │ │(FPGA/SPI)    │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────┤
│                    硬件抽象层 (HAL)                               │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌─────┐│
│  │超导   │ │离子阱│ │光量子│ │中性原子│ │硅自旋│ │NV色心│ │拓扑 ││
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └─────┘│
└──────────────────────────────────────────────────────────────────┘
```

---

## 模块规范

### 1. 内核层 — Quanta Microkernel (QMK)

**位置**: `kernel/`
**目标**: ≤64KB 二进制，FPGA MCU 直接烧录

| 模块 | 功能 | 实现语言 |
|------|------|---------|
| `boot.c` | 硬件自检、启动后端选择、校准调度 | C |
| `backend_selector.c` | 自动检测量子处理器类型并加载对应后端 | C |
| `hal/*.h` | 7种架构硬件参数表 | C |
| `gate_discovery.c` | Rabi/Ramsey 扫描、原生门集发现 | C |
| `topology_mapper.c` | SABRE 拓扑映射、SWAP 路由 | C |
| `pulse_sched.c` | 实时脉冲时序调度器 | C |
| `readout_ddc.c` | 读出数据处理、状态判别 | C |
| `error_budget.c` | 实时错误预算跟踪 | C |

**微核系统调用**:

| 编号 | 调用名 | 功能 |
|------|--------|------|
| 0x01 | `QOS_EXECUTE_CIRCUIT` | 执行量子电路 |
| 0x02 | `QOS_MEASURE_ALL` | 全部测量 |
| 0x03 | `QOS_GET_TOPOLOGY` | 获取拓扑图 |
| 0x04 | `QOS_GET_CALIBRATION` | 获取校准参数 |
| 0x05 | `QOS_SELF_CALIBRATE` | 触发自校准 |
| 0x06 | `QOS_ERROR_BUDGET` | 查询错误预算 |
| 0x07 | `QOS_SET_BACKEND` | 切换后端 |
| 0x08 | `QOS_GET_STATE` | 系统状态报告 |

---

### 2. 系统层 — Quantum Services

#### 2.1 量子编译器服务

**位置**: `evolution-engine/vqc_compiler.py`

**输入 → 输出流**:
```
[OpenQASM 3.0] → [Parsing → IR Generation → Optimization → 
 Gate Decomposition → Topology Mapping → 
 Pulse Scheduling → FPGA Pulse Binary]
```

**编译流水线阶段**:

| 阶段 | 功能 | 算法 |
|------|------|------|
| P1 | QASM 解析 | ANTLR4 解析器 |
| P2 | 中间表示生成 | QIR 兼容 DAG |
| P3 | 门优化 | 模板匹配 + 门取消 |
| P4 | 门分解 | 架构感知 (从 HAL 读原生门集) |
| P5 | 拓扑映射 | SABRE + SWAP 路由 |
| P6 | 脉冲调度 | 时序约束满足 |
| P7 | 输出生成 | FPGA 脉冲二进制 |

**架构自适应编译**: 编译时自动读取 HAL 后端信息，选择最优门分解策略。

#### 2.2 校准服务

**位置**: `evolution-engine/calibration_service.py`

- 自动 T1/T2 扫描 (每 30 分钟或按需)
- 拉比振荡扫描找 π/π/2 脉冲幅度
- CR 脉冲校准 (超导)
- 激光对准优化 (离子阱/中性原子)
- 光子损失校准 (光量子)
- 校准结果写入 HAL 参数表

#### 2.3 拓扑映射服务

**位置**: `kernel/topology_mapper.c`

- SABRE 算法 (默认)
- Goemans-Williamson 最大割 (小规模)
- 动态重映射 (运行时错误自适应)

#### 2.4 错误缓解服务

| 方法 | 适用场景 |
|------|---------|
| Zero-Noise Extrapolation (ZNE) | 通用噪声 |
| Probabilistic Error Cancellation (PEC) | 已知噪声模型 |
| Readout Error Mitigation | 测量错误 |
| Dynamical Decoupling | 空闲 qubit 退相干 |
| Pauli Twirling | 相干噪声 → 随机噪声 |

#### 2.5 资源调度器

- 量子作业队列
- 物理 qubit 分配 (考虑噪声水平)
- 多租户隔离
- 量子-经典协同调度

---

### 3. 用户层 — 研究工具链

#### 3.1 QOS Shell (量子 CLI)

```bash
# 启动系统
qos start --backend auto
# 或指定后端
qos start --backend superconducting --vendor ibm --model heron

# 查看系统状态
qos status
qos topology
qos calibration

# 编译并运行量子程序
qos run circuit.qasm
qos run circuit.qasm --shots 8192

# 交互式实验
qos shell
> q[0] = H()
> q[1] = CX(q[0], q[1])
> result = measure_all()
> print(result)
```

#### 3.2 Python SDK

```python
from quanta_os import QOS

# 初始化 (自动检测)
qos = QOS()

# 或指定
qos = QOS(backend='trapped_ion', vendor='ionq', model='Forte')

# 运行电路
circuit = """
OPENQASM 3.0;
qubit[4] q;
h q[0];
cx q[0], q[1];
cx q[1], q[2];
"""

result = qos.execute(circuit, shots=4096)
print(result.counts)

# 获取校准数据
cal = qos.get_calibration()
print(f"T1: {cal.qubits[0].t1_us} μs")

# 可视化拓扑
qos.visualize_topology()

# 自校准
qos.calibrate()
```

#### 3.3 可视化工具

- 实时拓扑图 (qubit 温度/错误率热力图)
- 校准仪表盘
- 脉冲序列可视化
- 实验结果分析

---

## 部署架构

### 单芯片部署

```
[量子芯片] ↔ [FPGA 控制板] ↔ [QOS 微核 (MCU)] ↔ [QOS 系统层 (Linux)]
```

### 开发部署 (当前模式)

```
[模拟器] → [QOS Python 全栈] → [研究人员 API]
```

---

## v1 交付物清单

| 项目 | 状态 | 优先级 |
|------|------|--------|
| QMK 微核 (C, ≤64KB) | 🟡 骨架 | P0 |
| HAL 抽象层 (7架构) | ✅ 完成 | P0 |
| 编译器服务 (VQC) | 🟡 骨架 | P0 |
| 校准服务 | 🟡 骨架 | P1 |
| 拓扑映射 (SABRE) | 🟡 骨架 | P1 |
| 错误缓解 | 🔴 待写 | P1 |
| QOS Shell (CLI) | 🔴 待写 | P2 |
| Python SDK | 🔴 待写 | P2 |
| 可视化仪表盘 | 🔴 待写 | P3 |
| 资源调度器 | 🔴 待写 | P2 |
| 噪声模拟器 | 🟡 骨架 | P1 |
| 实验编排平台 | 🟡 骨架 | P2 |
| 文档 + 教程 | 🔴 待写 | P2 |

**验证标准**: 在模拟器上完整运行 GHZ 态制备 → 测量 → 结果分析全流程。
