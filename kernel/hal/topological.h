/**
 * kernel/hal/topological.h
 * 拓扑量子比特
 * 覆盖: Microsoft Station Q (Majorana zero mode)
 *
 * 状态：至今未实现可靠的拓扑量子比特，均为实验阶段。
 * 但架构上预留——拓扑量子比特一旦实现，纠错代价极低。
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
    float      coherence_time_s;  /* 拓扑退相干小时级 */
    float      gate_fidelity_predict;
    uint8_t    experimental;
} topological_vendor_t;

static const topological_vendor_t known_topological[] = {
    {"Microsoft", "Station Q Gen-1", 0, 0, 0, 1}, /* 原型阶段 */
    {"Microsoft", "Station Q Gen-2 (Majorana 1)", 8, 1.0, 0.9999, 0},
    {NULL}
};

void topological_get_defaults(architecture_spec_t *spec);
