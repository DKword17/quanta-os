"""
evolution-engine/backends/trapped_ion_backend.py
离子阱量子计算机 — 专用后端
覆盖: IonQ, Quantinuum (Honeywell), 启科量子
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

from ..vqc_compiler import VariationalQuantumCompiler, Topology, QubitParams, EdgeParams

class TrappedIonBackend:
    """
    离子阱量子后端

    特征:
    - 全连通拓扑 (all-to-all)
    - Molmer-Sorensen 门做原生纠缠
    - 激光或微波驱动
    - T2 长达秒级
    - 门时间 ~100-300μs (快于超导1000x慢)
    """

    VENDORS = {
        'ionq': [
            {'name': 'Aria',  'qubits': 25, 'laser': True,  'gate_us': 200},
            {'name': 'Forte', 'qubits': 36, 'laser': True,  'gate_us': 180},
            {'name': 'Tempo', 'qubits': 64, 'laser': True,  'gate_us': 150},
        ],
        'quantinuum': [
            {'name': 'H1',   'qubits': 20, 'laser': False, 'gate_us': 300},
            {'name': 'H2',   'qubits': 56, 'laser': False, 'gate_us': 100},
        ],
        '启科量子': [
            {'name': 'AbaQ', 'qubits': 16, 'laser': True, 'gate_us': 250},
        ],
    }

    def __init__(self, vendor='ionq', model='Forte'):
        self.vendor = vendor
        self.model = model
        self.n_ions = 0
        self.gate_time_us = 200
        self.laser_based = True
        self.topology = None
        self.compiler = None
        self._resolve_model()
        self._build_topology()
        self.compiler = VariationalQuantumCompiler(self.topology)

    def _resolve_model(self):
        for entry in self.VENDORS.get(self.vendor, []):
            if entry['name'].lower() == self.model.lower():
                self.n_ions = entry['qubits']
                self.gate_time_us = entry['gate_us']
                self.laser_based = entry['laser']
                return
        self.n_ions = 36
        self.gate_time_us = 180
        self.model = 'Forte'

    def _build_topology(self):
        qubits = [QubitParams(id=i, t1_us=1e6, t2_us=5e5, 
                               readout_fidelity=0.995) for i in range(self.n_ions)]
        # 离子阱 = 全连通
        edges = []
        for i in range(self.n_ions):
            for j in range(i + 1, self.n_ions):
                edges.append(EdgeParams(i, j, cx_fidelity=0.997))
        self.topology = Topology(qubits=qubits, edges=edges)

    def ms_gate_decomposition(self, qubits, angle):
        """
        Molmer-Sorensen 多体纠缠门
        MS(θ) = exp(-i * θ/2 * S_x²)
        原生多体门，不分解为两量子门
        这是离子阱相比超导的独特优势
        """
        return {
            'type': 'ms_gate',
            'qubits': qubits,
            'angle': angle,
            'native': True,
            'gate_time_us': self.gate_time_us * 2,
        }

    @property
    def spec(self):
        return {
            'vendor': self.vendor,
            'model': self.model,
            'qubits': self.n_ions,
            'topology': 'all-to-all',
            'gate_time_us': self.gate_time_us,
            't2_us': 5e5,
            'requires_vacuum': True,
            'requires_laser': self.laser_based,
        }

class PhotonicBackend:
    """光量子后端 (Xanadu, PsiQuantum, 图灵量子, 玻色量子)"""

    VENDORS = {
        'xanadu': [
            {'name': 'X8',      'modes': 8,   'type': 'squeezed'},
            {'name': 'Borealis','modes': 216, 'type': 'squeezed'},
            {'name': 'Aurora',  'modes': 1000,'type': 'squeezed'},
        ],
        'psiquantum': [
            {'name': 'Fusion v1', 'modes': 1000, 'type': 'single_photon'},
        ],
        '图灵量子': [
            {'name': 'Gen-2', 'modes': 32, 'type': 'single_photon'},
        ],
        '玻色量子': [
            {'name': 'Basilisk', 'modes': 25, 'type': 'squeezed'},
        ],
    }

    def __init__(self, vendor='xanadu', model='Aurora'):
        self.vendor = vendor
        self.model = model
        self.n_modes = 0
        self.photonic_type = 'squeezed'
        self._resolve_model()

    def _resolve_model(self):
        for entry in self.VENDORS.get(self.vendor, []):
            if entry['name'].lower() == self.model.lower():
                self.n_modes = entry['modes']
                self.photonic_type = entry['type']
                return
        self.n_modes = 1000
        self.model = 'Aurora'

    @property
    def spec(self):
        return {
            'vendor': self.vendor,
            'model': self.model,
            'modes': self.n_modes,
            'type': self.photonic_type,
            'room_temp': True,
            'topology': 'all-to-all_via_switches',
        }

class NeutralAtomBackend:
    """中性原子/光镊后端 (QuEra, Pasqal, Atom Computing)"""

    VENDORS = {
        'quera': [
            {'name': 'Aquila',   'qubits': 256, 'reconfigurable': True},
            {'name': 'Aquila v2','qubits': 500, 'reconfigurable': True},
        ],
        'pasqal': [
            {'name': 'Fresnel', 'qubits': 200, 'reconfigurable': True},
        ],
    }

    def __init__(self, vendor='quera', model='Aquila v2'):
        self.vendor = vendor
        self.model = model
        self.n_atoms = 256
        self.reconfigurable = True
        self._resolve_model()

    def _resolve_model(self):
        for entry in self.VENDORS.get(self.vendor, []):
            if entry['name'].lower() == self.model.lower():
                self.n_atoms = entry['qubits']
                self.reconfigurable = entry['reconfigurable']
                return

    @property
    def spec(self):
        return {
            'vendor': self.vendor,
            'model': self.model,
            'qubits': self.n_atoms,
            'topology': 'reconfigurable',
            'room_temp': True,
            'requires_vacuum': True,
            'requires_laser': True,
        }

class SiliconSpinBackend:
    """硅基自旋后端 (Intel, Diraq, Equal1)"""
    VENDORS = {
        'intel': [
            {'name': 'Tunnel Falls', 'qubits': 12, 'temp_mk': 100},
        ],
        'diraq': [
            {'name': 'DQ v2', 'qubits': 10, 'temp_mk': 50},
        ],
        'equal1': [
            {'name': 'EQ1-2', 'qubits': 8, 'temp_mk': 300},
        ],
    }

    def __init__(self, vendor='intel', model='Tunnel Falls'):
        self.vendor = vendor
        self.model = model
        self.n_dots = 0
        self.temp_mk = 100
        self._resolve_model()

    def _resolve_model(self):
        for entry in self.VENDORS.get(self.vendor, []):
            if entry['name'].lower() == self.model.lower():
                self.n_dots = entry['qubits']
                self.temp_mk = entry['temp_mk']
                return

    @property
    def spec(self):
        return {
            'vendor': self.vendor,
            'model': self.model,
            'qubits': self.n_dots,
            'temp_mk': self.temp_mk,
            'topology': 'nearest_neighbor',
        }

class NVCenterBackend:
    """NV 色心后端 (Quantum Brilliance, 国仪量子)"""
    VENDORS = {
        'quantum_brilliance': [
            {'name': 'QB Cluster', 'qubits': 50},
        ],
        'ciqtek': [
            {'name': 'QP-G', 'qubits': 12},
        ],
    }

    def __init__(self, vendor='quantum_brilliance', model='QB Cluster'):
        self.vendor = vendor
        self.model = model
        self.n_centers = 50
        self._resolve_model()

    def _resolve_model(self):
        for entry in self.VENDORS.get(self.vendor, []):
            if entry['name'].lower() == self.model.lower():
                self.n_centers = entry['qubits']
                return

    @property
    def spec(self):
        return {
            'vendor': self.vendor,
            'model': self.model,
            'qubits': self.n_centers,
            'room_temp': True,
            'modular': True,
            'topology': 'diamond_lattice',
        }
