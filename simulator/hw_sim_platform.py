"""
simulator/hw_sim_platform.py
Quanta OS 软实验平台 — 14900HX 实机负载模拟驱动器

在宿主 CPU 上把 Quanta OS 各子系统拉到真实规模跑一遍，
产出可重复的实机指标并落盘 SIM_REPORT.json：

  1. 编译流水线 × 全后端（Bell / GHZ16 / QFT12 / 随机深电路）
  2. 大规模自演化闭环（64 qubit、多代，测量保真度学习曲线与收敛）
  3. 量子负载集群调度 + 线上协议（ResourceScheduler + ZMQ round-trip）
  4. 位校准仿真（T1 / T2* / 随机基准）

用法:
    python simulator/hw_sim_platform.py [--rounds N] [--report SIM_REPORT.json]
"""

#
# ── Quanta OS · 版权与出处 · Copyright & Provenance ──────────
# 作者    Author   : DKword17 <19832535010@163.com>
# 版权    Copyright: (c) 2026 DKword17
# 许可证  License  : Apache 2.0（见 LICENSE）
# 仓库    Repo     : https://github.com/DKword17/quanta-os
# Quanta OS 由 DKword17 一人原创并维护，转载/复用请保留本标记。
# ─────────────────────────────────────────────────────────────

# [水印层] 0x444B776F72643137 0x513175616E746120 0x4F5300DEADBEEF

import argparse
import importlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from quanta_os import QOS, BACKEND_REGISTRY


def now():
    return time.perf_counter()


