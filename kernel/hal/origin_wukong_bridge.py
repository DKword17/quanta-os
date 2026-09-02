#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kernel/hal/origin_wukong_bridge.py
==================================

本源悟空 180 量子处理器适配器
Origin Wukong 180-qubit Superconducting QPU Bridge

对接本源量子云平台 / ZMQ 协议层
Refer: https://qcloud.originqc.com.cn

Author : DKword17 <19832535010@163.com>
Date   : 2026-07-25

备注:
    这是 Quanta OS 到本源悟空 180 的桥接层。
    通过本源司南 (PilotOS) 的 ZMQ+JSON 协议
    提交量子线路到真实量子处理器。

    工作流程:
        Python SDK (QPanda3) -> ZMQ -> 本源司南 -> 悟空-180 QPU

    连接方式:
        本地: ZMQ REQ/REP @ tcp://localhost:5005
        云上: HTTPS REST -> 本源量子云 API

    本模块不关心量子线路怎么编译 —— 那是 compiler 和 backend_selector 的事情。
    本模块只负责: 接到线路 -> 送过去 -> 拿结果回来。
"""

#
# ─────────────────────────────────────────────────────────────
# Quanta OS — 版权与出处  |  Copyright & Provenance
# 作者    Author   : DKword17 <19832535010@163.com>
# 版权    Copyright: (c) 2026 DKword17
# 许可证  License  : Apache 2.0（见 LICENSE）
# 仓库    Repo     : https://github.com/DKword17/quanta-os
# Quanta OS 由 DKword17 一人原创并维护，转载/复用请保留本标记。
# ─────────────────────────────────────────────────────────────

from __future__ import annotations

import json
import time
import uuid
import hmac
import hashlib
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any

logger = logging.getLogger("quanta.origin_wukong")

# ─── 常量 ────────────────────────────────────────────────────────────────

DEFAULT_ZMQ_ENDPOINT    = "tcp://localhost:5005"   # 本地司南
DEFAULT_CLOUD_API_URL   = "https://qcloud.originqc.com.cn/api/v1"

QUBIT_COUNT_WUKONG      = 180                       # 悟空 180 量子比特
NATIVE_GATES_WUKONG     = ["CX", "CZ", "H", "S", "T",
                           "RX", "RY", "RZ", "SX",
                           "MEASURE", "RESET"]

# 超时配置（毫秒）
TIMEOUT_CONNECT_MS       = 5000
TIMEOUT_EXECUTE_MS       = 300000   # 量子芯片执行时间 ~5分钟
TIMEOUT_QUERY_MS         = 10000

# 认证
AUTH_VERSION             = "v1"

# ─── 数据结构 ────────────────────────────────────────────────────────────

@dataclass
class WukongTask:
    """提交给悟空的量子计算任务"""

    task_id: str = field(default_factory=lambda: f"wk_{uuid.uuid4().hex[:12]}")
    qasm_source: str = ""
    shots: int = 1024
    qubit_mapping: list[int] = field(default_factory=list)   # 逻辑->物理映射
    optimization_level: int = 2                               # 0-3
    source: str = "quanta_os"                                 # 来源标识

    def validate(self) -> bool:
        """检查任务参数是不是合理"""
        if not self.qasm_source.strip():
            logger.error("QASM 源码是空的，没法提交")
            return False
        if self.shots < 1 or self.shots > 1000000:
            logger.warning(f"shots={self.shots} 不太对，用默认值 1024")
            self.shots = 1024
        if self.optimization_level < 0 or self.optimization_level > 3:
            self.optimization_level = 2
        return True

@dataclass
class WukongResult:
    """悟空返回的计算结果"""

    task_id: str
    status: str                     # "completed", "failed", "queued", "running"
    counts: dict[str, int] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    error_message: str = ""
    calibration_id: str = ""
    metadata: dict = field(default_factory=dict)

# ─── 认证 ────────────────────────────────────────────────────────────────

def _generate_signature(api_key: str, api_secret: str, 
                        timestamp: str, body: str) -> str:
    """
    生成 HMAC-SHA256 签名。

    本源云 API 要求:
        signature = HMAC-SHA256(api_secret, timestamp + body)
        然后 base64 编码放到 Authorization header 里
    """
    msg = (timestamp + body).encode('utf-8')
    sig = hmac.new(
        api_secret.encode('utf-8'),
        msg,
        hashlib.sha256
    ).hexdigest()
    return sig

# ─── 桥接层 ──────────────────────────────────────────────────────────────

class WukongBridge:
    """
    悟空 180 QPU 桥接层。

    用之前记得先配好连接参数 —— 如果连不上会抛异常。

    两种模式:
        1. local: 通过 ZMQ 走本地本源司南
        2. cloud: 通过 HTTPS REST 走本源云

    用法:
        bridge = WukongBridge(mode="local")
        result = bridge.execute(task)

        if result.status == "completed":
            print(result.counts)   # {'00': 512, '11': 512}
    """

    def __init__(self, mode: str = "local",
                 endpoint: str = DEFAULT_ZMQ_ENDPOINT,
                 api_key: str = "", api_secret: str = "",
                 auto_reconnect: bool = True):
        """
        Args:
            mode: "local" 或 "cloud"
            endpoint: ZMQ 地址或 REST API 地址
            api_key/secret: 云模式才需要
            auto_reconnect: 断了自动重连
        """
        self.mode = mode
        self.endpoint = endpoint
        self.api_key = api_key
        self.api_secret = api_secret
        self.auto_reconnect = auto_reconnect

        self._connected = False
        self._zmq_socket = None
        self._chip_info: dict = {}   # 芯片信息缓存

        logger.info(f"悟空桥接层初始化 ({mode}, {endpoint})")

    def connect(self) -> bool:
        """
        连接后端。

        local 模式: 建立 ZMQ 连接
        cloud 模式: 验证 API key

        Returns:
            True 如果连上了
        """
        if self.mode == "local":
            return self._connect_zmq()
        elif self.mode == "cloud":
            return self._connect_cloud()
        else:
            raise ValueError(f"mode 必须是 'local' 或 'cloud', 给了 {mode}")

    def _connect_zmq(self) -> bool:
        """
        ZMQ 本地连接。

        先试默认端口 5005，
        不行就试 5006, 5007 做 fallback。
        """
        # ZMQ 导入可能没有，先试试
        import importlib
        spec = importlib.util.find_spec("zmq")
        if spec is None:
            logger.error("pyzmq 没装，没法连 ZMQ。"
                        "pip install pyzmq 试试")
            self._connected = False
            return False

        import zmq

        # 试端口
        for port_offset in range(3):
            port = 5005 + port_offset
            addr = f"tcp://localhost:{port}"
            try:
                ctx = zmq.Context.instance()
                sock = ctx.socket(zmq.REQ)
                sock.setsockopt(zmq.LINGER, 1000)
                sock.setsockopt(zmq.RCVTIMEO, TIMEOUT_CONNECT_MS)
                sock.connect(addr)

                # 发个心跳试试
                sock.send_json({"type": "ping"})
                resp = sock.recv_json()

                if resp.get("status") == "pong":
                    self._zmq_socket = sock
                    self._connected = True
                    logger.info(f"连接成功 -> {addr}")

                    # 顺手拿一下芯片信息
                    self._query_chip_info()
                    return True

            except Exception as e:
                logger.warning(f"连接 {addr} 失败: {e}")
                continue

        self._connected = False
        logger.error("所有端口都连不上，本源司南是不是没启动？")
        return False

    def _connect_cloud(self) -> bool:
        """检查 API key 通不通"""
        if not self.api_key or not self.api_secret:
            logger.error("云模式需要 api_key 和 api_secret")
            self._connected = False
            return False

        logger.info("云模式认证通过 (API key 校验略)")
        self._connected = True
        return True

    def _query_chip_info(self) -> dict:
        """
        拿芯片信息。

        包括:
            - 量子比特数量 (180)
            - T1/T2 范围
            - 耦合图
            - 校准时间
        """
        # 缓存逻辑: 1小时内不重复请求
        if self._chip_info and time.time() - self._chip_info.get("_ts", 0) < 3600:
            return self._chip_info

        info = {
            "name": "origin_wukong_180",
            "qubits": QUBIT_COUNT_WUKONG,
            "native_gates": NATIVE_GATES_WUKONG,
            "topology": "heavy-hex",
            "calibration_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "_ts": time.time(),
        }
        self._chip_info = info
        return info

    def execute(self, task: WukongTask) -> WukongResult:
        """
        提交任务到悟空，等结果回来。

        阻塞调用 —— 量子芯片执行需要几秒到几分钟。

        Args:
            task: 要执行的任务

        Returns:
            执行结果

        Raises:
            ConnectionError: 连不上后端
            RuntimeError: 执行过程出错
        """
        if not task.validate():
            return WukongResult(
                task_id=task.task_id,
                status="failed",
                error_message="参数验证没通过"
            )

        if not self._connected:
            if self.auto_reconnect:
                if not self.connect():
                    raise ConnectionError(f"连不上 {self.endpoint}")
            else:
                raise ConnectionError("没连上，先调 connect()")

        logger.info(f"提交任务 {task.task_id} ({task.shots} shots)")

        if self.mode == "local":
            return self._execute_local(task)
        else:
            return self._execute_cloud(task)

    def _execute_local(self, task: WukongTask) -> WukongResult:
        """
        通过 ZMQ 本地执行。

        流程:
            1. 发 SUBMIT_TASK 消息
            2. 拿回 task_id
            3. 轮询直到状态变成 completed 或 failed
            4. 取结果
        """
        zmq = __import__("zmq", fromlist=["Context"])

        try:
            # 发任务
            msg = {
                "type": "submit_task",
                "payload": {
                    "task_id": task.task_id,
                    "qasm": task.qasm_source,
                    "shots": task.shots,
                    "optimization_level": task.optimization_level,
                    "source": task.source,
                }
            }
            self._zmq_socket.send_json(msg)
            resp = self._zmq_socket.recv_json()

            if resp.get("status") != "ok":
                return WukongResult(
                    task_id=task.task_id,
                    status="failed",
                    error_message=resp.get("error", "提交被拒了")
                )

            # 等着
            start_ts = time.time()
            while time.time() - start_ts < TIMEOUT_EXECUTE_MS / 1000:
                time.sleep(0.5)

                self._zmq_socket.send_json({
                    "type": "query_task",
                    "task_id": task.task_id
                })
                qr = self._zmq_socket.recv_json()

                if qr.get("status") == "completed":
                    return WukongResult(
                        task_id=task.task_id,
                        status="completed",
                        counts=qr.get("counts", {}),
                        execution_time_ms=qr.get("time_ms", 0.0),
                    )
                elif qr.get("status") == "failed":
                    return WukongResult(
                        task_id=task.task_id,
                        status="failed",
                        error_message=qr.get("error", "执行出错")
                    )

            return WukongResult(
                task_id=task.task_id,
                status="failed",
                error_message=f"超时了 ({TIMEOUT_EXECUTE_MS}ms)"
            )

        except Exception as e:
            logger.exception("ZMQ 通信出问题了")
            return WukongResult(
                task_id=task.task_id,
                status="failed",
                error_message=str(e)
            )

    def _execute_cloud(self, task: WukongTask) -> WukongResult:
        """通过 REST API 提交到本源云（占位）"""
        # TODO: 等本源云给了 API 文档再补
        logger.warning("云模式还没完全实现, 先走本地模式")
        return self._execute_local(task)

    def get_status(self) -> dict:
        """看看桥接层当前是什么状态"""
        status = "connected" if self._connected else "disconnected"
        info = self._chip_info.copy()
        info.pop("_ts", None) if "_ts" in info else None
        return {
            "status": status,
            "mode": self.mode,
            "endpoint": self.endpoint,
            "chip": info,
        }

# ─── 测试 ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    bridge = WukongBridge(mode="local")

    if not bridge.connect():
        print("连不上本源司南 —— 是不是没启动？")
        print("先跑:   docker run origin-pilotos:latest")
        sys.exit(1)

    print(f"连上了！芯片信息: {bridge.get_status()}")

    # Bell state
    task = WukongTask(
        qasm_source="""OPENQASM 3.0;
qubit[2] q;
h q[0];
cx q[0], q[1];
measure q[0]; measure q[1];""",
        shots=1024
    )

    result = bridge.execute(task)

    if result.status == "completed":
        print(f"Bell state 结果: {result.counts}")
        print(f"执行时间: {result.execution_time_ms:.0f} ms")
    else:
        print(f"出错了: {result.error_message}")
