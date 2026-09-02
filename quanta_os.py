#!/usr/bin/env python3
"""
quanta_os.py - Quanta OS unified entry point.

Usage:
    # Interactive Python
    >>> from quanta_os import QOS
    >>> qos = QOS(backend="generic_simulator")
    >>> qasm = 'OPENQASM 3.0; include "stdgates.inc"; qubit[2] q; h q[0]; cx q[0], q[1]; measure q[0]; measure q[1];'
    >>> result = qos.compile(qasm)
    >>> print(result.final_ops)

    # CLI
    $ python quanta_os.py compile circuit.qasm --backend wukong_180
    $ python quanta_os.py calibrate --qubit 0
    $ python quanta_os.py list-backends

Architecture:
    Top-level entry point for Quanta OS. Ties together the kernel compiler,
    scheduler and calibration subsystems behind a single coherent API.
"""
# (c) 2026 DKword17 - 水印校验码: 0x444B776F72643137

from __future__ import annotations

# 完整性校验（水印层）
from _provenance import check_authenticity, _INTEGRITY_OK, _WATERMARK_A, _WATERMARK_B
_authentic, _tampered = check_authenticity()
if not _authentic:
    import warnings as _w
    _w.warn("Quanta OS 完整性校验失败：代码可能已被篡改。", RuntimeWarning)

#
# ─────────────────────────────────────────────────────────────
# Quanta OS — 版权与出处  |  Copyright & Provenance
# 作者    Author   : DKword17 <19832535010@163.com>
# 版权    Copyright: (c) 2026 DKword17
# 许可证  License  : Apache 2.0（见 LICENSE）
# 仓库    Repo     : https://github.com/DKword17/quanta-os
# Quanta OS 由 DKword17 一人原创并维护，转载/复用请保留本标记。
# ─────────────────────────────────────────────────────────────

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)
logger = logging.getLogger("quanta")


class QuantaOSError(Exception):
    """Base exception for all Quanta OS errors."""


class BackendUnavailableError(QuantaOSError):
    """Raised when the requested backend is not available."""


class CompilationError(QuantaOSError):
    """Raised when circuit compilation fails."""


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


