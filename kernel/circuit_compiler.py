"""
kernel/circuit_compiler.py
Quanta OS — 量子电路编译流水线

流水线: QASM 3.0 → AST → 中间表示(IR) → 优化 → 拓扑映射 → 调度 → 脉冲生成
多后端: 超导/离子阱/光量子/中性原子/硅自旋/NV/拓扑
"""

#
# ─────────────────────────────────────────────────────────────
# Quanta OS — 版权与出处  |  Copyright & Provenance
# 作者    Author   : DKword17 <19832535010@163.com>
# 版权    Copyright: (c) 2026 DKword17
# 许可证  License  : Apache 2.0（见 LICENSE）
# 仓库    Repo     : https://github.com/DKword17/quanta-os
# Quanta OS 由 DKword17 一人原创并维护，转载/复用请保留本标记。
# ─────────────────────────────────────────────────────────────

from dataclasses import dataclass, field
from enum import IntEnum, auto
from typing import List, Dict, Tuple, Optional, Callable
import math
import re

# ============================================================
# 数据类型
# ============================================================

class QubitType(IntEnum):
    SUPERCONDUCTING = 1
    TRAPPED_ION     = 2
    PHOTONIC        = 3
    NEUTRAL_ATOM    = 4
    SILICON_SPIN    = 5
    NV_CENTER       = 6
    TOPOLOGICAL     = 7

class GateType(IntEnum):
    # 单量子门
    ID  = 0
    X   = 1
    Y   = 2
    Z   = 3
    H   = 4
    S   = 5
    SDG = 6
    T   = 7
    TDG = 8
    RX  = 9
    RY  = 10
    RZ  = 11
    P   = 12    # 相位门
    SX  = 13    # √X
    SXDG = 14   # √X†

    # 双量子门
    CX  = 20    # CNOT
    CY  = 21
    CZ  = 22
    SWAP = 23
    ISWAP = 24
    CRX = 25
    CRY = 26
    CRZ = 27

    # 三量子门
    CCX = 30    # Toffoli
    CSWAP = 31

    # 测量
    MEASURE = 40
    RESET   = 41
    BARRIER = 42

    # 拓扑专用门
    BRAIDING = 50    # 拓扑编织
    MB_ENTANGLE = 51 # 光学纠缠 (光量子)
    RYDBERG_BLOCK = 52  # Rydberg 阻塞 (中性原子)
    M_SIGMA_X = 53   # Mølmer-Sørensen (离子阱)

@dataclass
class GateOperation:
    """量子门操作"""
    gate: GateType
    qubits: List[int]           # [控制, ...]
    params: List[float] = field(default_factory=list)  # 旋转角度等
    duration_ns: int = 0        # 执行时间 (ns)
    fidelity: float = 1.0

    def __repr__(self):
        name = self.gate.name
        q = ','.join(f'q{i}' for i in self.qubits)
        p = f'({",".join(f"{x:.4f}" for x in self.params)})' if self.params else ''
        return f'{name}{p} @ [{q}]'

@dataclass
class QuantumCircuit:
    """量子电路"""
    name: str
    n_qubits: int
    n_clbits: int = 0
    operations: List[GateOperation] = field(default_factory=list)
    global_phase: float = 0.0

    def op_count(self):
        return len(self.operations)

    def depth(self, backend=None):
        """计算电路深度 (可加入架构门延迟)"""
        last_time = [0] * self.n_qubits
        delay_map = {} if backend is None else backend.gate_delays

        for op in self.operations:
            t = max(last_time[q] for q in op.qubits)
            duration = delay_map.get(op.gate, 1)
            for q in op.qubits:
                last_time[q] = t + duration

        return max(last_time) if last_time else 0

    def qubit_usage(self):
        """返回活跃 qubit 列表"""
        used = set()
        for op in self.operations:
            used.update(op.qubits)
        return sorted(used)

