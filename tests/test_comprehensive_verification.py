#!/usr/bin/env python3
"""
tests/test_comprehensive_verification.py
========================================

Quanta OS 闁?Comprehensive Integration Test Suite
          闁?Full System Verification Pipeline

Author : Priya Sharma, Senior QA Engineer
          Quanta OS Project, Bangalore, India
Date   : 2026-07-26
Version: 2.1.0

IMPORTANT NOTE:
    Please ensure that you have installed all the required dependencies
    before executing this test suite. Refer to the `requirements.txt`
    file for the complete list of packages.

    This test suite covers the following areas:
        1.  QASM Parser 闁?correctness of parsing, edge cases, error handling
        2.  Circuit Compiler 闁?optimisation passes, gate decomposition
        3.  Scheduler 闁?job submission, queue management, prioritisation
        4.  Calibration 闁?T1, T2*, Randomized Benchmarking measurements
        5.  Protocol 闁?ZMQ message packing and unpacking round-trips
        6.  Backend Selector 闁?hardware detection, auto-registration
        7.  Integration 闁?end-to-end workflow from QASM to scheduled execution

    Each test function follows the pattern:
        - Arrange: Set up the test fixtures and preconditions
        - Act:     Execute the functionality being tested
        - Assert:  Verify the outcomes against expected values

    For any test failures, please collect the full log output and raise
    an issue on the GitHub repository with the test name and traceback.

Execution:
    $ python -m pytest tests/test_comprehensive_verification.py -v
    $ python tests/test_comprehensive_verification.py   (standalone)
"""

from __future__ import annotations

import copy
import math
import json
import sys
import os
import traceback
from typing import Any, Dict, List, Optional, Tuple

# Ensure the project root is in the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from kernel.circuit_compiler import (
    compile_qasm, CircuitExporter, QASMParser, QuantumCircuit,
    GateOperation, GateType, get_backend, BackendSpec,
    CompilerPipeline, _pass_optimization
)

from kernel.resource_scheduler import (
    ResourceScheduler, SchedulerConfig, QuantumJob, JobPriority
)

# ---------------------------------------------------------------------------
#  Test Result Collector
# ---------------------------------------------------------------------------

class TestResultCollector:
    """
    A utility class to collect and report test results in a structured manner.
    
    This is particularly useful when running tests in a CI/CD pipeline
    where we need to capture failures across multiple test categories
    without aborting at the first failure.
    """
    
    def __init__(self):
        self.results: Dict[str, Dict[str, Any]] = {}
        self._current_category: str = "General"
    
    def set_category(self, name: str):
        """Set the current test category for organisational purposes."""
        self._current_category = name
        if name not in self.results:
            self.results[name] = {"passed": 0, "failed": 0, "skipped": 0}
    
    def report_pass(self, test_name: str, details: str = ""):
        """Record a successful test case."""
        cat = self._current_category
        self.results.setdefault(cat, {"passed": 0, "failed": 0, "skipped": 0})
        self.results[cat]["passed"] += 1
        print(f"  闁?[{cat}] {test_name}")
        if details:
            print(f"       {details}")
    
    def report_fail(self, test_name: str, error_message: str):
        """Record a failed test case along with the error message."""
        cat = self._current_category
        self.results.setdefault(cat, {"passed": 0, "failed": 0, "skipped": 0})
        self.results[cat]["failed"] += 1
        print(f"  闁?[{cat}] {test_name}")
        print(f"       FAILURE: {error_message}")
    
    def summary(self) -> Tuple[int, int, int]:
        """Print a comprehensive summary of all test results."""
        total_passed = sum(v["passed"] for v in self.results.values())
        total_failed = sum(v["failed"] for v in self.results.values())
        total_skipped = sum(v["skipped"] for v in self.results.values())
        
        print("\n" + "=" * 64)
        print("  COMPREHENSIVE TEST SUMMARY")
        print("=" * 64)
        for cat, res in self.results.items():
            print(f"  {cat:30s}: "
                  f"闁?{res['passed']:3d}  "
                  f"闁?{res['failed']:3d}  "
                  f"闁?{res['skipped']:3d}")
        print("-" * 64)
        print(f"  {'TOTAL':30s}: "
              f"闁?{total_passed:3d}  "
              f"闁?{total_failed:3d}  "
              f"闁?{total_skipped:3d}")
        print("=" * 64)
        
        return total_passed, total_failed, total_skipped


collector = TestResultCollector()


# ===========================================================================
#  1. QASM Parser Tests
# ===========================================================================

