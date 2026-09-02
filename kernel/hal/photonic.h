/**
 * kernel/hal/photonic.h
 * 光量子计算架构参数
 * 覆盖: Xanadu (压缩态), PsiQuantum (单光子), 图灵量子, 玻色量子
 *
 * 光量子与其他架构差异最大：
 *   - 不基于 qubit，而是基于 qumode (连续变量)
 *   - 门操作 = 光学元件 (分束器、相移器、压缩器)
 *   - 测量 = 光子计数 / 零差检测 (homodyne detection)
 *   - 室温运行
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

/* 光量子使用 qumode 而非 qubit */
typedef enum {
    PHOTONIC_MODE_SQUEEZED,     /* 压缩真空态 (Xanadu, 玻色量子) */
    PHOTONIC_MODE_SINGLEPHOTON, /* 单光子 (PsiQuantum, 图灵量子) */
    PHOTONIC_MODE_FUSION        /* 融合态 (fusion-based) */
} photonic_mode_t;

typedef struct {
    const char *vendor;
    const char *model;
    photonic_mode_t mode;
    uint32_t   modes;            /* 光学模式数 */
    uint32_t   photon_number;    /* 最大光子数 */
    float      squeezing_db;     /* 压缩度 (dB) */
    float      loss_per_km_db;   /* 光纤损耗 dB/km */
    float      gate_fidelity_2q;
    float      detection_efficiency;
    float      clock_rate_mhz;   /* 重频 */
    
    /* 特殊操作 */
    uint8_t    supports_teleportation;
    uint8_t    supports_cluster_states;  /* 簇态生成 */
} photonic_vendor_t;

static const photonic_vendor_t known_photonic[] = {
    /* Xanadu — 压缩态光量子 */
    {"Xanadu",     "Borealis",     PHOTONIC_MODE_SQUEEZED, 216, 2, 12, 0.1, 0.990, 0.70, 1,  0, 1},
    {"Xanadu",     "X8",           PHOTONIC_MODE_SQUEEZED, 8,   2, 10, 0.1, 0.985, 0.68, 0.1, 0, 1},
    {"Xanadu",     "Aurora",       PHOTONIC_MODE_SQUEEZED, 1000, 2, 15, 0.05, 0.995, 0.80, 10, 1, 1},
    
    /* PsiQuantum — 单光子融合 */
    {"PsiQuantum", "Fusion v1",    PHOTONIC_MODE_SINGLEPHOTON, 1000, 1, 0, 0.01, 0.999, 0.90, 100, 1, 1},
    
    /* 图灵量子 (TuringQ) */
    {"图灵量子", "TuringQ Gen-1",PHOTONIC_MODE_SINGLEPHOTON, 8, 1, 0, 0.2, 0.980, 0.60, 0.01, 0, 0},
    {"图灵量子", "TuringQ Gen-2",PHOTONIC_MODE_SINGLEPHOTON, 32, 1, 0, 0.15, 0.990, 0.75, 1, 1, 1},
    
    /* 玻色量子 (BosonQ) */
    {"玻色量子", "Basilisk v1",  PHOTONIC_MODE_SQUEEZED, 25, 2, 8, 0.15, 0.975, 0.65, 0.01, 0, 1},
    
    {NULL}
};

void photonic_get_defaults(architecture_spec_t *spec);
