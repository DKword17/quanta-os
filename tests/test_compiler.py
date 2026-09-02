"""
test_compiler.py
Quanta OS — 编译流水线功能测试

测试内容:
1. QASM 3.0 解析 (bell_state, ghz_state, vqe_circuit)
2. 电路优化 pass
3. 多后端编译 (超导/离子阱/光量子)
4. 电路深度/门统计
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

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kernel.circuit_compiler import (
    compile_qasm, CircuitExporter, QASMParser,
    get_backend, GateOperation, GateType, QuantumCircuit,
)

def test_qasm_parser():
    """测试 QASM 解析"""
    print("=== Test 1: QASM Parser ===")

    bell = """OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
bit[2] c;
h q[0];
cx q[0], q[1];
measure q[0];
measure q[1];"""

    parser = QASMParser()
    circuit = parser.parse(bell)

    assert circuit.n_qubits == 2
    assert circuit.op_count() == 4  # h + cx + measure + measure
    print(f"  ✅ Bell state: {circuit.op_count()} ops, {circuit.n_qubits} qubits")
    print(f"    Operations: {[str(op) for op in circuit.operations]}")

    # GHZ-3
    ghz = """OPENQASM 3.0;
qubit[3] q;
h q[0];
cx q[0], q[1];
cx q[0], q[2];
measure q[0];
measure q[1];
measure q[2];"""

    circuit2 = parser.parse(ghz)
    assert circuit2.op_count() == 6
    print(f"  ✅ GHZ-3: {circuit2.op_count()} ops, {circuit2.n_qubits} qubits")

def test_compile_pipeline():
    """测试编译流水线"""
    print("\n=== Test 2: Compile Pipeline ===")

    # 用含冗余门来测试优化
    qasm = """OPENQASM 3.0;
qubit[3] q;
h q[0];
h q[0];       // HH = I, 应被消除
x q[1];
x q[1];       // XX = I, 应被消除
cx q[0], q[1];
measure q[0];
measure q[1];"""

    result = compile_qasm(qasm, "wukong_180")
    compiled = result["compiled"]

    stats = result["stats"]
    print(f"  Backend: {stats['backend_name']}")
    print(f"  Ops: {stats['original_ops']} → {stats['final_ops']}")
    print(f"  Qubits: {stats['n_qubits']}")

    # 冗余门应被优化掉
    assert stats['final_ops'] < stats['original_ops'], \
        f"Optimization failed: {stats['original_ops']} → {stats['final_ops']}"
    print(f"  ✅ Optimization active: {stats['original_ops']} → {stats['final_ops']}")

def test_multi_backend():
    """测试多后端编译"""
    print("\n=== Test 3: Multi-backend Compilation ===")

    qasm = """OPENQASM 3.0;
qubit[4] q;
h q[0];
cx q[0], q[1];
cx q[1], q[2];
cx q[2], q[3];
measure q[0];
measure q[1];
measure q[2];
measure q[3];"""

    for name in ["generic_10q", "wukong_180", "h2"]:
        result = compile_qasm(qasm, name)
        print(f"  🌐 {result['backend'].name}:")
        print(f"     {result['stats']['original_ops']} → {result['stats']['final_ops']} ops")
        print(f"     Depth: {result['stats']['original_depth']} → {result['stats']['final_depth']}")

    print(f"  ✅ All backends compiled successfully")

def test_export_qasm():
    """测试 QASM 导出"""
    print("\n=== Test 4: QASM Re-export ===")

    qasm = """OPENQASM 3.0;
qubit[2] q;
h q[0];
cx q[0], q[1];
measure q[0];
measure q[1];"""

    parser = QASMParser()
    circuit = parser.parse(qasm)

    exported = CircuitExporter.to_qasm(circuit)
    print(f"  Re-exported:\n{exported}\n")

    # 再次解析确认无损
    circuit2 = parser.parse(exported)
    assert circuit2.op_count() == circuit.op_count()
    print(f"  ✅ QASM round-trip: {circuit.op_count()} == {circuit2.op_count()} ops")

def test_vqe_circuit():
    """测试 VQE 变分电路"""
    print("\n=== Test 5: VQE-style Variational Circuit ===")

    # VQE 的硬件高效拟设 (HEA)
    qasm = """OPENQASM 3.0;
qubit[4] q;
// 第一层: 初始化
h q[0]; h q[1]; h q[2]; h q[3];
// 第一层: 纠缠
cx q[0], q[1]; cx q[1], q[2]; cx q[2], q[3];
// 第一层: 旋转
rx(0.5) q[0]; ry(0.3) q[1]; rz(0.7) q[2]; rx(0.1) q[3];
// 第二层: 纠缠
cx q[0], q[1]; cx q[1], q[2];
// 第二层: 旋转
rx(0.2) q[0]; ry(0.8) q[1]; rz(0.4) q[2]; rx(0.6) q[3];
measure q[0]; measure q[1]; measure q[2]; measure q[3];"""

    # 编译到悟空的 180-qubit 超导后端
    result = compile_qasm(qasm, "wukong_180")
    compiled = result["compiled"]

    print(f"  VQE 4-qubit HEA:")
    print(f"     Backend: {result['backend'].name}")
    print(f"     Qubits: {result['stats']['n_qubits']}")
    print(f"     Original ops: {result['stats']['original_ops']}")
    print(f"     Final ops: {result['stats']['final_ops']}")

    for op in compiled.operations:
        print(f"     {op}")

    assert compiled.op_count() > 0
    print(f"  ✅ VQE circuit compiled successfully")

def test_ion_trap_circuit():
    """测试离子阱专用电路"""
    print("\n=== Test 6: Ion Trap Circuit ===")

    # 离子阱专用 Mølmer-Sørensen 门
    backend = get_backend("h2")
    print(f"  Backend: {backend.name}")
    print(f"  Topology: all-to-all ({len(backend.topology)} edges)")
    print(f"  Native gates: {[g.name for g in backend.native_gates]}")

    qasm = """OPENQASM 3.0;
qubit[4] q;
h q[0]; h q[1]; h q[2]; h q[3];
cx q[0], q[1]; cx q[2], q[3];
measure q[0]; measure q[1]; measure q[2]; measure q[3];"""

    result = compile_qasm(qasm, "h2")
    print(f"  Qubits: {result['stats']['n_qubits']}")
    print(f"  Ops: {result['stats']['original_ops']} → {result['stats']['final_ops']}")
    print(f"  ✅ Ion trap compilation OK")

if __name__ == '__main__':
    print("=" * 50)
    print("Quanta OS — Compiler Test Suite")
    print("=" * 50)

    test_qasm_parser()
    test_compile_pipeline()
    test_multi_backend()
    test_export_qasm()
    test_vqe_circuit()
    test_ion_trap_circuit()

    print("\n" + "=" * 50)
    print("✅ ALL TESTS PASSED")
    print("=" * 50)