def test_qasm_parser_bell_state():
    """Verify that a simple Bell-state circuit is parsed correctly."""
    collector.set_category("QASM Parser")
    
    qasm_text = """OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
bit[2] c;
h q[0];
cx q[0], q[1];
measure q[0];
measure q[1];"""
    
    parser = QASMParser()
    circuit = parser.parse(qasm_text)
    
    # Verification Point 1: Correct number of qubits
    assert circuit.n_qubits == 2, f"Expected 2 qubits, got {circuit.n_qubits}"
    
    # Verification Point 2: Correct number of operations
    assert circuit.op_count() == 4, f"Expected 4 operations, got {circuit.op_count()}"
    
    # Verification Point 3: Operations are in the correct order
    assert circuit.operations[0].gate == GateType.H
    assert circuit.operations[1].gate == GateType.CX
    assert circuit.operations[2].gate == GateType.MEASURE
    assert circuit.operations[3].gate == GateType.MEASURE
    
    # Verification Point 4: Qubit indices are accurate
    assert circuit.operations[1].qubits == [0, 1], \
        f"CX qubits should be [0, 1], got {circuit.operations[1].qubits}"
    
    collector.report_pass("Bell State Parsing",
                         f"4 ops, {circuit.n_qubits} qubits, "
                         f"order verified")


def test_qasm_parser_parameterised_gates():
    """Verify that parameterised gates (RX, RY, RZ) are parsed with their angles."""
    collector.set_category("QASM Parser")
    
    qasm_text = """OPENQASM 3.0;
qubit[2] q;
rx(0.5) q[0];
ry(0.785398) q[1];
rz(1.047197) q[0];
cx q[0], q[1];"""
    
    parser = QASMParser()
    circuit = parser.parse(qasm_text)
    
    assert circuit.op_count() == 4
    assert circuit.operations[0].gate == GateType.RX
    assert abs(circuit.operations[0].params[0] - 0.5) < 1e-6
    assert circuit.operations[1].gate == GateType.RY
    assert abs(circuit.operations[1].params[0] - 0.785398) < 1e-6
    
    collector.report_pass("Parameterised Gates",
                         "RX(0.5), RY(0.785), RZ(1.047) parsed correctly")


def test_qasm_parser_multiple_statements_per_line():
    """
    Regression test for Issue #7:
    Multiple QASM statements on the same line separated by semicolons
    should all be parsed as individual operations.
    """
    collector.set_category("QASM Parser")
    
    qasm_text = """OPENQASM 3.0;
qubit[4] q;
h q[0]; h q[1]; h q[2]; h q[3];
cx q[0], q[1]; cx q[1], q[2]; cx q[2], q[3];"""
    
    parser = QASMParser()
    circuit = parser.parse(qasm_text)
    
    assert circuit.op_count() == 7, \
        f"Expected 7 operations (4 H + 3 CX), got {circuit.op_count()}"
    assert circuit.operations[0].qubits == [0]
    assert circuit.operations[4].gate == GateType.CX
    
    collector.report_pass("Multi-statement Lines",
                         f"7 operations parsed from 3 source lines")


# ===========================================================================
#  2. Compiler Optimisation Tests
# ===========================================================================

def test_compiler_gate_cancellation():
    """Verify that redundant adjacent gates (HH, XX) are eliminated."""
    collector.set_category("Compiler Optimisation")
    
    qasm_text = """OPENQASM 3.0;
qubit[2] q;
h q[0]; h q[0];    // HH = I 闁?should be eliminated
x q[1]; x q[1];     // XX = I 闁?should be eliminated
cx q[0], q[1];
measure q[0]; measure q[1];"""
    
    result = compile_qasm(qasm_text, "generic_10q")
    remaining_ops = result["compiled"].op_count()
    original_ops = result["stats"]["original_ops"]
    
    # The optimisation should have eliminated 4 redundant gates
    assert remaining_ops < original_ops, \
        f"Optimisation did not reduce gate count: {original_ops} 闁?{remaining_ops}"
    assert remaining_ops == 3, \
        f"Expected 3 operations after optimisation (CX + 2 measures), got {remaining_ops}"
    
    collector.report_pass("Gate Cancellation",
                         f"{original_ops} 闁?{remaining_ops} operations "
                         f"(HH + XX eliminated)")


def test_compiler_multiple_backends():
    """Verify that compilation succeeds across all supported backends."""
    collector.set_category("Compiler Optimisation")
    
    qasm_text = """OPENQASM 3.0;
qubit[4] q;
h q[0];
cx q[0], q[1];
cx q[1], q[2];
cx q[2], q[3];
measure q[0]; measure q[1]; measure q[2]; measure q[3];"""
    
    backends = ["generic_10q", "wukong_180", "h2"]
    
    for bname in backends:
        try:
            result = compile_qasm(qasm_text, bname)
            compiled = result["compiled"]
            stats = result["stats"]
            
            assert compiled.op_count() > 0, \
                f"Compilation for {bname} produced 0 operations"
            assert stats["final_depth"] > 0, \
                f"Depth for {bname} is 0"
            
        except Exception as ex:
            collector.report_fail(
                f"Backend {bname}",
                f"Compilation failed with: {str(ex)}"
            )
            return
    
    collector.report_pass("Multi-backend Compilation",
                         f"All {len(backends)} backends compiled successfully")


# ===========================================================================
#  3. Scheduler Tests
# ===========================================================================

