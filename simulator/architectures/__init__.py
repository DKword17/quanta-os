"""
simulator/architectures/superconducting_noise.py
超导量子芯片专用噪声模型
覆盖: IBM Transmon, Google Xmon, 本源量子, 国盾量子
"""

import numpy as np
from ..noise_channel import NoiseModel


class SuperconductingNoiseModel(NoiseModel):
    """
    超导量子比特噪声模型
    
    核心噪声源:
    - T1 能量弛豫 (准粒子隧穿)
    - T2* 相位弛豫 (1/f 磁通噪声)
    - 读出谐振器非线性 (AC Stark shift)
    - 串扰 CR 脉冲泄漏
    - 两能级系统 (TLS) 涨落
    """
    
    def __init__(self, vendor: str = 'ibm', model: str = 'Heron r1'):
        params = self._vendor_params(vendor, model)
        super().__init__(**params)
        self.vendor = vendor
        self.model = model
        
        # 超导专用噪声参数
        self.tls_density = 0.01          # TLS 缺陷密度
        self.flux_noise_amp = 1e-6       # 磁通噪声幅值 (Φ₀/√Hz)
        self.crosstalk_db = -30.0        # 通道串扰
        self.charge_noise = 1e-4         # 电荷噪声
        self.cr_leakage_rate = 0.001     # CR 脉冲泄漏率
    
    def _vendor_params(self, vendor, model):
        """厂商/型号参数表"""
        params = {
            # IBM
            ('ibm', 'Heron r1'): {
                't1_us': 200, 't2_us': 160,
                'single_gate_error': 2e-4,    # 0.02%
                'two_gate_error': 2e-3,       # 0.2%
                'readout_error': 1.5e-2,      # 1.5%
                'crosstalk_db': -35.0,
            },
            ('ibm', 'Eagle r3'): {
                't1_us': 150, 't2_us': 120,
                'single_gate_error': 3e-4,
                'two_gate_error': 3e-3,
                'readout_error': 2.0e-2,
                'crosstalk_db': -30.0,
            },
            ('ibm', 'Condor'): {
                't1_us': 100, 't2_us': 80,
                'single_gate_error': 5e-4,
                'two_gate_error': 6e-3,
                'readout_error': 3.0e-2,
                'crosstalk_db': -28.0,
            },
            # Google
            ('google', 'Willow'): {
                't1_us': 100, 't2_us': 80,
                'single_gate_error': 4e-4,
                'two_gate_error': 3e-3,
                'readout_error': 2.5e-2,
                'crosstalk_db': -32.0,
            },
            ('google', 'Sycamore'): {
                't1_us': 50, 't2_us': 40,
                'single_gate_error': 1e-3,
                'two_gate_error': 5e-3,
                'readout_error': 4.0e-2,
                'crosstalk_db': -28.0,
            },
            # Rigetti
            ('rigetti', 'Ankaa-3'): {
                't1_us': 50, 't2_us': 40,
                'single_gate_error': 5e-4,
                'two_gate_error': 5e-3,
                'readout_error': 3.0e-2,
                'crosstalk_db': -30.0,
            },
            # 本源量子
            ('origin_quantum', 'Wukong'): {
                't1_us': 80, 't2_us': 60,
                'single_gate_error': 8e-4,
                'two_gate_error': 7e-3,
                'readout_error': 4.0e-2,
                'crosstalk_db': -25.0,
            },
        }
        return params.get((vendor, model), {})
    
    def qubit_noise_spectrum(self, qubit_id: int, freq_hz: float) -> float:
        """
        噪声功率谱密度 S(f)
        典型超导器件: 1/f 磁通噪声 + 白噪声
        S(f) = A/f^α + B
        """
        A = self.flux_noise_amp ** 2
        alpha = 1.0  # 1/f 斜率
        B = 1e-12    # 白噪声本底
        return A / (freq_hz ** alpha + 1e-6) + B
    
    def dynamic_noise_aging(self, hours_elapsed: float):
        """
        模拟老化效应: T1/T2 缓慢退化
        当降解到阈值时，系统应触发自校准
        """
        t1_original = self.t1_us
        t2_original = self.t2_us
        
        # 准粒子隧穿导致的缓慢退化
        degradation = np.exp(-hours_elapsed / 1000)  # ~1000小时衰减
        self.t1_us = t1_original * degradation
        self.t2_us = t2_original * degradation


