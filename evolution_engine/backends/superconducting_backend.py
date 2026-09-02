"""
evolution-engine/backends/superconducting_backend.py
超导量子计算机 — 专用后端
覆盖: IBM, Google, Rigetti, 本源量子, 国盾量子
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

class SuperconductingBackend:
    """
    超导量子后端

    特征:
    - Transmon/Xmon qubits
    - Heavy-Hex / Grid / Square 拓扑
    - CR 脉冲实现 CNOT
    - DRAG 脉冲整形，40-50ns 门时间
    - 稀释制冷机 ~15mK
    """

    VENDORS = {
        'ibm': [
            {'name': 'Falcon r5.11', 'qubits': 27,  'topology': 'heavy_hex'},
            {'name': 'Eagle r3',     'qubits': 127, 'topology': 'heavy_hex'},
            {'name': 'Heron r1',     'qubits': 133, 'topology': 'heavy_hex'},
            {'name': 'Condor',       'qubits': 1121,'topology': 'heavy_hex'},
        ],
        'google': [
            {'name': 'Sycamore',     'qubits': 53,  'topology': 'grid'},
            {'name': 'Willow',       'qubits': 105, 'topology': 'grid'},
        ],
        'rigetti': [
            {'name': 'Ankaa-3',      'qubits': 84,  'topology': 'square'},
        ],
        'origin_quantum': [
            {'name': 'Wukong',       'qubits': 72,  'topology': 'heavy_hex'},
        ],
        'quantumctek': [
            {'name': 'QKD-72',       'qubits': 72,  'topology': 'square'},
        ],
    }

    def __init__(self, vendor='ibm', model='Heron r1'):
        self.vendor = vendor
        self.model = model
        self.n_qubits = 0
        self.topology_type = None
        self.topology = None
        self.compiler = None

        self._resolve_model()
        self._build_topology()
        self.compiler = VariationalQuantumCompiler(self.topology)

    def _resolve_model(self):
        for entry in self.VENDORS.get(self.vendor, []):
            if entry['name'].lower() == self.model.lower():
                self.n_qubits = entry['qubits']
                self.topology_type = entry['topology']
                return
        # Default fallback
        self.n_qubits = 133
        self.topology_type = 'heavy_hex'
        self.model = 'Heron r1'

    def _build_topology(self):
        qubits = [QubitParams(id=i, t1_us=150, t2_us=120, 
                               readout_fidelity=0.98) for i in range(self.n_qubits)]
        edges = self._generate_topology()
        self.topology = Topology(qubits=qubits, edges=edges)

    def _generate_topology(self):
        if self.topology_type == 'heavy_hex':
            return self._heavy_hex_topology()
        elif self.topology_type == 'grid':
            return self._grid_topology()
        else:  # square
            return self._square_topology()

    def _heavy_hex_topology(self):
        """IBM 重六边形拓扑"""
        edges = []
        # 每层 6 qubit 六边形
        n_layers = max(1, self.n_qubits // 6)
        for layer in range(n_layers):
            base = layer * 6
            # 六边形内部边
            for i in range(6):
                if base + i + 1 < self.n_qubits:
                    edges.append(EdgeParams(base + i, base + (i + 1) % 6))
                if base + i + 6 < self.n_qubits and i % 2 == 0:
                    edges.append(EdgeParams(base + i, base + i + 6))
            # 层间连接
            if layer > 0:
                prev_base = (layer - 1) * 6
                for i in [0, 3]:
                    if prev_base + i < self.n_qubits and base + i < self.n_qubits:
                        edges.append(EdgeParams(prev_base + (i + 2) % 6, base + i))
        return edges

    def _grid_topology(self):
        """Google Grid 拓扑"""
        cols = int(self.n_qubits ** 0.5)
        rows = (self.n_qubits + cols - 1) // cols
        edges = []
        for r in range(rows):
            for c in range(cols):
                idx = r * cols + c
                if idx + 1 < self.n_qubits and c + 1 < cols:
                    edges.append(EdgeParams(idx, idx + 1))
                if idx + cols < self.n_qubits:
                    edges.append(EdgeParams(idx, idx + cols))
        return edges

    def _square_topology(self):
        return self._grid_topology()

    @property
    def spec(self):
        return {
            'vendor': self.vendor,
            'model': self.model,
            'qubits': self.n_qubits,
            'topology': self.topology_type,
            'gate_time_ns': 40,
            't1_us': 150,
            't2_us': 120,
            'requires_dilution_fridge': True,
            'operating_temp_mk': 15,
        }
