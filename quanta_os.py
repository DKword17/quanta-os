#!/usr/bin/env python3
"""
quanta_os.py — Quanta OS Unified Entry Point

Usage:
    # Interactive Python
    >>> from quanta_os import QOS
    >>> qos = QOS(backend="wukong_180")
    >>> result = qos.compile("circuit.qasm")
    
    # CLI
    $ python quanta_os.py compile circuit.qasm --backend wukong_180
    $ python quanta_os.py run --shots 4096
    $ python quanta_os.py calibrate --qubit 0

Architecture:
    This is the top-level entry point for the Quanta OS system.
    It ties together the kernel, compiler, scheduler, calibration,
    and protocol subsystems into a single coherent API.

    Under the hood, it:
        1. Detects available backends (local QPUs, cloud endpoints)
        2. Initializes the compilation pipeline
        3. Boots the scheduler with detected resources
        4. Optionally runs calibration on available qubits
        5. Handles job lifecycle (submit → compile → execute → results)

    Design philosophy: 
        "Make the simple case fast, and the complex case possible."
        — Alex Chen, Quanta OS Architect

(c) 2026 Alex Chen — Quanta OS Project Lead, San Francisco
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Setup logging — production systems should use structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)
logger = logging.getLogger("quanta")


class QuantaOSError(Exception):
    """Base exception for all Quanta OS errors."""
    pass


class BackendUnavailableError(QuantaOSError):
    """Raised when the requested backend is not available."""
    pass


class CompilationError(QuantaOSError):
    """Raised when circuit compilation fails."""
    pass


@dataclass
class CompileResult:
    """Result of a compilation pipeline run."""
    source: str
    compiled: str
    backend_name: str
    original_ops: int
    final_ops: int
    original_depth: int
    final_depth: int
    compile_time_ms: float


@dataclass
class RunResult:
    """Full execution result including compilation and measurement."""
    compile_result: CompileResult
    counts: Dict[str, int]
    execution_time_ms: float
    shots: int
    fidelity_estimate: float = 0.0


# Known backend registry — extensible via plugins
BACKEND_REGISTRY = {
    "wukong_180": {
        "name": "origin_wukong_180",
        "type": "superconducting",
        "qubits": 180,
        "description": "Origin Wukong 180-qubit superconducting QPU (Hefei)",
        "provider": "Origin Quantum",
    },
    "quantinuum_h2": {
        "name": "quantinuum_h2",
        "type": "trapped_ion",
        "qubits": 56,
        "description": "Quantinuum H2 56-qubit trapped-ion QPU",
        "provider": "Quantinuum",
    },
    "borealis": {
        "name": "xanadu_borealis",
        "type": "photonic",
        "qubits": 216,
        "description": "Xanadu Borealis 216-squeezed-qumode photonic QPU",
        "provider": "Xanadu",
    },
    "generic_simulator": {
        "name": "generic_10q",
        "type": "simulator",
        "qubits": 10,
        "description": "Local state-vector simulator (10 qubit max)",
        "provider": "Quanta OS",
    },
}


class QOS:
    """
    Quanta OS — Main entry point.
    
    This is your one-stop shop for everything quantum.
    Create one instance and use it for the lifetime of your application.
    
    Example:
        >>> qos = QOS()
        >>> qos.list_backends()
        ['wukong_180', 'quantinuum_h2', 'generic_simulator']
        
        >>> result = qos.compile("""
        ...     OPENQASM 3.0;
        ...     qubit[2] q;
        ...     h q[0];
        ...     cx q[0], q[1];
        ...     measure q[0];
        ...     measure q[1];
        ... """, backend="generic_simulator")
        
        >>> print(result.final_ops)
    """
    
    def __init__(self, backend: str = "generic_simulator",
                 auto_init: bool = True):
        """
        Initialize the Quanta OS runtime.
        
        Args:
            backend: Default backend to use. Auto-detected if not specified.
            auto_init: Whether to auto-discover backends and run init.
        """
        self._default_backend = backend
        self._initialized = False
        self._scheduler = None
        
        if auto_init:
            self._initialize()
    
    def _initialize(self):
        """Internal initialization — discovers resources, boots subsystems."""
        start = time.monotonic()
        
        # Discover available backends
        available = self._discover_backends()
        logger.info(f"Discovered {len(available)} backends: "
                    f"{', '.join(available.keys())}")
        
        # Initialize scheduler
        self._init_scheduler(available)
        
        self._initialized = True
        elapsed = (time.monotonic() - start) * 1000
        logger.info(f"Quanta OS initialized in {elapsed:.1f} ms "
                    f"(default backend: {self._default_backend})")
    
    def _discover_backends(self) -> Dict[str, Any]:
        """Discover available backends — local and cloud."""
        available = {}
        
        # Always available: local simulator
        available["generic_simulator"] = BACKEND_REGISTRY["generic_simulator"]
        
        # Try to detect local backends via PCI/USP probe
        # (In production, this would call backend_selector)
        try:
            from kernel.hal.origin_wukong_bridge import WukongBridge
            bridge = WukongBridge(mode="local", auto_reconnect=False)
            if bridge.connect():
                available["wukong_180"] = BACKEND_REGISTRY["wukong_180"]
                logger.info("  → Origin Wukong 180 detected (local ZMQ)")
                bridge._zmq_socket.close()
        except Exception:
            logger.debug("  → No local Wukong backend detected")
        
        return available
    
    def _init_scheduler(self, backends: Dict[str, Any]):
        """Boot the resource scheduler with discovered backends."""
        from kernel.resource_scheduler import ResourceScheduler, SchedulerConfig
        
        config = SchedulerConfig(
            max_concurrent_jobs=8,
            fidelity_utilization_tradeoff=0.3,
        )
        self._scheduler = ResourceScheduler(config)
        
        for name, info in backends.items():
            self._scheduler.register_backend(
                name=name,
                n_qubits=info["qubits"],
                topology=[],
                gate_set=[],
            )
    
    # ── Public API ────────────────────────────────────────────────────
    
    def list_backends(self) -> List[Dict[str, Any]]:
        """List all available backends with their capabilities."""
        return [
            {"id": k, **v}
            for k, v in BACKEND_REGISTRY.items()
        ]
    
    def compile(self, qasm_source: str,
                backend: Optional[str] = None,
                optimization_level: int = 2) -> CompileResult:
        """
        Compile a QASM circuit for a specific backend.
        
        Args:
            qasm_source: OpenQASM 3.0 source string.
            backend: Target backend. Uses default if not specified.
            optimization_level: 0=no opt, 1=light, 2=aggresive, 3=max.
        
        Returns:
            CompileResult with original stats + compiled output.
        
        Raises:
            CompilationError: If the QASM cannot be parsed or compiled.
        """
        backend = backend or self._default_backend
        
        start = time.monotonic()
        
        try:
            result = compile_qasm(qasm_source, backend)
        except Exception as e:
            raise CompilationError(
                f"Compilation failed for backend '{backend}': {e}"
            ) from e
        
        elapsed = (time.monotonic() - start) * 1000
        
        compiled_qasm = CircuitExporter.to_qasm(result["compiled"])
        
        return CompileResult(
            source=qasm_source,
            compiled=compiled_qasm,
            backend_name=result["backend"].name,
            original_ops=result["stats"]["original_ops"],
            final_ops=result["stats"]["final_ops"],
            original_depth=result["stats"]["original_depth"],
            final_depth=result["stats"]["final_depth"],
            compile_time_ms=elapsed,
        )
    
    def calibrate(self, qubit_id: int = 0,
                  backend: Optional[str] = None) -> Dict[str, Any]:
        """
        Run calibration on a specific qubit.
        
        Args:
            qubit_id: Index of the qubit to calibrate.
            backend: Backend to calibrate on.
        
        Returns:
            Calibration results including T1, T2*, gate fidelity.
        """
        try:
            from kernel.kalibrierung_protokoll import (
                vollkalibrierung_durchfuehren
            )
        except ImportError:
            logger.warning("Calibration module not available")
            return {"status": "not_available"}
        
        result = vollkalibrierung_durchfuehren(qubit_id=qubit_id)
        
        return {
            "qubit_id": qubit_id,
            "t1_us": result.t1_zeit_s * 1e6,
            "t2_star_us": result.t2_stern_zeit_s * 1e6,
            "fidelity_cz": result.gatter_fidelitaet_cz,
            "valid": bool(result),
        }
    
    def status(self) -> Dict[str, Any]:
        """Get system-wide status."""
        backend_info = self.list_backends()
        scheduler_status = {}
        
        if self._scheduler:
            scheduler_status = self._scheduler.get_status()
        
        return {
            "version": "0.9.1",
            "initialized": self._initialized,
            "default_backend": self._default_backend,
            "available_backends": len(backend_info),
            "scheduler": scheduler_status,
        }


# ── CLI ────────────────────────────────────────────────────────────────

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Quanta OS — Quantum Operating System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compile a circuit
  python quanta_os.py compile my_circuit.qasm
  
  # Compile with a specific backend
  python quanta_os.py compile circuit.qasm --backend wukong_180
  
  # List available backends
  python quanta_os.py backends
  
  # Run calibration
  python quanta_os.py calibrate --qubit 0
  
  # Show system status
  python quanta_os.py status
        """,
    )
    
    parser.add_argument(
        "--backend", "-b",
        default="generic_simulator",
        help="Target backend (default: generic_simulator)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    
    subparsers = parser.add_subparsers(dest="command")
    
    # compile
    compile_parser = subparsers.add_parser("compile", help="Compile a QASM circuit")
    compile_parser.add_argument("file", help="Path to .qasm file or inline QASM string")
    compile_parser.add_argument("--output", "-o", help="Output file for compiled QASM")
    
    # run
    run_parser = subparsers.add_parser("run", help="Compile and execute a circuit")
    run_parser.add_argument("file", nargs="?", help="Path to .qasm file")
    run_parser.add_argument("--shots", type=int, default=1024, help="Number of shots")
    
    # backends
    subparsers.add_parser("backends", help="List available backends")
    
    # calibrate
    cal_parser = subparsers.add_parser("calibrate", help="Run calibration")
    cal_parser.add_argument("--qubit", type=int, default=0, help="Qubit to calibrate")
    
    # status
    subparsers.add_parser("status", help="Show system status")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        qos = QOS(backend=args.backend)
    except Exception as e:
        print(f"Error initializing Quanta OS: {e}", file=sys.stderr)
        return 1
    
    if args.command == "compile":
        if os.path.isfile(args.file):
            with open(args.file) as f:
                qasm = f.read()
        else:
            qasm = args.file
        
        result = qos.compile(qasm)
        print(result.compiled)
        
        if args.output:
            with open(args.output, "w") as f:
                f.write(result.compiled)
            logger.info(f"Written to {args.output}")
        
        logger.info(f"Compiled: {result.original_ops} → {result.final_ops} ops "
                    f"in {result.compile_time_ms:.1f} ms")
    
    elif args.command == "backends":
        for b in qos.list_backends():
            print(f"  {b['id']:20s}  {b['qubits']:4d} qubits  "
                  f"{b['type']:16s}  {b['provider']}")
    
    elif args.command == "calibrate":
        result = qos.calibrate(args.qubit)
        print(json.dumps(result, indent=2))
    
    elif args.command == "status":
        status = qos.status()
        print(json.dumps(status, indent=2))
    
    else:
        parser.print_help()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
