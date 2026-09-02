/**
 * kernel/hal/nv_center.h
 * 金刚石 NV 色心量子比特参数
 * 覆盖: Quantum Brilliance, 国仪量子
 *
 * NV 色心独特优势：
 *   - 室温运行（无需稀释制冷机）
 *   - 小尺寸模块化，可集群
 *   - 光学读出/初始化
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
    float      t1_us;           /* NV 色心 T1 室温可达 ms 级 */
    float      t2_us;
    float      gate_fidelity_1q;
    float      gate_fidelity_2q;
    float      gate_time_ns;
    uint8_t    room_temp;       /* 1=室温工作 */
    uint8_t    modular;         /* 可级联模块 */
} nv_center_vendor_t;

static const nv_center_vendor_t known_nv_center[] = {
    {"Quantum Brilliance", "QB v1",    5,  1e4, 1e3, 0.9990, 0.980, 200, 1, 1},
    {"Quantum Brilliance", "QB v2",    12, 3e4, 5e3, 0.9995, 0.990, 150, 1, 1},
    {"Quantum Brilliance", "QB Cluster", 50, 5e4, 1e4, 0.9997, 0.993, 100, 1, 1},
    
    {"国仪量子", "CIQTEK QP-F",       6,  5e3, 5e2, 0.9980, 0.970, 300, 1, 0},
    {"国仪量子", "CIQTEK QP-G (金刚石)", 12, 1e4, 1e3, 0.9990, 0.980, 250, 1, 1},
    
    {NULL}
};

void nv_center_get_defaults(architecture_spec_t *spec);