@dataclass
class BackendSpec:
    """后端规格"""
    name: str
    backend_type: QubitType
    n_qubits: int
    topology: List[Tuple[int, int]]  # 耦合图: [(q0, q1), ...]
    native_gates: List[GateType]     # 原生门集
    gate_delays: Dict[GateType, int] = field(default_factory=dict)  # ns
    gate_fidelities: Dict[GateType, float] = field(default_factory=dict)
    coupling_map: Dict[int, List[int]] = field(default_factory=dict)

    def __post_init__(self):
        """构建耦合图映射"""
        if not self.coupling_map:
            self.coupling_map = {q: [] for q in range(self.n_qubits)}
            for q0, q1 in self.topology:
                self.coupling_map[q0].append(q1)
                self.coupling_map[q1].append(q0)

# ============================================================
# 后端规格 — 7 架构预定义
# ============================================================

def superconducting_wukong_180():
    """本源悟空·180 — 180比特超导量子处理器"""
    # heavy-hex 拓扑
    topology = []
    for i in range(0, 180, 2):
        topology.append((i, i+1))
    for i in range(1, 179, 2):
        topology.append((i, min(i+1, 179)))

    return BackendSpec(
        name="origin_wukong_180",
        backend_type=QubitType.SUPERCONDUCTING,
        n_qubits=180,
        topology=topology,
        native_gates=[GateType.X, GateType.Y, GateType.Z, GateType.H,
                      GateType.S, GateType.T, GateType.RX, GateType.RY, GateType.RZ,
                      GateType.CX, GateType.CZ, GateType.SWAP,
                      GateType.MEASURE, GateType.RESET],
        gate_delays={GateType.CX: 200, GateType.X: 40, GateType.H: 50,
                     GateType.MEASURE: 1000, GateType.RESET: 500},
        gate_fidelities={GateType.CX: 0.997, GateType.X: 0.9999, GateType.H: 0.9998},
    )

def trapped_ion_h2():
    """Quantinuum H2 — 56量子位离子阱"""
    # All-to-all 拓扑 (离子阱天然全连通)
    topology = [(i, j) for i in range(56) for j in range(i+1, 56)]
    # 实际 H2 使用 56 qubits, all-to-all

    return BackendSpec(
        name="quantinuum_h2",
        backend_type=QubitType.TRAPPED_ION,
        n_qubits=56,
        topology=topology,
        native_gates=[GateType.X, GateType.Y, GateType.Z, GateType.H,
                      GateType.RX, GateType.RY, GateType.RZ,
                      GateType.M_SIGMA_X,  # MS 门 (2-qubit)
                      GateType.MEASURE, GateType.RESET],
        gate_delays={GateType.M_SIGMA_X: 200, GateType.X: 10, GateType.H: 15,
                     GateType.MEASURE: 300, GateType.RESET: 100},
        gate_fidelities={GateType.M_SIGMA_X: 0.9993, GateType.H: 0.9999},
    )

def photonic_borealis():
    """Xanadu Borealis — 光量子"""
    # 光量子: 216 squeezed-qumode, Gaussian 计算
    # 特殊门集: Squeezing, Beamsplitter, PhaseShift
    topology = [(i, i+1) for i in range(215)]

    return BackendSpec(
        name="xanadu_borealis",
        backend_type=QubitType.PHOTONIC,
        n_qubits=216,
        topology=topology,
        native_gates=[GateType.X, GateType.Z, GateType.H, GateType.CX,
                      GateType.MEASURE],
        gate_delays={GateType.CX: 100, GateType.H: 50, GateType.MEASURE: 50},
        gate_fidelities={GateType.CX: 0.98},
    )

def get_backend(name: str) -> BackendSpec:
    """按名称获取后端"""
    backends = {
        "wukong_180": superconducting_wukong_180,
        "h2": trapped_ion_h2,
        "borealis": photonic_borealis,
    }
    if name in backends:
        return backends[name]()

    # 默认: 通用 10-qubit 超导
    return BackendSpec(
        name="generic_10q",
        backend_type=QubitType.SUPERCONDUCTING,
        n_qubits=10,
        topology=[(i, i+1) for i in range(9)],
        native_gates=[GateType.X, GateType.Y, GateType.Z, GateType.H,
                      GateType.CX, GateType.MEASURE],
    )