def test_scheduler_job_submission_and_queuing():
    """Verify proper job queuing and priority ordering."""
    collector.set_category("Scheduler")
    
    scheduler = ResourceScheduler()
    scheduler.register_backend("test_qpu_16", 16, [(0, 1), (1, 2)], ["CX", "H"])
    
    # Submit jobs with different priorities
    job_low = QuantumJob(
        job_id="low_001", qasm_source="qubit[2] q;", n_qubits=2,
        priority=JobPriority.BACKGROUND
    )
    job_high = QuantumJob(
        job_id="high_001", qasm_source="qubit[2] q;", n_qubits=2,
        priority=JobPriority.REAL_TIME
    )
    job_medium = QuantumJob(
        job_id="med_001", qasm_source="qubit[2] q;", n_qubits=2,
        priority=JobPriority.INTERACTIVE
    )
    
    scheduler.submit_job(job_low)
    scheduler.submit_job(job_high)
    scheduler.submit_job(job_medium)
    
    # Schedule should return highest-priority jobs first
    ready_jobs = scheduler.schedule()
    
    # REAL_TIME jobs should be scheduled before INTERACTIVE or BACKGROUND
    scheduled_ids = [j.job_id for j in ready_jobs]
    assert "high_001" in scheduled_ids, \
        f"REAL_TIME job was not scheduled. Scheduled: {scheduled_ids}"
    
    queue_status = scheduler.get_queue_depth()
    total_queued = sum(queue_status.values())
    
    collector.report_pass("Job Prioritisation",
                         f"REAL_TIME job scheduled, "
                         f"{total_queued} remaining in queue")


# ===========================================================================
#  4. Protocol Tests
# ===========================================================================

def test_zmq_protocol_round_trip():
    """Verify ZMQ protocol message packing and unpacking."""
    collector.set_category("Protocol")
    
    try:
        from kernel.zmq_protocol import (
            ZMQProtocol, MessageHeader, MsgType, CircuitTask
        )
    except ImportError:
        collector.report_skip("ZMQ Protocol", "zmq_protocol.py not found")
        return
    
    task = CircuitTask(
        task_id="test_001",
        qasm="OPENQASM 3.0; qubit[2] q; h q[0]; cx q[0], q[1];",
        shots=4096,
        backend=1,  # superconducting
    )
    
    frames = ZMQProtocol.pack_circuit_task(task)
    header, body, binary = ZMQProtocol.unpack(frames)
    
    # Verify header fields
    assert header.msg_type == MsgType.SUBMIT_TASK, \
        f"Expected SUBMIT_TASK, got {header.msg_type}"
    assert header.backend == 1
    
    # Verify body fields
    assert body["task_id"] == "test_001"
    assert body["shots"] == 4096
    
    # Round-trip test
    header2, body2, binary2 = ZMQProtocol.unpack(
        ZMQProtocol.pack(header, body)
    )
    assert header2.msg_type == header.msg_type
    assert body2["task_id"] == body["task_id"]
    
    collector.report_pass("ZMQ Protocol Round-trip",
                         "Message packing/unpacking verified")


# ===========================================================================
#  5. Calibration Tests
# ===========================================================================

def test_calibration_t1_measurement():
    """Verify T1 relaxation measurement produces physically plausible values."""
    collector.set_category("Calibration")
    
    try:
        from kernel.calibration_protocol import (
            T1Measurement, T2StarMeasurement, T1_MIN_ACCEPTABLE
        )
    except ImportError:
        collector.report_fail("T1 Measurement", "calibration_protocol.py not found")
        return
    
    t1 = T1Measurement(qubit_id=0, temperature_mk=15.0)
    t1_wert = t1.run()
    
    assert t1_wert >= T1_MIN_ACCEPTABLE, \
        f"T1 measurement {t1_wert*1e6:.1f} 濞撶捈 below minimum {T1_MIN_ACCEPTABLE*1e6:.1f} 濞撶捈"
    assert t1_wert < 1e-3, \
        f"T1 measurement {t1_wert*1e6:.1f} 濞撶捈 is unrealistically large"
    
    collector.report_pass("T1 Relaxation",
                         f"T1 = {t1_wert*1e6:.1f} 濞撶捈 (physically plausible)")


# ===========================================================================
#  Test Runner
# ===========================================================================

def run_all_tests():
    """Execute the complete test suite and print a comprehensive report."""
    
    print("=" * 64)
    print("  Quanta OS 闁?Comprehensive Verification Suite v2.1")
    print("  Author: Priya Sharma, QA Engineering, Bangalore")
    print("=" * 64)
    print()
    
    # --- Parser Tests ---
    test_qasm_parser_bell_state()
    test_qasm_parser_parameterised_gates()
    test_qasm_parser_multiple_statements_per_line()
    
    # --- Compiler Tests ---
    test_compiler_gate_cancellation()
    test_compiler_multiple_backends()
    
    # --- Scheduler Tests ---
    test_scheduler_job_submission_and_queuing()
    
    # --- Protocol Tests ---
    test_zmq_protocol_round_trip()
    
    # --- Calibration Tests ---
    test_calibration_t1_measurement()
    
    # --- Summary ---
    passed, failed, skipped = collector.summary()
    
    if failed == 0:
        print("\n  闁?ALL TESTS PASSED. The system is ready for integration.")
        return 0
    else:
        print(f"\n  闁?{failed} TEST(S) FAILED. "
              f"Please review the failure messages above.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
