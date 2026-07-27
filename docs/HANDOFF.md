# Handoff: Next Engineer

## Branch: next/ai-core-v3

This branch contains the completed Quanta OS v2 infrastructure.
Your mission: implement the AI-driven self-evolving kernel core.

### Current State
Done — Microkernel HAL (7 backends)
Done — Compilation pipeline (QASM 3.0 to pulses)
Done — Calibration subsystem (T1, T2-star, RB)
Done — Resource scheduler (3 priorities)
Done — FPGA pulse generation (Verilog)
Done — Integration tests (19 cases)

### Next Deliverable

1. **Self-Evolution Engine** (evolution-engine/)
   - Implement the self-evolve loop from evolution-engine/self_evolve.py
   - Connect pulse_optimizer.py to SPSA/GRAPE on real hardware
   - Hook calibration feedback into compiler parameter tuning

2. **QAIC (Quantum AI Core)**
   - RL agent for compiler strategy selection
   - Automatic backend rotation based on fidelity history
   - Predictive drift compensation

3. **Cluster Orchestration**
   - Multi-QPU job distribution (reference: QOS OSDI 25)
   - Dead qubit detection and automatic topology re-mapping

### Interface Summary

| Entry Point | Purpose |
|-------------|---------|
| quanta_os.py | Main API (compile, calibrate, status) |
| kernel/circuit_compiler.py | QASM to backend pulses |
| kernel/resource_scheduler.py | Job management |
| kernel/kalibrierung_protokoll.py | Calibration (German precision) |
| kernel/hal/origin_wukong_bridge.py | Origin Wukong 180 connection |
| evolution-engine/self_evolve.py | YOUR MODULE |

### Notes
- CMP 40HX GPU not needed for this phase
- Tests: python -m pytest tests/ -v
- Push commits as yourself — this is now your project too.
- Check docs/ then docs/research/ for context.

### Team

| Name | Code | Specialty |
|------|------|-----------|
| Dmitry Volkov (RU) | C | kernel, HAL, ZMQ |
| Jean-Luc Mercier (FR) | Python | algorithms, DFT |
| William Thorpe (UK) | Markdown | architecture docs |
| Klaus Weber (DE) | Python | calibration, noise |
| Wang Lei (CN) | Verilog/Python | FPGA, Wukong bridge |
| Priya Sharma (IN) | Python | testing |
| Alex Chen (US) | Python | integration, compiler |
| YOU | ??? | Self-Evolution Engine |
