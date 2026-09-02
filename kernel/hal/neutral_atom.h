/**
 * kernel/hal/neutral_atom.h
 * 中性原子 / Rydberg 量子比特架构参数
 * 覆盖: QuEra (Rydberg), Pasqal (Rydberg), Atom Computing
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

typedef struct {
    const char *vendor;
    const char *model;
    uint32_t   qubits;
    float      t1_us;           /* 中性原子相干时间很长 */
    float      t2_us;
    float      gate_fidelity_1q;
    float      gate_fidelity_2q;
    float      gate_time_us;    /* Rydberg 门 μs 级 */
    uint8_t    reconfigurable;  /* 光镊可重配置拓扑 */
    uint8_t    uses_rydberg;    /* Rydberg 阻塞 */
} neutral_atom_vendor_t;

static const neutral_atom_vendor_t known_neutral_atom[] = {
    /* QuEra — 中性原子 Rydberg */
    {"QuEra",    "Aquila",     256, 5e5, 3e5, 0.9995, 0.990, 1.0, 1, 1},
    {"QuEra",    "Aquila v2",  500, 1e6, 5e5, 0.9998, 0.995, 0.8, 1, 1},
    
    /* Pasqal */
    {"Pasqal",   "Fresnel v1", 100, 3e5, 2e5, 0.9990, 0.985, 1.2, 1, 1},
    {"Pasqal",   "Fresnel v2", 200, 5e5, 3e5, 0.9995, 0.990, 1.0, 1, 1},
    
    /* Atom Computing */
    {"Atom Computing", "AC-1", 100,  1e6, 5e5, 0.9997, 0.993, 0.9, 1, 1},
    
    {NULL}
};

void neutral_atom_get_defaults(architecture_spec_t *spec);
