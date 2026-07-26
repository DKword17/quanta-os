"""
kernel/zmq_protocol.py

Quanta OS — ZMQ+JSON Protocol Layer

Based on: Origin PilotOS V4.0 ZMQ+JSON protocol design
Compatible backends: superconducting, trapped-ion, photonic,
                     neutral-atom, silicon-spin, NV-center, topological

Transport: ZeroMQ (REQ/REP + PUB/SUB)
Serialization: JSON
"""

import json
import struct
import time
from dataclasses import dataclass, field, asdict
from enum import IntEnum
from typing import Optional, Dict, Any, List


# ============================================================
# Message Protocol
# ============================================================

PROTOCOL_VERSION = "1.0.0"


class MsgType(IntEnum):
    HEARTBEAT       = 0x01
    LOGIN           = 0x02
    SUBMIT_TASK     = 0x10
    CANCEL_TASK     = 0x11
    QUERY_TASK      = 0x12
    GET_QUEUE       = 0x13
    GET_CHIP_INFO   = 0x14
    GET_CALIBRATION = 0x15
    EXECUTE_CIRCUIT = 0x20
    MEASURE_ALL     = 0x21
    SELF_CALIBRATE  = 0x30
    PAUSE_SERVICE   = 0x31
    RESUME_SERVICE  = 0x32
    GET_OPTIMAL_QUBITS = 0x33
    SESSION_START   = 0x40
    SESSION_END     = 0x41
    SESSION_UPDATE  = 0x42
    SUBSCRIBE       = 0x80
    UNSUBSCRIBE     = 0x81
    PUSH_EVENT      = 0x90
    ERROR           = 0xFF


class BackendType(IntEnum):
    SUPERCONDUCTING = 0x01
    TRAPPED_ION     = 0x02
    PHOTONIC        = 0x03
    NEUTRAL_ATOM    = 0x04
    SILICON_SPIN    = 0x05
    NV_CENTER       = 0x06
    TOPOLOGICAL     = 0x07


class TaskStatus(IntEnum):
    QUEUED      = 0
    COMPILING   = 1
    EXECUTING   = 2
    COMPLETED   = 3
    FAILED      = 4
    CANCELLED   = 5


class ErrorCode(IntEnum):
    SUCCESS             = 0
    AUTH_FAILED         = 1001
    TASK_NOT_FOUND      = 1002
    QUEUE_FULL          = 1003
    BACKEND_BUSY        = 1004
    BACKEND_ERROR       = 1005
    CALIBRATION_FAILED  = 1006
    INVALID_CIRCUIT     = 1007
    TIMEOUT             = 1008
    INTERNAL_ERROR      = 9999


# ============================================================
# Message Data Structures
# ============================================================


@dataclass
class MessageHeader:
    """Standard ZMQ message envelope."""
    version: str = PROTOCOL_VERSION
    msg_type: int = 0
    seq_id: int = 0
    timestamp: int = 0
    token: str = ""
    backend: int = 0

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)

    @classmethod
    def new(cls, msg_type, backend=0, token=""):
        return cls(
            msg_type=msg_type,
            seq_id=int(time.time() * 1000) % 1000000,
            timestamp=int(time.time()),
            token=token,
            backend=backend,
        )


@dataclass
class LoginRequest:
    """Client login request."""
    username: str
    password: str
    client_version: str = PROTOCOL_VERSION
    capabilities: List[str] = field(default_factory=list)


@dataclass
class LoginResponse:
    """Server login response."""
    success: bool
    token: str = ""
    session_id: str = ""
    allowed_backends: List[int] = field(default_factory=list)
    error: str = ""


@dataclass
class CircuitTask:
    """Circuit compilation/execution task."""
    task_id: str
    qasm: str
    shots: int = 1024
    optimization_level: int = 2
    backend: int = 0
    qubits: List[int] = field(default_factory=list)
    params: Dict[str, float] = field(default_factory=dict)


@dataclass
class TaskResult:
    """Task execution result."""
    task_id: str
    status: int
    counts: Dict[str, int] = field(default_factory=dict)
    fidelity: float = 0.0
    compile_time_ms: float = 0.0
    execution_time_ms: float = 0.0
    error_code: int = 0
    error_message: str = ""
    calibration_snapshot: Dict = field(default_factory=dict)