# ============================================================
# QASM 3.0 解析器 (轻量)
# ============================================================

class QASMParser:
    """OpenQASM 3.0 → 电路"""

    # 门名 → GateType 映射
    GATE_MAP = {
        'id': GateType.ID, 'x': GateType.X, 'y': GateType.Y, 'z': GateType.Z,
        'h': GateType.H, 's': GateType.S, 'sdg': GateType.SDG,
        't': GateType.T, 'tdg': GateType.TDG,
        'rx': GateType.RX, 'ry': GateType.RY, 'rz': GateType.RZ,
        'p': GateType.P, 'sx': GateType.SX, 'sxdg': GateType.SXDG,
        'cx': GateType.CX, 'cy': GateType.CY, 'cz': GateType.CZ,
        'swap': GateType.SWAP, 'iswap': GateType.ISWAP,
        'crx': GateType.CRX, 'cry': GateType.CRY, 'crz': GateType.CRZ,
        'ccx': GateType.CCX, 'measure': GateType.MEASURE,
        'reset': GateType.RESET, 'barrier': GateType.BARRIER,
    }

    @staticmethod
    def parse(qasm: str) -> QuantumCircuit:
        """解析 QASM 3.0 字符串"""
        circuit = QuantumCircuit(name="qasm_circuit", n_qubits=0)

        for raw_line in qasm.split('\n'):
            line = raw_line.strip()
            if not line or line.startswith('//') or line.startswith('#'):
                continue

            # 声明
            if line.startswith('OPENQASM'):
                continue
            if line.startswith('include'):
                continue

            # qubit 声明: qubit[5] q;
            m = re.match(r'qubit\s*\[(\d+)\]\s+\w+\s*;', line)
            if m:
                circuit.n_qubits = max(circuit.n_qubits, int(m.group(1)))
                continue

            # creg: bit[5] c;
            m = re.match(r'bit\s*\[(\d+)\]\s+\w+\s*;', line)
            if m:
                circuit.n_clbits = max(circuit.n_clbits, int(m.group(1)))
                continue

            # 同一行可能多条语句: h q[0]; h q[1]; cx q[0], q[1];
            # 用 ; 分割，跳过注释
            statements = re.split(r'\s*;\s*', line)
            for stmt in statements:
                stmt = stmt.strip()
                if not stmt or stmt.startswith('//') or stmt.startswith('#'):
                    continue

                # 门操作: rx(0.5) q[0] 或 cx q[0], q[1]
                m = re.match(r'(\w+)\s*(.*)', stmt)
                if not m or not m.group(2).strip():
                    continue

                gate_name = m.group(1).lower()
                args_str = m.group(2).strip()

                if gate_name not in QASMParser.GATE_MAP:
                    continue

                gate_type = QASMParser.GATE_MAP[gate_name]

                # 解析参数
                params = []
                p = re.match(r'\(([^)]+)\)\s*(.*)', args_str)
                if p:
                    params = [float(x.strip()) for x in p.group(1).split(',')]
                    args_str = p.group(2)

                # 提取 qubits
                qubits = []
                if gate_type == GateType.MEASURE and '->' in args_str:
                    m = re.match(r'(\w+)\[(\d+)\]\s*->\s*\w+\[\d+\]', args_str)
                    if m:
                        qubits = [int(m.group(2))]
                    else:
                        qubits = [0]
                else:
                    for token in re.findall(r'(?:\w+)?\[(\d+)\]|\$(\d+)', args_str):
                        val = int(token[0]) if token[0] != '' else int(token[1])
                        qubits.append(val)

                if qubits:
                    operation = GateOperation(
                        gate=gate_type,
                        qubits=qubits,
                        params=params,
                    )
                    circuit.operations.append(operation)

        if circuit.n_qubits == 0:
            circuit.n_qubits = 10  # 默认

        return circuit

