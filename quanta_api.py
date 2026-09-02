"""
quanta_api.py - Quanta OS REST API 服务器

基于 Python 内置 http.server，零额外依赖。
提供编译/校准/调度/自演化等核心功能的 HTTP 接口。

用法:
    python -m quanta_api --port 8080 --host 0.0.0.0
    quanta-os serve --port 8080
"""

import argparse
import json
import logging
import os
import sys
import time
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse
from typing import Any, Dict, Optional

import numpy as np

from quanta_os import QOS, BACKEND_REGISTRY, BackendUnavailableError, CompilationError

# ===================================================================
#  Configuration
# ===================================================================
VERSION = "0.4.0"
logger = logging.getLogger("quanta.api")
_qos = QOS()

# ===================================================================
#  Custom JSON encoder (handles numpy types)
# ===================================================================
class QuantaJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        return super().default(o)


def json_dumps(obj):
    return json.dumps(obj, cls=QuantaJSONEncoder, ensure_ascii=False, default=str)


# ===================================================================
#  HTTP Request Handler
# ===================================================================
class QuantaAPIHandler(BaseHTTPRequestHandler):
    """REST API 请求处理器"""

    def log_message(self, fmt, *args):
        logger.info(f"{self.client_address[0]} - {fmt % args}")

    def _send_json(self, data: Any, status: int = 200):
        """发送 JSON 响应"""
        body = json_dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, status: int, error_type: str, message: str):
        self._send_json({"error": error_type, "message": message}, status)

    def _read_body(self) -> Optional[Dict[str, Any]]:
        """读取并解析 JSON 请求体"""
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return None
        try:
            raw = self.rfile.read(length)
            return json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self._send_error(400, "BadRequest", f"Invalid JSON: {e}")
            return None

    def do_OPTIONS(self):
        """CORS preflight"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/health":
            self._handle_health()
        elif path == "/api/backends":
            self._handle_list_backends()
        elif path.startswith("/api/backends/"):
            name = path[len("/api/backends/"):]
            self._handle_backend_info(name)
        else:
            self._send_error(404, "NotFound", f"Unknown endpoint: {path}")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/compile":
            self._handle_compile()
        elif path == "/api/calibrate":
            self._handle_calibrate()
        elif path == "/api/schedule":
            self._handle_schedule()
        elif path == "/api/evolve":
            self._handle_evolve()
        else:
            self._send_error(404, "NotFound", f"Unknown endpoint: {path}")

    # ========== Handlers ==========

    def _handle_health(self):
        """GET /api/health"""
        from _provenance import _INTEGRITY_OK
        self._send_json({
            "status": "ok",
            "version": VERSION,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "integrity": bool(_INTEGRITY_OK),
            "backends": len(BACKEND_REGISTRY),
        })

    def _handle_list_backends(self):
        """GET /api/backends"""
        backends = []
        for key, info in BACKEND_REGISTRY.items():
            entry = {"key": key, **info}
            backends.append(entry)
        self._send_json({"backends": backends})

    def _handle_backend_info(self, name: str):
        """GET /api/backends/{name}"""
        if name not in BACKEND_REGISTRY:
            known = ", ".join(BACKEND_REGISTRY.keys())
            self._send_error(404, "BackendNotFound",
                             f"Unknown backend '{name}'. Known: {known}")
            return
        self._send_json({"backend": name, **BACKEND_REGISTRY[name]})

    def _handle_compile(self):
        """POST /api/compile"""
        body = self._read_body()
        if body is None:
            return
        qasm = body.get("qasm", "").strip()
        if not qasm:
            self._send_error(400, "BadRequest", "Missing required field: 'qasm'")
            return
        backend = body.get("backend", "generic_simulator")
        try:
            result = _qos.compile(qasm, backend=backend)
            self._send_json({
                "source": result.source[:200],
                "compiled": result.compiled[:200] if hasattr(result, 'compiled') else "",
                "backend_name": result.backend_name,
                "original_ops": result.original_ops,
                "final_ops": result.final_ops,
                "original_depth": result.original_depth,
                "final_depth": result.final_depth,
                "compile_time_ms": result.compile_time_ms,
            })
        except (BackendUnavailableError, CompilationError) as e:
            self._send_error(422, type(e).__name__, str(e))
        except Exception as e:
            logger.exception("Compile error")
            self._send_error(500, "InternalError", str(e))

    def _handle_calibrate(self):
        """POST /api/calibrate"""
        body = self._read_body()
        if body is None:
            body = {}
        qubit_id = body.get("qubit_id", 0)
        backend = body.get("backend", "generic_simulator")
        temperature_mk = body.get("temperature_mk", 15.0)
        try:
            result = _qos.calibrate(qubit_id=qubit_id, backend=backend,
                                    temperature_mk=temperature_mk)
            self._send_json(result)
        except Exception as e:
            logger.exception("Calibrate error")
            self._send_error(500, "InternalError", str(e))

    def _handle_schedule(self):
        """POST /api/schedule"""
        body = self._read_body()
        if body is None:
            return
        qasm = body.get("qasm", "").strip()
        backend = body.get("backend", "generic_simulator")
        shots = body.get("shots", 1024)
        priority = body.get("priority", "BATCH")
        job_id = body.get("job_id", f"api_{int(time.time())}")

        try:
            from kernel.resource_scheduler import (ResourceScheduler, SchedulerConfig,
                                                   QuantumJob, JobPriority)
            sched = ResourceScheduler(SchedulerConfig(max_concurrent_jobs=16))
            sched.register_backend("primary", 10, [(i, i + 1) for i in range(9)],
                                   ["CX", "H", "RX", "RZ"])
            prio_map = {
                "BACKGROUND": JobPriority.BACKGROUND,
                "BATCH": JobPriority.BATCH,
                "INTERACTIVE": JobPriority.INTERACTIVE,
                "REAL_TIME": JobPriority.REAL_TIME,
            }
            job = QuantumJob(
                job_id=job_id,
                qasm_source=qasm or "OPENQASM 3.0; qubit[2] q; h q[0];",
                n_qubits=8,
                shots=shots,
                priority=prio_map.get(priority, JobPriority.BATCH),
            )
            sched.submit_job(job)
            scheduled = sched.schedule()
            self._send_json({
                "job_id": job_id,
                "status": "scheduled",
                "position": len(scheduled),
                "queue_depth": sched.get_queue_depth(),
            })
        except Exception as e:
            logger.exception("Schedule error")
            self._send_error(500, "InternalError", str(e))

    def _handle_evolve(self):
        """POST /api/evolve"""
        body = self._read_body()
        if body is None:
            body = {}
        n_iterations = body.get("n_iterations", 50)
        n_qubits = body.get("n_qubits", 16)

        try:
            from evolution_engine.self_evolve import SelfEvolutionEngine
            import numpy as np
            np.random.seed(body.get("seed", 42))
            engine = SelfEvolutionEngine(n_qubits=n_qubits, seed=body.get("seed", 42))
            state = engine.run_evolution_cycle(n_iterations=n_iterations)
            report = engine.get_system_report()
            self._send_json(report)
        except Exception as e:
            logger.exception("Evolve error")
            self._send_error(500, "InternalError", str(e))


# ===================================================================
#  Threaded HTTP Server
# ===================================================================
class ThreadedQuantaServer(ThreadingMixIn, HTTPServer):
    """多线程 HTTP 服务器"""
    allow_reuse_address = True
    daemon_threads = True


def create_server(host: str = "127.0.0.1", port: int = 8080) -> HTTPServer:
    """创建并返回 API 服务器实例"""
    return ThreadedQuantaServer((host, port), QuantaAPIHandler)


def main(argv: Optional[list] = None) -> int:
    """CLI 入口：启动 API 服务器"""
    parser = argparse.ArgumentParser(prog="quanta-os serve",
                                     description="Quanta OS REST API Server")
    parser.add_argument("--port", type=int, default=8080, help="Listen port")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    server = create_server(args.host, args.port)
    print(f"Quanta OS API server v{VERSION} starting...")
    print(f"Listening on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())