"""
evolution-engine/pulse_optimizer.py
脉冲形状自优化引擎 (GRAPE + 有限差分)
在噪声环境中对脉冲参数做梯度下降，最小化门错误率
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

import numpy as np
from dataclasses import dataclass
from typing import Callable

@dataclass
class OptimizedPulse:
    """优化后的脉冲参数"""
    qubit_id: int
    gate_name: str
    amplitude: float
    duration_ns: float
    sigma_ratio: float
    drag_coefficient: float
    estimated_error: float

class PulseOptimizer:
    """
    脉冲自优化器

    使用 GRAPE (Gradient Ascent Pulse Engineering) 算法
    配合 Simultaneous Perturbation Stochastic Approximation (SPSA)
    在噪声条件下做无梯度优化
    """

    def __init__(self, n_qubits: int, gate_names: list = None):
        self.n_qubits = n_qubits
        self.gate_names = gate_names or ['X', 'Y', 'H', 'SX']
        self.pulses: dict = {}
        self._init_pulses()

    def _init_pulses(self):
        for g in self.gate_names:
            for q in range(self.n_qubits):
                self.pulses[(q, g)] = OptimizedPulse(
                    qubit_id=q,
                    gate_name=g,
                    amplitude=1.0,
                    duration_ns=40.0,
                    sigma_ratio=4.0,
                    drag_coefficient=0.0,
                    estimated_error=0.01,
                )

    def spsa_optimize(self, gate: str, qubit: int, 
                       n_iter: int = 200, cost_fn: Callable = None):
        """
        SPSA 同时扰动随机逼近优化

        优点：每次迭代只需要 2 次目标函数求值，
        O(1) 复杂度，缩放良好
        """
        pulse = self.pulses[(qubit, gate)]
        theta = np.array([pulse.amplitude, pulse.duration_ns, 
                          pulse.sigma_ratio, pulse.drag_coefficient])

        a = 0.1    # 梯度步长
        c = 0.05   # 扰动幅度
        alpha = 0.602
        gamma = 0.101

        for k in range(n_iter):
            ak = a / (k + 1) ** alpha
            ck = c / (k + 1) ** gamma

            # 生成随机扰动向量 Δ ∈ {-1, +1}^4
            delta = np.random.choice([-1, 1], size=4)

            # 两次求值：θ+ 和 θ-
            cost_plus  = self._eval_pulse(theta + ck * delta, qubit)
            cost_minus = self._eval_pulse(theta - ck * delta, qubit)

            # 梯度估计
            g_hat = (cost_plus - cost_minus) / (2 * ck * delta)

            # 参数更新
            theta -= ak * g_hat

            # 钳制到合法范围
            theta = np.clip(theta, [0.1, 10.0, 2.0, -5.0], 
                                    [2.0, 200.0, 10.0, 5.0])

        # 更新存储
        pulse.amplitude = theta[0]
        pulse.duration_ns = theta[1]
        pulse.sigma_ratio = theta[2]
        pulse.drag_coefficient = theta[3]
        pulse.estimated_error = self._eval_pulse(theta, qubit)

        return pulse

    def _eval_pulse(self, theta, qubit_id, n_shots=1024) -> float:
        """
        评估脉冲参数的门错误率
        实际硬件上这里做真实测量；
        模拟版本用噪声模型近似
        """
        amp, dur, sigma, drag = theta

        # 脉冲形状
        dt = 0.5  # ns
        t = np.linspace(-dur/2, dur/2, int(dur/dt))
        gaussian = np.exp(-0.5 * (t / (dur/sigma))**2)

        # 计算泄漏率 (到 |2> 态的布居数)
        rabi_freq = amp * 10.0  # MHz
        rabi_rate = rabi_freq / 1000.0  # GHz
        leakage = (drag * rabi_freq / 200.0) ** 2

        # 退相干贡献
        t1 = 50.0  # μs
        t2 = 30.0
        dephasing = dur / 1000 / t2
        amplitude_damping = dur / 1000 / t1

        # 总错误率
        total_error = 0.01 * (1 - amp)**2 + leakage + dephasing + amplitude_damping

        return total_error

class SelfCalibratingPulseLibrary:
    """
    自校准脉冲库

    每个 qubit 的脉冲参数独立优化，
    并随着硬件老化 (T1/T2 漂移) 自动更新
    """

    def __init__(self, optimizer: PulseOptimizer):
        self.optimizer = optimizer
        self.last_calibration_time = 0
        self.calibration_interval_s = 3600  # 每小时重新校准

    def auto_refresh(self, t1_map: dict, t2_map: dict):
        """
        根据最新 T1/T2 测量数据自动刷新脉冲参数
        """
        for (q, g), pulse in self.optimizer.pulses.items():
            q_t1 = t1_map.get(q, 50.0)
            q_t2 = t2_map.get(q, 30.0)

            # T1/T2 缩短 → 需要更快脉冲
            if q_t1 < 30.0 or q_t2 < 20.0:
                new_duration = pulse.duration_ns * 0.8
                new_amplitude = pulse.amplitude * 1.1

                self.optimizer.pulses[(q, g)] = OptimizedPulse(
                    qubit_id=q,
                    gate_name=g,
                    amplitude=min(new_amplitude, 2.0),
                    duration_ns=max(new_duration, 10.0),
                    sigma_ratio=pulse.sigma_ratio,
                    drag_coefficient=pulse.drag_coefficient,
                    estimated_error=pulse.estimated_error,
                )