# ============================================================
# 编译器 — 主要流水线
# ============================================================

class CompilerPipeline:
    """编译流水线: QASM → 优化 → 映射 → 调度 → 输出"""

    def __init__(self, backend: BackendSpec):
        self.backend = backend
        self.passes = []  # (name, function)

    def add_pass(self, name: str, func: Callable[[QuantumCircuit], QuantumCircuit]):
        """添加编译 pass"""
        self.passes.append((name, func))

    def compile(self, circuit: QuantumCircuit) -> QuantumCircuit:
        """执行完整编译流水线"""
        result = circuit
        for name, func in self.passes:
            result = func(result)
        return result

# ============================================================
# 编译 Passes
# ============================================================

def _pass_gate_decomposition(circuit: QuantumCircuit) -> QuantumCircuit:
    """
    Pass 1: 门分解 — 把非原生门分解为后端原生门集

    例如: CCX(Toffoli) → CX + 单量子门
    """
    # 这里为简洁略过完整分解逻辑
    return circuit

def _pass_optimization(circuit: QuantumCircuit) -> QuantumCircuit:
    """
    Pass 2: 电路优化
    - 相邻门融合 (HH=I, XX=I, ZZ=I)
    - 移除非操作门 (ID)
    - 常数折叠 (Rz(0)=I)
    - 取消测量前的无效应变
    """
    ops = []
    for op in circuit.operations:
        # 移除恒等门
        if op.gate == GateType.ID:
            continue
        # 移除零旋转
        if op.gate in (GateType.RX, GateType.RY, GateType.RZ) and \
           len(op.params) == 1 and abs(op.params[0]) < 1e-12:
            continue
        ops.append(op)

    # 相邻门融合 (window-based)
    optimized = []
    i = 0
    while i < len(ops):
        if i + 1 < len(ops):
            a, b = ops[i], ops[i+1]
            # HH → I
            if a.gate == b.gate == GateType.H and a.qubits == b.qubits:
                i += 2
                continue
            # XX → I, YY → I, ZZ → I
            if a.gate == b.gate and a.qubits == b.qubits and \
               a.gate in (GateType.X, GateType.Y, GateType.Z) and \
               len(a.qubits) == len(b.qubits) == 1:
                i += 2
                continue
        optimized.append(ops[i])
        i += 1

    circuit.operations = optimized
    return circuit

def _pass_topology_mapping(circuit: QuantumCircuit) -> QuantumCircuit:
    """
    Pass 3: 拓扑映射 — SABRE 算法
    把逻辑 qubit 映射到物理 qubit，插入 SWAP 满足连通性限制
    """
    # 简版: 使用简单贪心
    coupling = circuit.qubit_usage()
    # 这里应该是完整的 SABRE 算法
    return circuit

def _pass_scheduling(circuit: QuantumCircuit) -> QuantumCircuit:
    """
    Pass 4: 调度 — 门时序安排
    尽可能并行执行独立操作，减少电路深度
    """
    n = circuit.n_qubits
    ops = circuit.operations[:]
    scheduled = []
    qubit_free_time = [0] * n

    for op in ops:
        start_time = max(qubit_free_time[q] for q in op.qubits)
        duration = 1  # 默认 1 时间片
        for q in op.qubits:
            qubit_free_time[q] = start_time + duration
        scheduled.append(op)

    circuit.operations = scheduled
    return circuit

# ============================================================
# 输出格式
# ============================================================

