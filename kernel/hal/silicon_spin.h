/**
 * kernel/hal/silicon_spin.h
 * 硅基自旋量子比特架构参数
 * 覆盖: Intel Si/SiGe 量子点, Diraq 施主, Equal1
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
    qubit_physical_type_t subtype;  /* QUBIT_TYPE_SI_DOT / DONOR */
    uint32_t   qubits;
    float      t1_us;           /* 硅自旋 T1 较长 */
    float      t2_us;
    float      gate_fidelity_1q;
    float      gate_fidelity_2q;
    float      gate_time_ns;
    float      operating_temp_mk;  /* ~100mK - 1K */
} silicon_spin_vendor_t;

static const silicon_spin_vendor_t known_silicon_spin[] = {
    {"Intel",       "Tunnel Falls",   QUBIT_TYPE_SI_DOT, 12,  3e5, 2e5, 0.9990, 0.990, 50,  100},
    {"Intel",       "v2 (12-QD)",     QUBIT_TYPE_SI_DOT, 12,  5e5, 3e5, 0.9995, 0.993, 40,  100},
    
    {"Diraq",       "DQ v1",          QUBIT_TYPE_DONOR,  6,   1e6, 5e5, 0.9998, 0.995, 30,  50},
    {"Diraq",       "DQ v2",          QUBIT_TYPE_DONOR,  10,  2e6, 1e6, 0.9999, 0.997, 20,  50},
    
    {"Equal1",      "EQ1-1",          QUBIT_TYPE_SI_DOT, 6,   1e5, 8e4, 0.9980, 0.980, 60,  500},
    {"Equal1",      "EQ1-2 (Bell)",   QUBIT_TYPE_SI_DOT, 8,   2e5, 1e5, 0.9990, 0.990, 50,  300},
    
    {NULL}
};

void silicon_spin_get_defaults(architecture_spec_t *spec);
