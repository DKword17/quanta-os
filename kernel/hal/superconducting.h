/**
 * kernel/hal/superconducting.h
 * 超导量子比特架构参数
 * 覆盖: IBM Transmon, Google Xmon, Rigetti Transmon,
 *       本源量子 (Origin Quantum), 国盾量子 (QuantumCTek)
 */

/*
 * ─────────────────────────────────────────────────────────────
 * Quanta OS — 版权与出处  |  Copyright & Provenance
 * 作者    Author   : DKword17 <19832535010@163.com>
 * 版权    Copyright: (c) 2026 DKword17
 * 许可证  License  : Apache 2.0（见 LICENSE）
 * 仓库    Repo     : https://github.com/DKword17/quanta-os
 * Quanta OS 由 DKword17 一人原创并维护，转载/复用请保留本标记。
 * ─────────────────────────────────────────────────────────────
 */

#include "qubit_abstract.h"

/* ========== 厂商规格表 ========== */

typedef struct {
    const char *vendor;
    const char *model;
    qubit_physical_type_t subtype;
    uint32_t   qubits;
    float      t1_us;
    float      t2_us;
    float      gate_fidelity_1q;
    float      gate_fidelity_2q;
    float      readout_fidelity;
    float      gate_time_ns;
    float      base_temp_mk;
    uint8_t    topology_type;    /* 0=heavy-hex, 1=grid, 2=square-lattice */
} superconducting_vendor_t;

static const superconducting_vendor_t known_superconducting[] = {
    /* IBM Quantum */
    {"IBM",  "Falcon r5.11",   QUBIT_TYPE_TRANSMON,   27,   100, 90,  0.9995, 0.995,  0.970, 40,  15, 0},
    {"IBM",  "Hummingbird",    QUBIT_TYPE_TRANSMON,   65,   120, 100, 0.9996, 0.996,  0.975, 40,  15, 0},
    {"IBM",  "Eagle r3",       QUBIT_TYPE_TRANSMON,   127,  150, 120, 0.9997, 0.997,  0.980, 40,  15, 0},
    {"IBM",  "Osprey",         QUBIT_TYPE_TRANSMON,   433,  130, 110, 0.9996, 0.996,  0.975, 45,  10, 0},
    {"IBM",  "Condor",         QUBIT_TYPE_TRANSMON,   1121, 100, 80,  0.9995, 0.994,  0.970, 45,  10, 0},
    {"IBM",  "Heron r1",       QUBIT_TYPE_TRANSMON,   133,  200, 160, 0.9998, 0.998,  0.985, 35,  10, 0},
    
    /* Google Quantum AI */
    {"Google", "Sycamore",     QUBIT_TYPE_XMON,       53,   50,  40,  0.9990, 0.995,  0.960, 50,  15, 1},
    {"Google", "Sycamore v2",  QUBIT_TYPE_XMON,       70,   60,  50,  0.9995, 0.996,  0.965, 45,  15, 1},
    {"Google", "Willow",       QUBIT_TYPE_XMON,       105,  100, 80,  0.9996, 0.997,  0.975, 40,  10, 1},
    
    /* Rigetti */
    {"Rigetti", "Aspen-M-3",   QUBIT_TYPE_TRANSMON,   80,   30,  25,  0.9990, 0.990,  0.950, 50,  20, 2},
    {"Rigetti", "Ankaa-3",     QUBIT_TYPE_TRANSMON,   84,   50,  40,  0.9995, 0.995,  0.970, 40,  15, 2},
    
    /* 本源量子 (Origin Quantum) */
    {"本源量子", "Origin Wukong", QUBIT_TYPE_TRANSMON, 72,  80,  60,  0.9992, 0.993,  0.960, 45,  15, 0},
    {"本源量子", "Origin Mountain",QUBIT_TYPE_TRANSMON,24,  70,  50,  0.9990, 0.990,  0.950, 50,  15, 2},
    
    /* 国盾量子 (QuantumCTek) */
    {"国盾量子", "QKD-72",     QUBIT_TYPE_FLUX_QUBIT, 72,   60,  45,  0.9985, 0.988,  0.940, 55,  20, 2},
    {"国盾量子", "ZD-50",      QUBIT_TYPE_FLUX_QUBIT, 50,   55,  40,  0.9980, 0.985,  0.935, 60,  20, 1},
    
    {NULL}
};

/* 超导后端默认参数 */
void superconducting_get_defaults(architecture_spec_t *spec);
int  superconducting_topology_map(uint32_t n_qubits, uint8_t topology_type,
                                   uint32_t *coupling_list, uint32_t *n_edges);
void superconducting_heavy_hex(uint32_t n_qubits, uint32_t *edges, uint32_t *n);
void superconducting_grid(uint32_t rows, uint32_t cols, uint32_t *edges, uint32_t *n);