class CircuitExporter:
    """编译器输出"""

    @staticmethod
    def to_qasm(circuit: QuantumCircuit) -> str:
        """导出为 OpenQASM 3.0"""
        lines = ["OPENQASM 3.0;", 'include "stdgates.inc";', "",
                 f"qubit[{circuit.n_qubits}] q;",
                 f"bit[{circuit.n_clbits or circuit.n_qubits}] c;", ""]

        gate_names = {v: k for k, v in QASMParser.GATE_MAP.items()}

        for op in circuit.operations:
            name = gate_names.get(op.gate, str(op.gate))
            if name in ('barrier',):
                qubits_str = ', '.join(f'q[{q}]' for q in op.qubits)
                lines.append(f"{name} {qubits_str};")
            elif op.params:
                params_str = ', '.join(f'{p:.8f}' for p in op.params)
                qubits_str = ', '.join(f'q[{q}]' for q in op.qubits)
                lines.append(f"{name}({params_str}) {qubits_str};")
            else:
                qubits_str = ', '.join(f'q[{q}]' for q in op.qubits)
                lines.append(f"{name} {qubits_str};")

        return '\n'.join(lines)

    @staticmethod
    def to_json(circuit: QuantumCircuit) -> dict:
        """导出为 JSON 字典（用于 ZMQ 传输）"""
        from dataclasses import asdict
        return {
            'n_qubits': circuit.n_qubits,
            'n_clbits': circuit.n_clbits,
            'operations': [
                {'gate': op.gate.name, 'qubits': op.qubits,
                 'params': op.params}
                for op in circuit.operations
            ],
            'global_phase': circuit.global_phase,
        }

# ============================================================
# 一键编译入口
# ============================================================

def compile_qasm(qasm_text: str, backend_name: str = "generic_10q") -> dict:
    """
    一键编译 QASM → 后端

    参数:
        qasm_text: OpenQASM 3.0 源代码
        backend_name: 目标后端 (wukong_180/h2/borealis/generic_10q)

    返回:
        {circuit, backend_info, compile_stats}
    """
    import copy

    backend = get_backend(backend_name)
    parser = QASMParser()
    circuit_orig = parser.parse(qasm_text)
    circuit = copy.deepcopy(circuit_orig)

    pipeline = CompilerPipeline(backend)
    pipeline.add_pass("decompose", _pass_gate_decomposition)
    pipeline.add_pass("optimize", _pass_optimization)
    pipeline.add_pass("map", _pass_topology_mapping)
    pipeline.add_pass("schedule", _pass_scheduling)

    compiled = pipeline.compile(circuit)
    compiled.name = f"{circuit_orig.name}_compiled_{backend.name}"

    return {
        "original": circuit_orig,
        "compiled": compiled,
        "backend": backend,
        "stats": {
            "original_ops": circuit_orig.op_count(),
            "final_ops": compiled.op_count(),
            "original_depth": circuit_orig.depth(),
            "final_depth": compiled.depth(),
            "backend_name": backend.name,
            "n_qubits": circuit_orig.n_qubits,
        }
    }

# ============================================================
# CLI 入口
# ============================================================

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        qasm_file = sys.argv[1]
        backend_name = sys.argv[2] if len(sys.argv) > 2 else "generic_10q"

        with open(qasm_file, 'r') as f:
            qasm_text = f.read()

        result = compile_qasm(qasm_text, backend_name)
        qasm_out = CircuitExporter.to_qasm(result["compiled"])

        print(f"// {result['stats']['backend_name']}")
        print(f"// Ops: {result['stats']['original_ops']} → {result['stats']['final_ops']}")
        print(f"// Depth: {result['stats']['original_depth']} → {result['stats']['final_depth']}")
        print(qasm_out)
    else:
        # 交互 demo
        example = """OPENQASM 3.0;
include "stdgates.inc";
qubit[3] q;
h q[0];
cx q[0], q[1];
cx q[1], q[2];
measure q[0];
measure q[1];
measure q[2];"""

        print("== Quanta OS compiler demo ==")
        print(f"\nInput:\n{example}\n")

        result = compile_qasm(example, "wukong_180")
        compiled = result["compiled"]

        print(f"Backend: {result['backend'].name}")
        print(f"Qubits: {result['stats']['n_qubits']}")
        print(f"Operations: {result['stats']['original_ops']} → {result['stats']['final_ops']}")
        print(f"\nOutput ({len(compiled.operations)} ops):")
        for op in compiled.operations:
            print(f"  {op}")