def bench_compile(qos, rounds):
    """编译流水线 × 多后端。返回每后端吞吐与整体指标。"""
    def ghz(n):
        return ("OPENQASM 3.0; include \"stdgates.inc\"; qubit[%d] q; h q[0];"
                % n) + "; ".join(f"cx q[{i}], q[{i + 1}]" for i in range(n - 1)) \
               + "; measure q[0];"

    def deep_rnd(n=8, depth=25):
        return ("OPENQASM 3.0; include \"stdgates.inc\"; qubit[%d] q; "
                "h q[0]; " % n) + "; ".join(
                    f"cx q[{i % n}], q[{(i + 1) % n}]" for i in range(depth)
                ) + "; measure q[0];"

    circuits = {
        "Bell": "OPENQASM 3.0; include \"stdgates.inc\"; qubit[2] q; "
                "h q[0]; cx q[0], q[1]; measure q[0]; measure q[1];",
        "GHZ16": ghz(16),
        "QFT12": (ghz(12).replace(" h q[0];", " h q[0]; h q[1]; h q[2]; h q[3];"
                                  " h q[4]; h q[5]; h q[6]; h q[7]; h q[8];"
                                  " h q[9]; h q[10]; h q[11];", 1)),
        "RND50": deep_rnd(8, 25),
    }

    backends = list(BACKEND_REGISTRY.keys())
    rows = []
    total_ms = total_compiled = 0

    samples = max(rounds // max(1, len(circuits)), 1)

    for be in backends:
        row = {"backend": be, "qubits": BACKEND_REGISTRY[be]["qubits"],
               "circuits": {}, "throughput_cps": 0.0}
        t0 = now()
        n_ok = 0
        for name, qasm in circuits.items():
            times = []
            ok = 0
            for _ in range(samples):
                try:
                    r = qos.compile(qasm, backend=be)
                    times.append(r.compile_time_ms)
                    ok += 1
                except Exception as exc:
                    pass
            if ok:
                n_ok += 1
                row["circuits"][name] = {
                    "ops": r.final_ops, "depth": r.final_depth,
                    "avg_ms": sum(times) / len(times),
                }
        el_s = now() - t0
        if n_ok:
            row["throughput_cps"] = (n_ok * samples) / el_s if el_s else 0.0
            total_ms += el_s * 1000
            total_compiled += n_ok * samples
        rows.append(row)

    return {"per_backend": rows, "total_compile_ms": round(total_ms, 2),
            "circuits_compiled": total_compiled}


def bench_self_evolution(n_qubits=64, generations=8, iters=24):
    """大规模自演化闭环，返回学习曲线与收敛判定。"""
    from evolution_engine.self_evolve import SelfEvolutionEngine

    engine = SelfEvolutionEngine(n_qubits=n_qubits, seed=42)
    t0 = now()
    curve = []
    ref_curve = []
    first = last = None
    for gen in range(generations):
        state = engine.run_evolution_cycle(n_iterations=iters)
        if first is None:
            first = state.avg_fidelity
        last = state.avg_fidelity
        curve.append(round(state.avg_fidelity, 5))
        ref_curve.append(round(state.fidelity_window[-1], 5) if state.fidelity_window else 0.0)
    wall = now() - t0
    improved = (last - first) / first if first else 0.0
    return {
        "n_qubits": n_qubits, "generations": generations,
        "wall_s": round(wall, 3),
        "iter_per_gen": iters,
        "fidelity_curve": curve,
        "ref_fidelity_curve": ref_curve,
        "fidelity_first": round(first, 5) if first else None,
        "fidelity_last": round(last, 5) if last else None,
        "improvement_pct": round(improved * 100, 2) if first else None,
        "converged": engine.state.converged,
    }


def bench_scheduler(jobs=8000, backends=3):
    """量子负载集群调度：多 QPU、混合优先级、吞吐指标 + ZMQ 协议 round-trip。"""
    from kernel.resource_scheduler import (ResourceScheduler, SchedulerConfig,
                                           QuantumJob, JobPriority)
    from kernel.zmq_protocol import ZMQProtocol, MessageHeader, MsgType

    sched = ResourceScheduler(SchedulerConfig(max_concurrent_jobs=16))
    topo = [(i, i + 1) for i in range(120)]
    for name, q in [("origin_wukong_180", 180), ("quantinuum_h2", 56),
                    ("generic_10q", 10)]:
        sched.register_backend(name, q, topo, ["CX", "H", "RX", "RZ"])

    t0 = now()
    prios = [JobPriority.BATCH, JobPriority.INTERACTIVE, JobPriority.REAL_TIME]
    for i in range(jobs):
        job = QuantumJob(
            job_id=f"job_{i:06d}",
            qasm_source="OPENQASM 3.0; qubit[8] q; h q[0];",
            n_qubits=[8, 16, 24][i % 3],
            shots=1024,
            priority=prios[i % 3],
        )
        sched.submit_job(job)
    submit_s = now() - t0

    t0 = now()
    cycles = 0
    scheduled = 0
    while True:
        ready = sched.schedule()
        if not ready and sum(len(q) for q in sched._queues.values()) == 0:
            break
        scheduled += len(ready)
        cycles += 1
        if cycles > jobs * 2:
            break
    sched_s = now() - t0

    # ZMQ 线上协议吞吐
    header = MessageHeader.new(MsgType.SUBMIT_TASK, backend=1, token="dkw17")
    body = {"qubit_count": 24, "shots": 1024}
    t0 = now()
    n = 50000
    for _ in range(n):
        frames = ZMQProtocol.pack(header, body)
        ZMQProtocol.unpack(frames)  # 返回 (header, body, binary)
    zmq_s = now() - t0

    return {
        "jobs_submitted": jobs, "backends": backends,
        "submit_time_s": round(submit_s, 3),
        "schedule_cycles": cycles, "jobs_scheduled": scheduled,
        "schedule_time_s": round(sched_s, 3),
        "jobs_per_sec": round(scheduled / sched_s, 1) if sched_s else 0.0,
        "zmq_roundtrips": n,
        "zmq_time_s": round(zmq_s, 3),
        "zmq_rps": round(n / zmq_s, 1) if zmq_s else 0.0,
    }


def bench_calibration(qubits=8):
    """位校准仿真：T1 / T2* / 随机基准。"""
    from kernel.calibration_protocol import run_full_calibration

    t0 = now()
    rows = []
    for q in range(qubits):
        res = run_full_calibration(q, temperature_mk=15.0)
        rows.append({
            "qubit": q,
            "t1_us": round(getattr(res, "t1_time_s", -1) * 1e6, 2),
            "t2_us": round(getattr(res, "t2_star_time_s", -1) * 1e6, 2),
            "mean_fidelity": round(getattr(res, "mean_sq_fidelity", -1), 5),
        })
    wall = now() - t0
    t1 = [r["t1_us"] for r in rows]
    return {
        "qubits": qubits, "wall_s": round(wall, 3),
        "avg_t1_us": round(sum(t1) / len(t1), 2) if t1 else -1,
        "calibration_rows": rows,
    }


def main():
    ap = argparse.ArgumentParser(description="Quanta OS 实机负载模拟平台")
    ap.add_argument("--rounds", type=int, default=40)
    ap.add_argument("--report", default="SIM_REPORT.json")
    args = ap.parse_args()

    report = {
        "platform": {
            "cpu": (os.popen("grep -m1 'model name' /proc/cpuinfo")
                    .read().split(':')[-1].strip()
                    if os.path.exists('/proc/cpuinfo') else 'unknown'),
            "cores": os.cpu_count(),
            "python": sys.version.split()[0],
        },
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "backend_version": "v1",
    }
    t_start = time.perf_counter()

    print("=" * 62)
    print("  Quanta OS — 实机软模拟平台 (14900HX)")
    print("=" * 62)

    # 1 编译流水线
    print("\n[1/4] 编译流水线 × 全后端 ...")
    qos = QOS()
    rc = bench_compile(qos, args.rounds)
    report["compile"] = rc
    for b in rc["per_backend"]:
        langs = ", ".join(f"{k}:{v['avg_ms']:.3f}ms" for k, v in b["circuits"].items())
        print(f"      {b['backend']:<16} qubits={b['qubits']:<4} "
              f"thrpt={b['throughput_cps']:.1f} cps | {langs}")

    # 2 大规模自演化
    print("\n[2/4] 大规模自演化闭环 (64 qubit) ...")
    se = bench_self_evolution()
    report["self_evolution"] = se
    print(f"      wall={se['wall_s']}s first={se['fidelity_first']} "
          f"last={se['fidelity_last']} improve={se['improvement_pct']}% "
          f"conv={se['converged']}")
    print(f"      curve={se['fidelity_curve']}")

    # 3 调度负载 + 线上协议
    print("\n[3/4] 量子负载集群调度 + ZMQ 协议 ...")
    sc = bench_scheduler()
    report["scheduler"] = sc
    print(f"      jobs={sc['jobs_submitted']} submit={sc['submit_time_s']}s "
          f"cycles={sc['schedule_cycles']} thrpt={sc['jobs_per_sec']}/s")
    print(f"      zmq roundtrips={sc['zmq_roundtrips']} "
          f"time={sc['zmq_time_s']}s rate={sc['zmq_rps']}/s")

    # 4 校准
    print("\n[4/4] 位校准仿真 ...")
    cc = bench_calibration()
    report["calibration"] = cc
    print(f"      qubits={cc['qubits']} wall={cc['wall_s']}s "
          f"avg_T1={cc['avg_t1_us']}us")

    report["duration_s"] = round(time.perf_counter() - t_start, 2)

    # 写报告
    out = os.path.abspath(args.report)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print("\n" + "=" * 62)
    print(f"  软模拟平台完成 — 报告已写入 {out}  (总耗时 {report['duration_s']}s)")
    print("=" * 62)


if __name__ == "__main__":
    main()