"""
kernel/zmq_protocol.py
Quanta OS — 量子测控系统通信协议层

参考: 本源司南 (Origin PilotOS) V4.0 ZMQ+JSON 协议设计
兼容性: 超导/离子阱/光量子/中性原子 四体系

通信模式: ZeroMQ (REQ/REP + PUB/SUB)
序列化格式: JSON
"""

import json
import struct
import time
from dataclasses import dataclass, field, asdict
from enum import IntEnum
from typing import Optional, Dict, Any, List


# ============================================================
# 协议常量
# ============================================================

PROTOCOL_VERSION = "1.0.0"

# 消息类型
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

# 后端类型
class BackendType(IntEnum):
    SUPERCONDUCTING = 0x01  # 超导
    TRAPPED_ION     = 0x02  # 离子阱
    PHOTONIC        = 0x03  # 光量子
    NEUTRAL_ATOM    = 0x04  # 中性原子
    SILICON_SPIN    = 0x05  # 硅自旋
    NV_CENTER       = 0x06  # NV色心
    TOPOLOGICAL     = 0x07  # 拓扑

# 任务状态
class TaskStatus(IntEnum):
    QUEUED      = 0  # 排队中
    COMPILING   = 1  # 编译中
    EXECUTING   = 2  # 执行中
    COMPLETED   = 3  # 已完成
    FAILED      = 4  # 失败
    CANCELLED   = 5  # 已取消

# 错误码
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
# 消息定义
# ============================================================

@dataclass
class MessageHeader:
    """消息头 — 所有 ZMQ 消息通用"""
    version: str = PROTOCOL_VERSION
    msg_type: int = 0
    seq_id: int = 0          # 序列号（去重/重传）
    timestamp: int = 0       # Unix 时间戳
    token: str = ""          # 认证令牌
    backend: int = 0         # 目标后端类型
    
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
    """登录请求"""
    username: str
    password: str  # 或 token
    client_version: str = PROTOCOL_VERSION
    capabilities: List[str] = field(default_factory=list)


@dataclass
class LoginResponse:
    """登录响应"""
    success: bool
    token: str = ""
    session_id: str = ""
    allowed_backends: List[int] = field(default_factory=list)
    error: str = ""


@dataclass
class CircuitTask:
    """量子电路任务"""
    task_id: str
    qasm: str                    # OpenQASM 3.0
    shots: int = 1024
    optimization_level: int = 2  # 0-3
    backend: int = 0             # 后端类型
    qubits: List[int] = field(default_factory=list)  # 指定 qubit
    params: Dict[str, float] = field(default_factory=dict)  # VQC 参数


@dataclass
class TaskResult:
    """任务执行结果"""
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
    """芯片信息"""
    backend_type: int
    n_qubits: int
    topology: List[List[int]]     # [[q0, q1], ...]
    t1_us: List[float]            # 每 qubit T1
    t2_us: List[float]            # 每 qubit T2
    gate_fidelity: Dict[str, float]  # {"cx": 0.997, "h": 0.999, ...}
    calibration_time: str         # 上次校准时间
    is_available: bool = True


@dataclass
class SessionContext:
    """Session 机制 — 支持变分线路动态优化"""
    session_id: str
    backend: int
    circuit_template: str           # QASM 模板
    n_parameters: int = 0
    current_params: List[float] = field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 200
    convergence_threshold: float = 1e-6


# ============================================================
# ZMQ 消息打包/解包
# ============================================================

