"""
simulator/noise_channel.py
量子噪声模拟器
用于离线环境下验证 Quanta OS 的自演化能力
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class NoiseModel:
    """
    噪声模型参数
    参考真实超导量子处理器噪声特征
    """
    # 退相干
    t1_us: float = 50.0       # 能量弛豫
    t2_us: float = 30.0       # 相位弛豫
    
    # 门错误
    single_gate_error: float = 1e-3    # 单量子门错误率
    two_gate_error: float = 1e-2       # 两量子门错误率
    readout_error: float = 5e-2        # 读出错误率
    
    # 串扰
    crosstalk_db: float = -30.0        # qubit 间串扰衰减
    residual_coupling: float = 1e-3    # ZZ 残余耦合
    
    # 1/f 噪声
    flux_noise_amp: float = 1e-6       # 磁通噪声幅值
    charge_noise_amp: float = 1e-4     # 电荷噪声幅值


class NoisyQuantumChannel:
    """
    含噪声量子信道
    
    模拟 qubit 在真实物理硬件上的演化过程，
    包含退相干、门错误、串扰等主要噪声源
    """
    
    def __init__(self, n_qubits: int, model: Optional[NoiseModel] = None):
        self.n_qubits = n_qubits
        self.model = model or NoiseModel()
        self._rng = np.random.default_rng()
        
        # 量子态 |ψ⟩
        self._state = np.zeros(2 ** n_qubits, dtype=complex)
        self._state[0] = 1.0
    
    def apply_gate(self, qubit: int, gate_matrix: np.ndarray):
        """
        应用量子门，加入噪声
        gate_matrix: 2×2 酉矩阵
        """
        # 构建全算子
        full = self._build_operator(gate_matrix, qubit)
        
        # 加入门错误
        error_chance = self._rng.random()
        if error_chance < self.model.single_gate_error:
            # 随机泡利错误
            pauli = self._rng.choice([
                np.array([[1,0],[0,-1]]),   # Z
                np.array([[0,1],[1,0]]),    # X
                np.array([[0,-1j],[1j,0]]), # Y
            ])
            full = pauli @ full
        
        # 应用
        self._state = full @ self._state
    
    def apply_cx(self, control: int, target: int):
        """应用 CNOT 门"""
        # CNOT 矩阵 (4×4) 投射到控制-target 空间
        cx_mat = np.array([
            [1,0,0,0],
            [0,1,0,0],
            [0,0,0,1],
            [0,0,1,0]
        ], dtype=complex)
        
        # 构建全算子
        full = self._build_two_qubit_op(cx_mat, control, target)
        
        # 加入两量子门错误
        if self._rng.random() < self.model.two_gate_error:
            self._state = self._decohere()
        
        self._state = full @ self._state
    
    def measure(self, qubit: int, n_shots: int = 1) -> int:
        """测量量子比特"""
        n = 2 ** self.n_qubits
        probs = np.abs(self._state) ** 2
        
        # 投影到目标 qubit 的基矢
        result = 0
        for _ in range(n_shots):
            # 随机坍缩
            sample = self._rng.choice(n, p=probs)
            bit = (sample >> (self.n_qubits - 1 - qubit)) & 1
            
            # 加入读出错误
            if self._rng.random() < self.model.readout_error:
                bit ^= 1
            
            result += bit
        
        return result
    
    def apply_decoherence(self, elapsed_ns: float):
        """应用退相干（在空闲周期）"""
        t1 = self.model.t1_us * 1000  # 转为 ns
        t2 = self.model.t2_us * 1000
        
        # 振幅阻尼 (T1)
        p_reset = 1 - np.exp(-elapsed_ns / t1)
        
        # 相位阻尼 (T2)
        p_dephase = 1 - np.exp(-elapsed_ns / t2)
        
        n = 2 ** self.n_qubits
        for i in range(n):
            # 简化：应用经典衰减
            self._state[i] *= np.sqrt(1 - p_reset)
            
            # 随机相位抖动
            if self._rng.random() < p_dephase:
                self._state[i] *= self._rng.choice([1, -1, 1j, -1j])
        
        # 归一化
        self._state /= np.linalg.norm(self._state)
    
    def get_state(self) -> np.ndarray:
        return self._state.copy()
    
    def _build_operator(self, gate: np.ndarray, qubit: int) -> np.ndarray:
        """构建全空间算子"""
        if qubit == 0:
            op = gate
            for _ in range(1, self.n_qubits):
                op = np.kron(op, np.eye(2, dtype=complex))
        else:
            op = np.eye(2, dtype=complex)
            op = np.kron(op, gate)
            for _ in range(2, self.n_qubits):
                op = np.kron(op, np.eye(2, dtype=complex))
        return op
    
    def _build_two_qubit_op(self, op_2q: np.ndarray, q1: int, q2: int) -> np.ndarray:
        """构建两量子门在全空间的算子"""
        # 简化实现：假设 q1=0, q2=1
        if q1 == 0 and q2 == 1:
            full = op_2q
            for _ in range(2, self.n_qubits):
                full = np.kron(full, np.eye(2, dtype=complex))
            return full
        else:
            # 一般情况需量子线路重映射
            raise NotImplementedError("通用两量子门构建器待实现")
    
    def _decohere(self) -> np.ndarray:
        """应用退相干到量子态"""
        probs = np.abs(self._state) ** 2
        phases = np.exp(2j * np.pi * self._rng.random(len(self._state)))
        return np.sqrt(probs) * phases


class TopologyGenerator:
    """
    随机拓扑生成器
    
    模拟不同量子处理器的连接拓扑，
    用于测试 Quanta OS 的自适应映射能力
    """
    
    @staticmethod
    def grid(rows: int, cols: int) -> list:
        """网格拓扑（如 Google Sycamore）"""
        edges = []
        for r in range(rows):
            for c in range(cols):
                idx = r * cols + c
                if c + 1 < cols:
                    edges.append((idx, idx + 1))
                if r + 1 < rows:
                    edges.append((idx, idx + cols))
        return edges
    
    @staticmethod
    def heavy_hex(layers: int = 3) -> list:
        """重六边形拓扑（如 IBM Quantum）"""
        edges = []
        n_qubits = layers * 6
        for i in range(n_qubits):
            edges.append((i, (i + 1) % n_qubits))
            edges.append((i, (i + 3) % n_qubits))
        return [(a, b) for a, b in edges if a < b]
    
    @staticmethod
    def random(n_qubits: int, connectivity: float = 0.3) -> list:
        """随机拓扑"""
        edges = []
        for i in range(n_qubits):
            for j in range(i + 1, n_qubits):
                if np.random.random() < connectivity:
                    edges.append((i, j))
        return edges