@dataclass
class ChipInfo:
    """Backend chip information."""
    backend_type: int
    n_qubits: int
    topology: List[List[int]]
    t1_us: List[float]
    t2_us: List[float]
    gate_fidelity: Dict[str, float]
    calibration_time: str
    is_available: bool = True


@dataclass
class SessionContext:
    """Variational session context."""
    session_id: str
    backend: int
    circuit_template: str
    n_parameters: int = 0
    current_params: List[float] = field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 200
    convergence_threshold: float = 1e-6


# ============================================================
# ZMQ Protocol (Pack / Unpack)
# ============================================================


class ZMQProtocol:
    """
    ZeroMQ + JSON message serialization.

    Frame layout:
      [0]: Message header (JSON)
      [1]: Message body (JSON)
      [2]: Optional binary payload
    """

    @staticmethod
    def pack(header: MessageHeader, body: dict, binary: bytes = None) -> list:
        """Pack a ZMQ multipart message."""
        frames = [
            json.dumps(header.to_dict()).encode('utf-8'),
            json.dumps(body).encode('utf-8'),
        ]
        if binary:
            frames.append(binary)
        return frames

    @staticmethod
    def unpack(frames: list) -> tuple:
        """Unpack ZMQ multipart frames into (header, body, binary)."""
        if len(frames) < 2:
            raise ValueError("Message too short: need at least 2 frames")
        header = MessageHeader.from_dict(json.loads(frames[0].decode('utf-8')))
        body = json.loads(frames[1].decode('utf-8'))
        binary = frames[2] if len(frames) > 2 else None
        return header, body, binary

    @staticmethod
    def pack_circuit_task(task: CircuitTask) -> tuple:
        """Pack a circuit task into ZMQ message frames."""
        header = MessageHeader.new(
            msg_type=MsgType.SUBMIT_TASK,
            backend=task.backend,
        )
        body = asdict(task)
        return ZMQProtocol.pack(header, body)

    @staticmethod
    def pack_task_result(result: TaskResult) -> tuple:
        """Pack a task result into ZMQ message frames."""
        header = MessageHeader.new(msg_type=MsgType.PUSH_EVENT)
        body = asdict(result)
        return ZMQProtocol.pack(header, body)


# ============================================================
# Hardware-specific Configuration
# ============================================================


@dataclass
class SuperconductingPulseConfig:
    """Superconducting qubit pulse configuration."""
    qubit_id: int
    pulse_type: str
    amplitude: float
    phase: float
    duration_ns: int
    frequency_mhz: float
    shape: str = "DRAG"


@dataclass
class TrappedIonLaserConfig:
    """Trapped ion laser pulse configuration."""
    ion_id: int
    laser_type: str
    wavelength_nm: float
    power_mw: float
    duration_us: int
    beam_waist_um: float


@dataclass
class PhotonicOpticalConfig:
    """Photonic component configuration."""
    mode_id: int
    component: str
    transmissivity: float = 0.5
    phase_shift: float = 0.0
    squeezing_db: float = 0.0


@dataclass
class NeutralAtomLaserConfig:
    """Neutral atom laser operation."""
    atom_id: int
    operation: str
    detuning_mhz: float
    rabi_frequency_mhz: float
    duration_us: int


# ============================================================
# Event Routing
# ============================================================


class EventSystem:
    """ZMQ PUB/SUB event routing helper."""

    EVENTS = {
        "calibration.complete": "Calibration completed successfully",
        "calibration.failed": "Calibration failed",
        "task.completed": "Task completed",
        "task.failed": "Task failed",
        "chip.status_change": "Chip status changed",
        "chip.error_rate_spike": "Error rate spike detected",
        "system.temperature": "System temperature warning",
        "system.error": "System error",
        "qubit.drift": "Qubit parameter drift detected",
        "scheduler.queue": "Scheduler queue update",
    }

    @staticmethod
    def subscribe_event(topic: str, zmq_socket):
        """Subscribe to a ZMQ PUB topic."""
        zmq_socket.subscribe(topic)

    @staticmethod
    def publish_event(topic: str, data: dict, zmq_socket):
        """Publish to a ZMQ PUB topic."""
        zmq_socket.send_multipart([
            topic.encode('utf-8'),
            json.dumps(data).encode('utf-8'),
        ])