class TrappedIonNoiseModel(NoiseModel):
    """离子阱噪声模型"""
    
    def __init__(self, vendor='ionq', model='Forte'):
        params = {
            ('ionq', 'Forte'): {
                't1_us': 1e6, 't2_us': 5e5,
                'single_gate_error': 2e-4,
                'two_gate_error': 3e-3,
                'readout_error': 5e-3,
            },
            ('quantinuum', 'H2'): {
                't1_us': 2e6, 't2_us': 1e6,
                'single_gate_error': 1e-4,
                'two_gate_error': 5e-4,
                'readout_error': 3e-3,
            },
        }
        super().__init__(**params.get((vendor, model), {}))
        self.vendor = vendor
        self.model = model
        self.laser_phase_noise = 1e-3    # 激光相位噪声
        self.ion_heating_rate = 1e-5     # 离子加热率


class PhotonicNoiseModel(NoiseModel):
    """光量子噪声模型"""
    
    def __init__(self, vendor='xanadu', model='Aurora'):
        params = {
            ('xanadu', 'Aurora'): {
                't1_us': 1e6,  # 光子: 飞行中无退相干
                't2_us': 1e6,
                'single_gate_error': 1e-3,
                'two_gate_error': 5e-3,
                'readout_error': 0.15,  # 探测效率 <1
            },
        }
        super().__init__(**params.get((vendor, model), {}))
        self.optical_loss_db_km = 0.2   # 光纤损耗
        self.detector_efficiency = 0.7   # 单光子探测效率
        self.phase_stability = 0.95      # 干涉仪相位稳定性


class NeutralAtomNoiseModel(NoiseModel):
    """中性原子噪声模型"""
    
    def __init__(self, vendor='quera', model='Aquila'):
        super().__init__(
            t1_us=5e5, t2_us=3e5,
            single_gate_error=5e-4,
            two_gate_error=1e-2,
            readout_error=1e-2,
        )
        self.optical_tweezer_jitter = 1e-9  # 光镊位置抖动
        self.rydberg_lifetime_us = 100     # Rydberg 态寿命


class NVCenterNoiseModel(NoiseModel):
    """NV 色心噪声模型 (室温)"""
    
    def __init__(self, vendor='quantum_brilliance', model='QB Cluster'):
        super().__init__(
            t1_us=5e4, t2_us=5e3,
            single_gate_error=3e-4,
            two_gate_error=1e-2,
            readout_error=5e-2,
        )
        self.temperature_k = 300
        self.spin_bath_coupling = 1e-6   # 自旋浴耦合


class SiliconSpinNoiseModel(NoiseModel):
    """硅基自旋噪声模型"""
    
    def __init__(self, vendor='intel', model='Tunnel Falls'):
        super().__init__(
            t1_us=3e5, t2_us=2e5,
            single_gate_error=1e-3,
            two_gate_error=1e-2,
            readout_error=5e-2,
        )
        self.valley_splitting_error = 1e-3   # 谷分裂误差
        self.nuclear_spin_noise = 1e-5      # 核自旋噪声


class TopologicalNoiseModel(NoiseModel):
    """拓扑量子比特噪声模型 (理论)"""
    
    def __init__(self):
        super().__init__(
            t1_us=1e9, t2_us=1e9,     # 理论: 小时级
            single_gate_error=1e-6,    # 理论: 极低
            two_gate_error=1e-5,
            readout_error=1e-3,
        )
        self.majorana_splitting = 1e-3  # Majorana 能级分裂