# Known backend registry. Keys map to `kernel.circuit_compiler.get_backend()`
# names via _BACKEND_IMPL (any other key falls back to the generic simulator).
BACKEND_REGISTRY: Dict[str, Dict[str, Any]] = {
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
        "description": "Xanadu Borealis 216-qumode photonic QPU",
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

# registry key -> kernel backend name understood by compile_qasm()
_BACKEND_IMPL = {
    "wukong_180": "wukong_180",
    "quantinuum_h2": "h2",
    "borealis": "borealis",
}


def _resolve_backend(backend: Optional[str]) -> str:
    """Map a registry key to the kernel backend name (generic fallback)."""
    if not backend:
        return "generic_simulator"
    if backend not in BACKEND_REGISTRY:
        raise BackendUnavailableError(
            f"Unknown backend '{backend}'. Known: {', '.join(BACKEND_REGISTRY)}"
        )
    return _BACKEND_IMPL.get(backend, "generic_simulator")


def _kernel_compile(qasm_source: str, backend_impl: str) -> dict:
    """Compile through kernel.circuit_compiler (lazy import)."""
    try:
        from kernel.circuit_compiler import compile_qasm, CircuitExporter
    except Exception as exc:  # pragma: no cover - environment guard
        raise QuantaOSError(
            "kernel package not importable; run from the quanta-os repo root"
        ) from exc
    return compile_qasm(qasm_source, backend_impl), CircuitExporter


class QOS:
    """
    Quanta OS main entry point.

    Create one instance and reuse it for the lifetime of the application.

    Example:
        >>> qos = QOS()
        >>> qos.list_backends()
        ['wukong_180', 'quantinuum_h2', 'borealis', 'generic_simulator']
    """

    def __init__(self, backend: str = "generic_simulator"):
        self._default_backend = backend
        if backend not in BACKEND_REGISTRY:
            raise BackendUnavailableError(
                f"Unknown backend '{backend}'. Known: {', '.join(BACKEND_REGISTRY)}"
            )
        logger.info("Quanta OS ready (default backend: %s)", backend)

    def list_backends(self) -> List[str]:
        """List all known backend registry keys."""
        return list(BACKEND_REGISTRY.keys())

    def backend_info(self, backend: Optional[str] = None) -> Dict[str, Any]:
        """Return metadata for a backend (defaults to the instance default)."""
        return dict(BACKEND_REGISTRY[backend or self._default_backend])

    def compile(
        self,
        qasm_source: str,
        backend: Optional[str] = None,
    ) -> CompileResult:
        """
        Compile an OpenQASM 3.0 circuit for a backend.

        Args:
            qasm_source: OpenQASM 3.0 source string.
            backend: Registry key; falls back to the instance default.

        Returns:
            CompileResult with original/final stats and compiled QASM.

        Raises:
            CompilationError: if the QASM cannot be parsed or compiled.
        """
        backend = backend or self._default_backend
        impl = _resolve_backend(backend)
        start = time.monotonic()
        try:
            result, _ = _kernel_compile(qasm_source, impl)
        except Exception as exc:
            raise CompilationError(
                f"Compilation failed for backend '{backend}': {exc}"
            ) from exc
        elapsed = (time.monotonic() - start) * 1000

        compiled = result["compiled"]
        compiled_qasm = _export_qasm(compiled)
        stats = result["stats"]
        return CompileResult(
            source=qasm_source,
            compiled=compiled_qasm,
            backend_name=result["backend"].name,
            original_ops=stats["original_ops"],
            final_ops=stats["final_ops"],
            original_depth=stats["original_depth"],
            final_depth=stats["final_depth"],
            compile_time_ms=round(elapsed, 3),
        )

    def calibrate(
        self,
        qubit_id: int = 0,
        backend: Optional[str] = None,
        temperature_mk: float = 15.0,
    ) -> Dict[str, Any]:
        """
        Run the full calibration sequence (T1 -> T2* -> RB) on a qubit.

        Args:
            qubit_id: Qubit index on the chip.
            backend: Registry key (informational for now).
            temperature_mk: Mixing chamber temperature in mK.

        Returns:
            Calibration metrics as a JSON-safe dict.
        """
        try:
            from kernel.calibration_protocol import run_full_calibration
        except Exception as exc:  # pragma: no cover
            raise QuantaOSError(
                "kernel package not importable; run from the quanta-os repo root"
            ) from exc

        backend = backend or self._default_backend
        logger.info(
            "Calibrating %s qubit %d at %.1f mK", backend, qubit_id, temperature_mk
        )
        result = run_full_calibration(
            qubit_id=qubit_id, temperature_mk=temperature_mk
        )
        from dataclasses import asdict

        payload = asdict(result)
        payload["backend"] = backend
        return payload


def _export_qasm(circuit: Any) -> str:
    """Serialize a compiled circuit back to OpenQASM 3.0."""
    try:
        from kernel.circuit_compiler import CircuitExporter
    except Exception as exc:  # pragma: no cover
        raise QuantaOSError("kernel not importable") from exc
    return CircuitExporter.to_qasm(circuit)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
_SAMPLE_QASM = """OPENQASM 3.0;
include "stdgates.inc";
qubit[3] q;
h q[0];
cx q[0], q[1];
cx q[1], q[2];
measure q[0];
measure q[1];
measure q[2];"""


def _cmd_compile(args: argparse.Namespace) -> int:
    if args.file and args.file != "-":
        with open(args.file, encoding="utf-8") as fh:
            source = fh.read()
    else:
        source = _SAMPLE_QASM
    qos = QOS(backend=args.backend)
    result = qos.compile(source)
    if getattr(args, 'json', False):
        print(json.dumps({
            "backend": result.backend_name,
            "original_ops": result.original_ops,
            "final_ops": result.final_ops,
            "original_depth": result.original_depth,
            "final_depth": result.final_depth,
            "compile_time_ms": result.compile_time_ms,
            "compiled": result.compiled,
        }, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"// backend: {result.backend_name}")
        print(f"// ops: {result.original_ops} -> {result.final_ops}")
        print(f"// depth: {result.original_depth} -> {result.final_depth}")
        print(f"// {result.compile_time_ms} ms")
        print(result.compiled)
    return 0


def _cmd_calibrate(args: argparse.Namespace) -> int:
    qos = QOS(backend=args.backend)
    payload = qos.calibrate(qubit_id=args.qubit, temperature_mk=getattr(args, 'temp', 15.0))
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    qos = QOS()
    if getattr(args, 'json', False):
        backends = {k: dict(v) for k, v in BACKEND_REGISTRY.items()}
        print(json.dumps(backends, ensure_ascii=False, indent=2, default=str))
    else:
        print("\n".join(qos.list_backends()))
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    """Show system information."""
    import sys as _sys
    from _provenance import _INTEGRITY_OK
    if getattr(args, 'json', False):
        print(json.dumps({
            "version": "0.4.0",
            "python": f"{_sys.version_info.major}.{_sys.version_info.minor}.{_sys.version_info.micro}",
            "backends": len(BACKEND_REGISTRY),
            "backend_list": list(BACKEND_REGISTRY.keys()),
            "integrity": bool(_INTEGRITY_OK),
        }, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"Quanta OS v0.4.0")
        print(f"Python: {_sys.version_info.major}.{_sys.version_info.minor}.{_sys.version_info.micro}")
        print(f"Backends: {len(BACKEND_REGISTRY)} ({', '.join(BACKEND_REGISTRY.keys())})")
        print(f"Integrity: {'OK' if _INTEGRITY_OK else 'FAILED'}")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    """Start the REST API server."""
    from quanta_api import main as _api_main
    return _api_main([f"--port={args.port}", f"--host={args.host}"])


def _cmd_run(args: argparse.Namespace) -> int:
    """Run full test suite: compile + calibrate + benchmark."""
    import time as _time
    qos = QOS(backend=args.backend)

    if args.file and args.file != "-":
        with open(args.file, encoding="utf-8") as fh:
            source = fh.read()
    else:
        source = _SAMPLE_QASM

    results = {}
    t0 = _time.perf_counter()

    # 1. Compile
    result = qos.compile(source)
    results["compile"] = {
        "backend": result.backend_name,
        "ops": f"{result.original_ops} -> {result.final_ops}",
        "depth": f"{result.original_depth} -> {result.final_depth}",
        "time_ms": result.compile_time_ms,
    }

    # 2. Calibrate
    cal = qos.calibrate(qubit_id=0)
    results["calibrate"] = {
        "t1_us": round(cal.get("t1_time_s", 0) * 1e6, 1),
        "t2_us": round(cal.get("t2_star_time_s", 0) * 1e6, 1),
    }

    # 3. Benchmark (compile 3 circuits)
    benchmarks = []
    for name, qasm in [("Bell", "OPENQASM 3.0; include \"stdgates.inc\"; qubit[2] q; h q[0]; cx q[0], q[1]; measure q[0]; measure q[1];"),
                        ("GHZ4", "OPENQASM 3.0; include \"stdgates.inc\"; qubit[4] q; h q[0]; cx q[0], q[1]; cx q[1], q[2]; cx q[2], q[3]; measure q[0];")]:
        r = qos.compile(qasm)
        benchmarks.append({"circuit": name, "time_ms": r.compile_time_ms})
    results["benchmark"] = benchmarks

    wall = _time.perf_counter() - t0
    results["wall_s"] = round(wall, 3)

    if getattr(args, 'json', False):
        print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
    else:
        print("=== Quanta OS Run Report ===")
        print(f"Backend: {result.backend_name}")
        print(f"Compile: {result.compile_time_ms} ms ({result.original_ops} ops)")
        print(f"Calibrate: T1={results['calibrate']['t1_us']}us T2={results['calibrate']['t2_us']}us")
        bench_str = ", ".join(f'{b["circuit"]}={b["time_ms"]}ms' for b in benchmarks)
        print(f"Benchmark: {bench_str}")
        print(f"Total: {wall:.3f}s")
    return 0


def _cmd_backends(args: argparse.Namespace) -> int:
    """List backends with detailed info."""
    if getattr(args, 'json', False):
        backends = {k: dict(v) for k, v in BACKEND_REGISTRY.items()}
        print(json.dumps(backends, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"{'Key':20s} {'Type':18s} {'Qubits':6s} {'Provider':25s}")
        print("-" * 70)
        for key, info in BACKEND_REGISTRY.items():
            print(f"{key:20s} {info['type']:18s} {info['qubits']:<6d} {info['provider']:25s}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="quanta_os", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_compile = sub.add_parser("compile", help="compile a QASM circuit")
    p_compile.add_argument("file", nargs="?", default="-",
                           help="path to OpenQASM file (default: built-in sample)")
    p_compile.add_argument("--backend", default="generic_simulator")
    p_compile.add_argument("--json", action="store_true", help="JSON output")
    p_compile.set_defaults(func=_cmd_compile)

    p_cal = sub.add_parser("calibrate", help="run qubit calibration")
    p_cal.add_argument("--qubit", type=int, default=0)
    p_cal.add_argument("--backend", default="generic_simulator")
    p_cal.add_argument("--temp", type=float, default=15.0, help="temperature in mK")
    p_cal.set_defaults(func=_cmd_calibrate)

    p_list = sub.add_parser("list-backends", help="list known backends")
    p_list.add_argument("--json", action="store_true", help="JSON output")
    p_list.set_defaults(func=_cmd_list)

    p_info = sub.add_parser("info", help="show system information")
    p_info.add_argument("--json", action="store_true", help="JSON output")
    p_info.set_defaults(func=_cmd_info)

    p_serve = sub.add_parser("serve", help="start REST API server")
    p_serve.add_argument("--port", type=int, default=8080, help="listen port")
    p_serve.add_argument("--host", default="127.0.0.1", help="bind address")
    p_serve.set_defaults(func=_cmd_serve)

    p_run = sub.add_parser("run", help="run full test suite")
    p_run.add_argument("--backend", default="generic_simulator")
    p_run.add_argument("file", nargs="?", default="-",
                       help="path to QASM file (default: built-in sample)")
    p_run.add_argument("--json", action="store_true", help="JSON output")
    p_run.set_defaults(func=_cmd_run)

    p_backends = sub.add_parser("backends", help="list backends with details")
    p_backends.add_argument("--json", action="store_true", help="JSON output")
    p_backends.set_defaults(func=_cmd_backends)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
