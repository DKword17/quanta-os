# Handoff: Next Engineer

## Branch: next/ai-core-v3

This branch contains the completed Quanta OS v2 infrastructure.
The AI-driven self-evolving kernel core is the next deliverable.

## Current State
- Microkernel HAL (7 backends) — complete
- Compilation pipeline (QASM 3.0 → pulses) — complete
- Calibration subsystem (T1, T2*, RB) — complete
- Resource scheduler (3 priorities) — complete
- FPGA pulse generation (Verilog) — complete
- Integration tests (19 cases) — all passing

## Next Deliverable

1. **Self-Evolution Engine** (`evolution-engine/`)
   - Implement the self-evolve loop from `evolution-engine/self_evolve.py`
   - Connect `pulse_optimizer.py` to SPSA/GRAPE on real hardware
   - Hook calibration feedback into compiler parameter tuning

2. **QAIC (Quantum AI Core)**
   - RL agent for compiler strategy selection
   - Automatic backend rotation based on fidelity history
   - Predictive drift compensation

3. **Cluster Orchestration**
   - Multi-QPU job distribution
   - Dead qubit detection and automatic topology re-mapping

## Interface Summary

| Entry Point | Purpose |
|-------------|---------|
| `quanta_os.py` | Main API (compile, calibrate, status) |
| `kernel/circuit_compiler.py` | QASM → backend pulses |
| `kernel/resource_scheduler.py` | Job management |
| `kernel/calibration_protocol.py` | Calibration (T1, T2*, RB) |
| `kernel/hal/origin_wukong_bridge.py` | Origin Wukong 180 connection |
| `evolution-engine/self_evolve.py` | YOUR MODULE |

## Notes
- CMP 40HX GPU not needed for this phase
- Tests: `python -m pytest tests/ -v`
- Push commits as yourself — this is now your project too.
- Check `docs/` and `docs/research/` for context.
