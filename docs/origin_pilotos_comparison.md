# Quanta OS — 与本源司南 (Origin PilotOS) 技术对标

> 本源司南 V4.0 — 国内首款量子计算机操作系统
> 本源量子 (Origin Quantum) 自主研发

---

## 对标分析

| 能力 | 本源司南 V4.0 | Quanta OS v1 | Quanta OS v2 |
|------|-------------|--------------|-------------|
| **多体系接入** | ✅ 超导/离子阱/光量子/中性原子 | ✅ 7架构 (含硅自旋/NV/拓扑) | ✅ |
| **统一调度** | ✅ 多用户多任务 | 🔴 待写 | ✅ |
| **量超融合** | ✅ 混合编译编排 | 🔴 待写 | ✅ |
| **噪声校正 (M3)** | ✅ 读取误差修正 | 🟡 计划中 | ✅ |
| **微内核架构** | ❌ 云服务层 | ✅ 内核 ≤64KB | ✅ |
| **FPGA 实时控制** | ❌ 协议层之上 | ✅ kernel/ 含 | ✅ |
| **自演化引擎** | ❌ 静态调度 | 🟡 VQC 编译器 | ✅ RL + Kalman |
| **集群编排** | ❌ 单节点 | 🔴 待写 | ✅ |
| **开源** | 社区版免费 | 🟡 Apache 2.0 | ✅ |
| **国产可控** | ✅ 全自主 | 🟡 含中国支持 | ✅ |

## Quanta OS 差异化优势

1. **微内核轻量** — 本源司南需要 Linux 运行环境；Quanta OS ≤64KB 可烧 FPGA/MCU
2. **实时 FPGA 控制** — 本源司南通过 ZMQ 协议通信；Quanta OS 直接生成 FPGA 脉冲二进制
3. **自演化循环** — 本源司南静态校准策略；Quanta OS RL 智能体 + Kalman 预测 + 闭环学习
4. **集群原生** — 本源司南单节点部署；Quanta OS 内置 mDNS 节点发现 + 分布式编译
5. **7 架构覆盖** — 本源司南 4 架构；Quanta OS 增加了硅自旋/NV色心/拓扑

## 兼容性

Quanta OS 的 ZMQ 协议层 (`kernel/zmq_protocol.py`) 兼容本源司南的消息格式：
- ZeroMQ + JSON 多帧消息
- 同样的消息类型和消息结构
- 可直接接入本源悟空/司南平台的 QPU

## 参考

- 本源司南文档: https://qcloud.originqc.com.cn/zh/programming/pilotos
- 司南通信协议: ZeroMQ+JSON, ZMQ REQ/REP + PUB/SUB
- 开源: QPanda2 (Apache 2.0), 本源司南社区版免费下载