class ZMQProtocol:
    """
    ZeroMQ + JSON 通信处理器
    
    消息格式:
      [帧1: 消息头 (JSON)]
      [帧2: 消息体 (JSON)]
      [帧3: 可选二进制数据 (FPGA 脉冲/测量结果)]
    """
    
    @staticmethod
    def pack(header: MessageHeader, body: dict, binary: bytes = None) -> list:
        """打包为 ZMQ 多帧消息"""
        frames = [
            json.dumps(header.to_dict()).encode('utf-8'),
            json.dumps(body).encode('utf-8'),
        ]
        if binary:
            frames.append(binary)
        return frames
    
    @staticmethod
    def unpack(frames: list) -> tuple:
        """解包 ZMQ 多帧消息"""
        if len(frames) < 2:
            raise ValueError("Message too short: need at least 2 frames")
        
        header = MessageHeader.from_dict(
            json.loads(frames[0].decode('utf-8'))
        )
        body = json.loads(frames[1].decode('utf-8'))
        binary = frames[2] if len(frames) > 2 else None
        
        return header, body, binary
    
    @staticmethod
    def pack_circuit_task(task: CircuitTask) -> tuple:
        """打包电路任务为 ZMQ 消息"""
        header = MessageHeader.new(
            msg_type=MsgType.SUBMIT_TASK,
            backend=task.backend,
        )
        body = asdict(task)
        return ZMQProtocol.pack(header, body)
    
    @staticmethod
    def pack_task_result(result: TaskResult) -> tuple:
        """打包任务结果"""
        header = MessageHeader.new(msg_type=MsgType.PUSH_EVENT)
        body = asdict(result)
        return ZMQProtocol.pack(header, body)


# ============================================================
# 消息定义 — 各架构专用
# ============================================================

# --- 超导专用消息 ---
@dataclass
class SuperconductingPulseConfig:
    """超导脉冲配置"""
    qubit_id: int
    pulse_type: str      # "X180", "X90", "CR", "Readout"
    amplitude: float     # 归一化 0.0-1.0
    phase: float         # 弧度
    duration_ns: int     # 脉冲持续时间
    frequency_mhz: float # 微波频率
    shape: str = "DRAG"  # 脉冲形状: DRAG/Gaussian/Hermite


# --- 离子阱专用消息 ---
@dataclass
class TrappedIonLaserConfig:
    """离子阱激光配置"""
    ion_id: int
    laser_type: str      # "Carrier", "RedSideband", "BlueSideband"
    wavelength_nm: float # 激光波长 (369nm for Yb+)
    power_mw: float      # 激光功率
    duration_us: int     # 脉冲时间
    beam_waist_um: float # 光束半径


# --- 光量子专用消息 ---
@dataclass
class PhotonicOpticalConfig:
    """光量子光学配置"""
    mode_id: int
    component: str       # "BS" 分束器, "PS" 相移器, "Squeezer"
    transmissivity: float = 0.5  # 分束器透过率
    phase_shift: float = 0.0     # 相移量
    squeezing_db: float = 0.0    # 压缩度 (dB)


# --- 中性原子专用消息 ---
@dataclass
class NeutralAtomLaserConfig:
    """中性原子激光配置"""
    atom_id: int
    operation: str       # "Rydberg", "Cooling", "Imaging"
    detuning_mhz: float  # 激光失谐
    rabi_frequency_mhz: float  # Rabi 频率
    duration_us: int     # 激光作用时间


# ============================================================
# 消息订阅/推送 (事件系统)
# ============================================================

class EventSystem:
    """基于 ZMQ PUB/SUB 的事件推送系统"""
    
    # 事件类型
    EVENTS = {
        "calibration.complete": "校准完成",
        "calibration.failed": "校准失败",
        "task.completed": "任务完成",
        "task.failed": "任务失败",
        "chip.status_change": "芯片状态变更",
        "chip.error_rate_spike": "错误率激增",
        "system.temperature": "系统温度变更",
        "system.error": "系统错误",
        "qubit.drift": "Qubit 参数漂移",
        "scheduler.queue": "队列变更",
    }
    
    @staticmethod
    def subscribe_event(topic: str, zmq_socket):
        """订阅事件"""
        zmq_socket.subscribe(topic)
    
    @staticmethod
    def publish_event(topic: str, data: dict, zmq_socket):
        """发布事件"""
        zmq_socket.send_multipart([
            topic.encode('utf-8'),
            json.dumps(data).encode('utf-8'),
        ])
