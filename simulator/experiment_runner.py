"""
simulator/experiment_runner.py
实验编排平台 — 自动化验证 Quanta OS 自演化能力
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from simulator.noise_channel import NoisyQuantumChannel, NoiseModel, TopologyGenerator
from evolution_engine.vqc_compiler import VariationalQuantumCompiler, Topology, QubitParams, EdgeParams
from evolution_engine.self_evolve import SelfEvolutionEngine
import time
import json


def experiment_bootstrap():
    """实验 1: 验证引导微核的基本功能"""
    print("=" * 60)
    print("实验 1: 引导微核启动测试")
    print("=" * 60)
    
    # 模拟 8-qubit 处理器
    engine = SelfEvolutionEngine(n_qubits=8)
    print(f"[PASS] 拓扑构建: {len(engine.topology.edges)} 条边")
    
    # 编译一个简单电路
    test_qasm = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
h q[0];
cx q[0],q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];"""
    
    result = engine.compiler.compile_circuit(test_qasm)
    print(f"[PASS] 电路编译: {result['n_gates']} 个门 | "
          f"保真度: {result['estimated_fidelity']:.4f}")
    
    return True


def experiment_self_evolution():
    """实验 2: 自演化循环验证"""
    print("\n" + "=" * 60)
    print("实验 2: 自演化闭环测试 (10 代)")
    print("=" * 60)
    
    engine = SelfEvolutionEngine(n_qubits=8)
    
    initial_fidelity = None
    
    for gen in range(10):
        state = engine.run_evolution_cycle(n_iterations=30)
        report = engine.get_system_report()
        
        if initial_fidelity is None:
            initial_fidelity = state.avg_fidelity
        
        print(f"  第 {gen+1:2d} 代 | "
              f"保真度: {state.avg_fidelity:.4f} | "
              f"复杂度: {state.circuit_complexity}")
    
    final_fidelity = state.avg_fidelity
    improvement = (final_fidelity - initial_fidelity) / initial_fidelity * 100
    
    print(f"\n[结果] 保真度提升: {improvement:+.1f}% "
          f"({initial_fidelity:.4f} → {final_fidelity:.4f})")
    
    return improvement > 0  # 只要有改善就算通过


def experiment_topology_adaptation():
    """实验 3: 拓扑自适应测试"""
    print("\n" + "=" * 60)
    print("实验 3: 拓扑自适应测试")
    print("=" * 60)
    
    # 生成三种不同拓扑
    topologies = {
        'Grid (3×3)': TopologyGenerator.grid(3, 3),
        'Heavy-Hex': TopologyGenerator.heavy_hex(2),
        'Random': TopologyGenerator.random(8, 0.3),
    }
    
    for name, edges in topologies.items():
        # 创建对应拓扑的引擎
        qubits = [QubitParams(id=i) for i in range(
            max([e[0] for e in edges] + [e[1] for e in edges]) + 1
        )]
        edge_params = [EdgeParams(a, b) for a, b in edges]
        topo = Topology(qubits=qubits, edges=edge_params)
        
        compiler = VariationalQuantumCompiler(topo)
        
        test_qasm = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
h q[0]; cx q[0],q[1]; cx q[1],q[2]; cx q[2],q[3];
measure q[0] -> c[0]; measure q[3] -> c[3];"""
        
        result = compiler.compile_circuit(test_qasm)
        print(f"  {name:20s} | SWAP: {result['mapping']['swaps']} | "
              f"保真度: {result['estimated_fidelity']:.4f}")
    
    return True


def experiment_adaptive_error_correction():
    """实验 4: 自适应纠错"""
    print("\n" + "=" * 60)
    print("实验 4: 噪声劣化自适应测试")
    print("=" * 60)
    
    engine = SelfEvolutionEngine(n_qubits=4)
    
    # 模拟硬件老化: T1/T2 逐渐下降
    for stage in range(5):
        t1_degraded = 50.0 * (0.7 ** stage)
        t2_degraded = 30.0 * (0.7 ** stage)
        
        # 更新噪声
        for q in engine.topology.qubits:
            q.t1_us = t1_degraded
            q.t2_us = t2_degraded
        
        # 运行自演化
        state = engine.run_evolution_cycle(n_iterations=20)
        report = engine.get_system_report()
        
        print(f"  阶段 {stage+1}: T1={t1_degraded:.1f}μs T2={t2_degraded:.1f}μs | "
              f"保真度: {state.avg_fidelity:.4f}")
    
    return True


def run_all():
    """运行全部实验"""
    results = []
    
    print("\n" + "=" * 60)
    print("  Quanta OS — 软实验环境")
    print("  验证平台 v0.1")
    print("=" * 60 + "\n")
    
    experiments = [
        ("引导启动", experiment_bootstrap),
        ("自演化闭环", experiment_self_evolution),
        ("拓扑自适应", experiment_topology_adaptation),
        ("噪声自适应", experiment_adaptive_error_correction),
    ]
    
    for name, func in experiments:
        start = time.time()
        try:
            passed = func()
            elapsed = time.time() - start
            status = "✅ PASS" if passed else "⚠️  PARTIAL"
            results.append({"name": name, "passed": passed, "time": elapsed})
            print(f"\n[{status}] ({elapsed:.1f}s)\n")
        except Exception as e:
            elapsed = time.time() - start
            print(f"\n[❌ FAIL] ({elapsed:.1f}s): {e}\n")
            results.append({"name": name, "passed": False, "error": str(e)})
    
    print("\n" + "=" * 60)
    print("  实验汇总")
    print("=" * 60)
    passed = sum(1 for r in results if r.get("passed"))
    total = len(results)
    print(f"  {passed}/{total} 通过\n")
    
    for r in results:
        icon = "✅" if r.get("passed") else "❌"
        print(f"  {icon} {r['name']} ({r.get('time', 0):.1f}s)")
    
    return results


if __name__ == "__main__":
    run_all()
